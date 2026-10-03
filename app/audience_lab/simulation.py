"""Run a draft post past every segment agent, analyse, rewrite, and re-test.

The only arithmetic done in code is aggregation: size-weighted averages of
what the agents reported, and the difference between the original and the
rewritten post. Every judgement (reactions, insights, the rewrite) comes from
the model. Uplift is therefore a *simulated* uplift: the same agents scoring
both versions under the same conditions.
"""
from __future__ import annotations

import hashlib
import json
import logging
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audience_lab import prompts
from app.audience_lab.config import AudienceLabSettings
from app.audience_lab.llm import LLMClient, LLMError
from app.audience_lab.models import AudienceSegment, PostSimulation
from app.audience_lab.schemas import AnalystOutput, SegmentReaction, SimulationRequest
from app.audience_lab.tracker import JobCancelled, JobTracker, TrackedClient, call_one, run_parallel

log = logging.getLogger(__name__)
METRICS = ("positive", "neutral", "negative", "sarcastic", "interested", "engage", "share")


def media_meta(request: SimulationRequest) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    if request.media_description:
        meta["description"] = request.media_description
    if request.image_data_url:
        header, _, data = request.image_data_url.partition(",")
        meta["mime"] = header.removeprefix("data:").split(";")[0]
        meta["sha256"] = hashlib.sha256(data.encode()).hexdigest()
        meta["approx_bytes"] = len(data) * 3 // 4
    return meta


def _agent_system(segment: AudienceSegment, platform: str) -> str:
    persona = segment.persona or {}
    return (
        (persona.get("agent_instructions") or f"You represent the audience segment '{segment.name}'.")
        + "\n\nSegment profile (from evidence):\n"
        + json.dumps({
            "segment": segment.name, "description": segment.description,
            "summary": persona.get("summary"), "demographics": persona.get("demographics"),
            "interests": persona.get("interests"), "values": persona.get("values"),
            "communication_style": persona.get("communication_style"),
            "positive_triggers": persona.get("positive_triggers"), "negative_triggers": persona.get("negative_triggers"),
            "sarcasm_tendency": persona.get("sarcasm_tendency"), "evidence_strength": persona.get("evidence_strength"),
            "member_attribute_breakdown": segment.attribute_breakdown,
        }, ensure_ascii=False)
        + prompts.AGENT_TASK.format(platform=platform)
    )


def _post_payload(text: str, media: dict[str, Any], has_image: bool) -> str:
    lines = ["DRAFT POST (data):", "<<<", text, ">>>"]
    if media.get("description"):
        lines.append(f"Attached media description: {media['description']}")
    if has_image:
        lines.append("The attached image is part of the post.")
    return "\n".join(lines)


def _normalise(reaction: SegmentReaction) -> dict[str, Any]:
    mix = reaction.reaction_mix_pct
    raw = {k: max(0.0, float(getattr(mix, k))) for k in ("positive", "neutral", "negative", "sarcastic")}
    total = sum(raw.values()) or 1.0
    data = reaction.model_dump()
    data["reaction_mix_pct"] = {k: round(100 * v / total, 1) for k, v in raw.items()}
    for key in ("interested_pct", "engage_pct", "share_pct"):
        data[key] = round(max(0.0, min(100.0, float(data[key]))), 1)
    return data


def run_panel(
    segments: list[AudienceSegment], text: str, platform: str, media: dict[str, Any],
    image_data_url: str | None, client: TrackedClient, settings: AudienceLabSettings, tracker: JobTracker,
    *, version: str = "original",
) -> dict[str, Any]:
    """Every segment agent reacts independently and in parallel."""
    user = _post_payload(text, media, bool(image_data_url))

    def react(segment: AudienceSegment):
        try:
            reaction = client.chat_json(
                label=f"{segment.name} agent ({version})",
                system=_agent_system(segment, platform), user=user, output=SegmentReaction,
                name="segment_reaction", image_data_url=image_data_url,
            )
            return segment, _normalise(reaction), None
        except JobCancelled:
            raise
        except LLMError as exc:
            return segment, None, str(exc)

    results: list[dict[str, Any]] = []
    for segment, reaction, error in run_parallel(react, segments, settings.audience_lab_max_parallel_agents, tracker):
        results.append({
            "segment_id": str(segment.segment_id), "code": segment.code, "name": segment.name,
            "share": segment.share, "member_count": segment.member_count,
            "status": "PASS" if reaction else "FAILED", "reaction": reaction, "error": error,
        })
        tracker.advance()
    results.sort(key=lambda r: r["code"])
    return {"segments": results, "weighted": weighted_metrics(results), "interested_audience": interested_audience(results, segments)}


def weighted_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [r for r in results if r["reaction"]]
    weight = sum(r["share"] for r in ok)
    if not ok or weight <= 0:
        return {"coverage_share": 0.0}
    out: dict[str, Any] = {"coverage_share": round(weight, 4)}
    for metric in METRICS:
        values = [(r["share"], _metric(r["reaction"], metric)) for r in ok]
        out[metric] = round(sum(w * v for w, v in values) / weight, 1)
    out["net_sentiment"] = round(out["positive"] - out["negative"] - out["sarcastic"], 1)
    return out


def _metric(reaction: dict[str, Any], metric: str) -> float:
    if metric in reaction["reaction_mix_pct"]:
        return reaction["reaction_mix_pct"][metric]
    return reaction[f"{metric}_pct"]


def interested_audience(results: list[dict[str, Any]], segments: list[AudienceSegment]) -> dict[str, Any]:
    """Who the interested people are: segment mix + attribute mix, weighted by interested share."""
    by_id = {str(s.segment_id): s for s in segments}
    weights = {
        r["segment_id"]: r["share"] * r["reaction"]["interested_pct"] / 100
        for r in results if r["reaction"]
    }
    total = sum(weights.values())
    if total <= 0:
        return {"interested_share_of_audience_pct": 0.0, "by_segment": [], "attributes": {}}
    by_segment = sorted(
        ({"segment": by_id[sid].name, "code": by_id[sid].code, "pct_of_interested": round(100 * w / total, 1)} for sid, w in weights.items()),
        key=lambda item: -item["pct_of_interested"],
    )
    attributes: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for sid, w in weights.items():
        for key, info in (by_id[sid].attribute_breakdown or {}).items():
            for entry in info.get("top", []):
                attributes[key][entry["value"]] += (w / total) * entry["pct"]
    attr_out = {
        key: [{"value": v, "pct": round(p, 1)} for v, p in sorted(values.items(), key=lambda kv: -kv[1])[:5]]
        for key, values in attributes.items()
    }
    return {
        "interested_share_of_audience_pct": round(100 * total / (sum(r["share"] for r in results if r["reaction"]) or 1), 1),
        "by_segment": by_segment,
        "attributes": attr_out,
    }


def compute_uplift(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    ids = {r["segment_id"] for r in before["segments"] if r["reaction"]} & {r["segment_id"] for r in after["segments"] if r["reaction"]}
    b = weighted_metrics([r for r in before["segments"] if r["segment_id"] in ids])
    a = weighted_metrics([r for r in after["segments"] if r["segment_id"] in ids])
    if "positive" not in b or "positive" not in a:
        return {"available": False, "reason": "No segment produced a reaction for both versions"}
    delta_pp = {m: round(a[m] - b[m], 1) for m in (*METRICS, "net_sentiment")}
    relative = {m: (round(100 * (a[m] - b[m]) / b[m], 1) if b[m] > 0 else None) for m in ("interested", "engage", "share", "positive")}
    per_segment = []
    before_by = {r["segment_id"]: r for r in before["segments"]}
    for r in after["segments"]:
        if r["segment_id"] not in ids:
            continue
        old, new = before_by[r["segment_id"]]["reaction"], r["reaction"]
        per_segment.append({
            "code": r["code"], "name": r["name"], "share": r["share"],
            "interested_pp": round(new["interested_pct"] - old["interested_pct"], 1),
            "engage_pp": round(new["engage_pct"] - old["engage_pct"], 1),
            "negative_pp": round(new["reaction_mix_pct"]["negative"] - old["reaction_mix_pct"]["negative"], 1),
            "sarcastic_pp": round(new["reaction_mix_pct"]["sarcastic"] - old["reaction_mix_pct"]["sarcastic"], 1),
        })
    return {
        "available": True,
        "method": "same segment agents scored the original and the rewrite; values are size-weighted simulated reactions",
        "segments_compared": len(ids),
        "before": b, "after": a, "delta_pp": delta_pp, "relative_pct": relative, "per_segment": per_segment,
    }


def run_simulation(
    session: Session, simulation_id: UUID, request: SimulationRequest,
    client: LLMClient, settings: AudienceLabSettings,
) -> None:
    sim = session.get(PostSimulation, simulation_id)
    if sim is None:
        return

    def flush(snapshot: dict[str, Any]) -> None:
        sim.progress = snapshot
        session.commit()

    tracker = JobTracker(simulation_id, "simulation", flush)
    tracked = TrackedClient(client, tracker)
    sim.status = "RUNNING"
    session.commit()
    try:
        segments = list(session.scalars(
            select(AudienceSegment).where(AudienceSegment.segmentation_id == sim.segmentation_id).order_by(AudienceSegment.code)
        ))
        if not segments:
            raise ValueError("The selected segmentation has no segments")
        steps = 3 if request.auto_improve else 2

        tracker.stage("agents_reacting", len(segments), step=1, steps=steps,
                      message=f"{len(segments)} audience agents are reading the post")
        baseline = run_panel(segments, sim.post_text, sim.platform, sim.media, request.image_data_url,
                             tracked, settings, tracker)
        sim.baseline = baseline
        session.commit()
        if not any(r["reaction"] for r in baseline["segments"]):
            raise LLMError("Every segment agent failed: " + "; ".join({r["error"] or "" for r in baseline["segments"]}))

        tracker.stage("analysing", 1, step=2, steps=steps, message="Lead analyst is combining the reactions")
        analyst_input = {
            "platform": sim.platform,
            "draft_post": sim.post_text,
            "media": sim.media,
            "weighted_totals": baseline["weighted"],
            "interested_audience_computed": baseline["interested_audience"],
            "segments": [
                {"name": r["name"], "share_of_audience": round(r["share"], 3), "member_count": r["member_count"], "reaction": r["reaction"]}
                for r in baseline["segments"] if r["reaction"]
            ],
        }
        analysis = call_one(lambda: tracked.chat_json(
            label="Lead analyst", system=prompts.ANALYST, user=json.dumps(analyst_input, ensure_ascii=False),
            output=AnalystOutput, name="post_analysis", image_data_url=request.image_data_url,
        ), tracker)
        tracker.advance()
        sim.analysis = analysis.model_dump()
        session.commit()

        rewrite = analysis.improved_post.strip()
        if request.auto_improve and analysis.should_rewrite and rewrite and rewrite != sim.post_text.strip():
            sim.improved_post = rewrite
            tracker.stage("retesting_rewrite", len(segments), step=3, steps=steps,
                          message="Same agents are scoring the rewritten post")
            improved = run_panel(segments, rewrite, sim.platform, sim.media, request.image_data_url,
                                 tracked, settings, tracker, version="rewrite")
            sim.improved = improved
            sim.uplift = compute_uplift(baseline, improved)
        elif request.auto_improve:
            sim.uplift = {"available": False, "reason": "The analyst judged that no rewrite would improve the reaction"}
        failed = [r for r in baseline["segments"] if not r["reaction"]]
        sim.status = "PARTIAL" if failed else "COMPLETED"
        tracker.stage("completed", step=steps, steps=steps, message="Simulation complete")
    except (LLMError, ValueError) as exc:
        session.rollback()
        sim = session.get(PostSimulation, simulation_id)
        cancelled = isinstance(exc, JobCancelled)
        sim.status = "CANCELLED" if cancelled else "FAILED"
        sim.error = str(exc)[:2000]
        tracker.event(f"{'Cancelled' if cancelled else 'Failed'}: {exc}", "warn")
        sim.progress = {**tracker.snapshot(), "stage": sim.status.lower()}
        log.warning("Simulation %s %s: %s", simulation_id, sim.status, exc)
    finally:
        tracker.close()
    sim.completed_at = datetime.now(UTC)
    session.commit()
