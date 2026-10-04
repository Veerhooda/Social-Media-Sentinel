"""Model-driven audience segmentation: discover → assign → build persona agents."""
from __future__ import annotations

import json
import logging
import random
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audience_lab import prompts
from app.audience_lab.config import AudienceLabSettings
from app.audience_lab.llm import LLMClient, LLMError
from app.audience_lab.models import (
    AudienceProfile,
    AudienceSegment,
    AudienceSegmentation,
    AudienceSegmentMember,
)
from app.audience_lab.profiles import attribute_breakdown, profile_card
from app.audience_lab.schemas import (
    AssignmentOutput,
    DiscoveryOutput,
    PersonaOutput,
    SegmentationRequest,
)
from app.audience_lab.tracker import (
    JobCancelled,
    JobTracker,
    TrackedClient,
    call_one,
    run_parallel,
)

log = logging.getLogger(__name__)
UNASSIGNED = "UNASSIGNED"
STEPS = 3


def run_segmentation(
    session: Session, segmentation_id: UUID, request: SegmentationRequest,
    client: LLMClient, settings: AudienceLabSettings, *, seed: int | None = None,
) -> None:
    run = session.get(AudienceSegmentation, segmentation_id)
    if run is None:
        return

    def flush(snapshot: dict) -> None:
        run.progress = snapshot
        session.commit()

    tracker = JobTracker(segmentation_id, "segmentation", flush)
    run.status = "RUNNING"
    session.commit()
    try:
        _segment(session, run, request, TrackedClient(client, tracker), settings, tracker, seed=seed)
        run.status = "COMPLETED"
        tracker.stage("completed", step=STEPS, steps=STEPS, message="Segmentation complete")
    except (LLMError, ValueError) as exc:
        session.rollback()
        run = session.get(AudienceSegmentation, segmentation_id)
        cancelled = isinstance(exc, JobCancelled)
        run.status = "CANCELLED" if cancelled else "FAILED"
        run.error = str(exc)[:2000]
        tracker.event(f"{'Cancelled' if cancelled else 'Failed'}: {exc}", "warn")
        run.progress = {**tracker.snapshot(), "stage": run.status.lower()}
        log.warning("Segmentation %s %s: %s", segmentation_id, run.status, exc)
    finally:
        tracker.close()
    run.completed_at = datetime.now(UTC)
    session.commit()


def _segment(
    session: Session, run: AudienceSegmentation, request: SegmentationRequest,
    client: TrackedClient, settings: AudienceLabSettings, tracker: JobTracker, *, seed: int | None,
) -> None:
    query = select(AudienceProfile).order_by(AudienceProfile.created_at, AudienceProfile.profile_id)
    if request.sources:
        query = query.where(AudienceProfile.source.in_(request.sources))
    profiles = list(session.scalars(query))
    if not profiles:
        raise ValueError("No audience profiles available. Sync or import profiles first.")
    lo = request.min_segments or settings.audience_lab_min_segments
    hi = request.max_segments or settings.audience_lab_max_segments
    lo, hi = min(lo, hi), max(lo, hi)
    hi = max(1, min(hi, len(profiles)))
    lo = min(lo, hi)
    run.profile_count = len(profiles)
    refs = {f"P{i + 1}": profile for i, profile in enumerate(profiles)}

    # 1. Discover segments from a random sample -------------------------
    rng = random.Random(seed)
    sample_refs = list(refs)
    if len(sample_refs) > settings.audience_lab_discovery_sample:
        sample_refs = rng.sample(sample_refs, settings.audience_lab_discovery_sample)
    tracker.stage("discovering_segments", 1, step=1, steps=STEPS,
                  message=f"Reading {len(sample_refs)} of {len(profiles)} profiles to design segments ({lo}-{hi})")
    cards = "\n".join(profile_card(ref, refs[ref]) for ref in sample_refs)
    focus = f"Team's steer for this segmentation: {request.focus}" if request.focus else ""
    discovery = call_one(lambda: client.chat_json(
        label="Segment design", system=prompts.DISCOVERY.format(min_segments=lo, max_segments=hi, focus=focus),
        user=f"Total audience profiles: {len(profiles)} (showing {len(sample_refs)} random cards)\n\n{cards}",
        output=DiscoveryOutput, name="audience_segmentation",
    ), tracker)
    tracker.advance()
    segments = _dedupe_segments(discovery)[:hi]
    if not segments:
        raise LLMError("Model proposed no segments")
    run.rationale = discovery.rationale
    tracker.event("Proposed segments: " + ", ".join(f"{s.id} {s.name}" for s in segments))

    # 2. Assign every profile (parallel batches) -------------------------
    definitions = json.dumps([
        {"id": s.id, "name": s.name, "membership_rule": s.membership_rule, "traits": s.defining_traits}
        for s in segments
    ], ensure_ascii=False)
    valid_ids = {s.id for s in segments}
    size = settings.audience_lab_assign_batch
    ordered = list(refs)
    batches = [(n + 1, ordered[i:i + size]) for n, i in enumerate(range(0, len(ordered), size))]
    tracker.stage("assigning_profiles", len(batches), step=2, steps=STEPS,
                  message=f"Placing {len(ordered)} profiles in {len(batches)} batches of up to {size} "
                          f"({min(settings.audience_lab_max_parallel_agents, len(batches))} at a time)")
    assignment: dict[str, tuple[str, float]] = {}

    def assign(item: tuple[int, list[str]]) -> list[tuple[str, str, float]]:
        number, batch = item
        out = client.chat_json(
            label=f"Batch {number}/{len(batches)} ({len(batch)} profiles)",
            system=prompts.ASSIGN,
            user=f"Segments:\n{definitions}\n\nProfiles:\n" + "\n".join(profile_card(r, refs[r], texts=1) for r in batch),
            output=AssignmentOutput, name="segment_assignment", temperature=0,
            reasoning_effort=settings.audience_lab_fast_reasoning_effort,
        )
        wanted = set(batch)
        return [(a.ref, a.segment_id, a.confidence) for a in out.assignments if a.ref in wanted]

    for result in run_parallel(assign, batches, settings.audience_lab_max_parallel_agents, tracker):
        for ref, segment_id, confidence in result:
            if segment_id in valid_ids and ref not in assignment:
                assignment[ref] = (segment_id, max(0.0, min(1.0, confidence)))
        tracker.advance()

    members: dict[str, list[tuple[AudienceProfile, float]]] = defaultdict(list)
    for ref, (segment_id, confidence) in assignment.items():
        members[segment_id].append((refs[ref], confidence))
    total_weight = sum(p.weight or 1 for p in profiles) or 1
    run.assigned_count = len(assignment)
    tracker.event(f"Placed {len(assignment)}/{len(profiles)} profiles; " + ", ".join(
        f"{s.id}: {len(members.get(s.id, []))}" for s in segments))

    # 3. Build one persona agent per non-empty segment --------------------
    populated = [s for s in segments if members.get(s.id)]
    tracker.stage("building_agents", len(populated), step=3, steps=STEPS,
                  message=f"Writing {len(populated)} audience agents from their members' evidence")
    samples = {
        s.id: (lambda g: g if len(g) <= settings.audience_lab_persona_sample else rng.sample(g, settings.audience_lab_persona_sample))(
            [p for p, _ in members[s.id]]
        )
        for s in populated
    }

    def persona(segment) -> tuple[str, PersonaOutput]:
        group = [p for p, _ in members[segment.id]]
        payload = {
            "segment": segment.model_dump(),
            "member_count": len(group),
            "share_of_audience_pct": round(100 * sum(p.weight or 1 for p in group) / total_weight, 1),
            "attribute_breakdown": attribute_breakdown(group),
        }
        out = client.chat_json(
            label=f"Agent for {segment.name}",
            system=prompts.PERSONA,
            user=json.dumps(payload, ensure_ascii=False) + "\n\nMember cards:\n"
            + "\n".join(profile_card(f"M{i + 1}", p, texts=3) for i, p in enumerate(samples[segment.id])),
            output=PersonaOutput, name="segment_persona",
        )
        return segment.id, out

    personas: dict[str, PersonaOutput] = {}
    for segment_id, out in run_parallel(persona, populated, settings.audience_lab_max_parallel_agents, tracker):
        personas[segment_id] = out
        tracker.advance()

    for segment in populated:
        group = members[segment.id]
        weight = sum(p.weight or 1 for p, _ in group)
        row = AudienceSegment(
            segmentation_id=run.segmentation_id, code=segment.id, name=segment.name[:256],
            description=segment.description, defining_traits=segment.defining_traits,
            member_count=len(group), weight_total=weight, share=weight / total_weight,
            attribute_breakdown=attribute_breakdown([p for p, _ in group]),
            persona={**personas[segment.id].model_dump(), "membership_rule": segment.membership_rule},
        )
        session.add(row)
        session.flush()
        session.add_all(AudienceSegmentMember(segment_id=row.segment_id, profile_id=p.profile_id, confidence=c) for p, c in group)
    session.commit()


def _dedupe_segments(discovery: DiscoveryOutput):
    seen: set[str] = set()
    out = []
    for index, segment in enumerate(discovery.segments):
        sid = (segment.id or f"S{index + 1}").strip().upper()
        if sid in seen or sid == UNASSIGNED:
            sid = f"S{index + 1}"
        seen.add(sid)
        out.append(segment.model_copy(update={"id": sid}))
    return out
