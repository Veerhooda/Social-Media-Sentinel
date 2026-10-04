"""End-to-end Audience Lab flow against PostgreSQL with a scripted model double."""
from __future__ import annotations

import re
import threading
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.audience_lab import (
    routes,  # also registers Audience Lab tables on Base.metadata
)
from app.audience_lab.config import AudienceLabSettings, get_lab_settings
from app.audience_lab.llm import LLMError
from app.audience_lab.schemas import (
    AnalystOutput,
    AssignmentOutput,
    DiscoveryOutput,
    PersonaOutput,
    SegmentReaction,
)
from app.db.models import NLPAnalysis, SocialEvent, SocialUser, UserDemographic
from app.db.session import get_db_session

pytestmark = pytest.mark.integration


class ScriptedMuse:
    """Deterministic stand-in for Muse Spark; reacts to its inputs, not to hard-coded answers."""

    model_name = "scripted-muse"

    def __init__(self, fail_segment: str | None = None):
        self.calls: list[str] = []
        self.efforts: list[tuple[str, str | None]] = []
        self.crash = False
        self.fail_segment = fail_segment
        self.lock = threading.Lock()

    def chat_json(self, *, system, user, output, name, image_data_url=None, temperature=None, reasoning_effort=None):
        with self.lock:
            self.calls.append(name)
            self.efforts.append((name, reasoning_effort))
        if self.crash:
            raise RuntimeError("boom")
        if output is DiscoveryOutput:
            assert "between 2 and 4" in system
            return DiscoveryOutput(rationale="profession splits reactions", segments=[
                {"id": "S1", "name": "Builders", "description": "tech workers", "defining_traits": ["tech"],
                 "membership_rule": "profession=Technology", "estimated_share_pct": 60},
                {"id": "S2", "name": "Creatives", "description": "artists", "defining_traits": ["art"],
                 "membership_rule": "profession=Arts", "estimated_share_pct": 40},
                {"id": "S3", "name": "Nobody", "description": "empty", "defining_traits": [],
                 "membership_rule": "never", "estimated_share_pct": 0},
            ])
        if output is AssignmentOutput:
            refs = re.findall(r"^(P\d+) \|(.*)$", user, flags=re.MULTILINE)
            return AssignmentOutput(assignments=[
                {"ref": ref, "segment_id": "S1" if "Technology" in rest else "S2" if "Arts" in rest else "UNASSIGNED", "confidence": 0.9}
                for ref, rest in refs
            ] + [{"ref": "P999", "segment_id": "S1", "confidence": 1}])  # hallucinated ref must be ignored
        if output is PersonaOutput:
            name_ = "Builders" if '"Builders"' in user else "Creatives"
            return PersonaOutput(
                persona_name=name_, summary=f"{name_} summary", demographics="evidence based", interests=["x"], values=["y"],
                communication_style="direct", positive_triggers=["utility"], negative_triggers=["hype"],
                sarcasm_tendency="medium", evidence_strength="moderate",
                agent_instructions=f"You represent the {name_} segment.",
            )
        if output is SegmentReaction:
            builders = "Builders segment" in system
            if self.fail_segment and f"{self.fail_segment} segment" in system:
                raise LLMError("simulated outage")
            improved = "with a free trial" in user
            base = 30 if builders else 10
            bump = 20 if improved else 0
            return SegmentReaction(
                first_impression="meh" if not improved else "better",
                reaction_mix_pct={"positive": base + bump, "neutral": 40, "negative": 20 - bump / 2, "sarcastic": 10},
                interested_pct=base + bump, engage_pct=base / 2 + bump, share_pct=5,
                interested_subgroups=[{"who": "seniors", "why": "fit", "share_of_segment_pct": 20}],
                sample_reactions=[{"voice": "member", "tone": "sarcastic", "text": "sure, another launch"}],
                what_works=["clear"], what_fails=["vague"], misread_risks=[],
                suggested_edits=[{"change": "add a free trial", "expected_effect": "more interest"}],
                confidence="medium", confidence_reason="ok",
            )
        if output is AnalystOutput:
            assert "weighted_totals" in user
            return AnalystOutput(
                headline="Lukewarm", verdict="minor_edits", summary="needs a hook", key_insights=["a"], risks=["b"],
                interested_audience_profile="mostly builders",
                recommendations=[{"change": "offer trial", "rationale": "builders want to try", "segments_helped": ["Builders"],
                                  "segments_at_risk": [], "priority": "high"}],
                should_rewrite=True, improved_post="We launched our tool — start with a free trial today.", rewrite_notes="added CTA",
            )
        raise AssertionError(f"unexpected output {output}")


def _seed(session):
    now = datetime(2026, 9, 30, tzinfo=UTC)
    for i in range(10):
        profession = "Technology" if i < 6 else "Arts"
        user = SocialUser(platform="x", platform_user_id=f"u{i}", username=f"user{i}", bio=f"bio {i}", followers_count=10 * i)
        session.add(user)
        session.flush()
        session.add(UserDemographic(user_id=user.user_id, primary_language="en", professional_sector=profession, inferred_country="IN"))
        for j in range(2):
            event = SocialEvent(platform="x", platform_post_id=f"p{i}-{j}", author_id=user.user_id, interaction_type="post",
                                created_at=now - timedelta(minutes=i * 3 + j), collected_at=now,
                                content_text=f"post {j} about {profession.lower()} #topic{i % 2}", hashtags=[f"topic{i % 2}"],
                                metrics={"likes": i, "shares": 1, "comments": 0})
            session.add(event)
            session.flush()
            session.add(NLPAnalysis(event_id=event.event_id, sentiment_label="positive" if j else "negative", sentiment_confidence=0.8,
                                    sentiment_scores={}, is_ironic=bool(i % 3 == 0), irony_confidence=0.5, irony_scores={},
                                    primary_emotion="joy", emotion_scores={}, model_versions={}, processed_at=now))
    # replay data must be ignored
    ghost = SocialUser(platform="x", platform_user_id="replay", username="replay")
    session.add(ghost)
    session.flush()
    session.add(SocialEvent(platform="x", platform_post_id="r1", author_id=ghost.user_id, interaction_type="post", created_at=now,
                            collected_at=now, content_text="replayed", source_metadata={"replay": True}))
    session.commit()


@pytest.fixture()
def api(db_session, db_engine):
    factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    settings = AudienceLabSettings(_env_file=None, META_MODEL_API_KEY="k", audience_lab_min_segments=2,
                                   audience_lab_max_segments=4, audience_lab_assign_batch=5, audience_lab_max_parallel_agents=3)
    muse = ScriptedMuse()
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_lab_settings] = lambda: settings
    app.dependency_overrides[routes.get_session_factory] = lambda: factory
    app.dependency_overrides[routes.get_client_factory] = lambda: (lambda _s: muse)
    app.dependency_overrides[routes.get_job_runner] = lambda: (lambda job: job())  # run inline
    _seed(db_session)
    client = TestClient(app)
    client.muse = muse
    return client


def test_full_flow_profiles_segments_agents_uplift(api):
    status = api.get("/api/audience-lab/status").json()
    assert status["total_profiles"] == 0 and status["latest_segmentation_id"] is None

    synced = api.post("/api/audience-lab/profiles/sync").json()
    assert synced["created"] == 10 and synced["by_source"] == {"social": 10}
    again = api.post("/api/audience-lab/profiles/sync").json()
    assert again["created"] == 0 and again["updated"] == 10

    imported = api.post("/api/audience-lab/profiles/import", json={"profiles": [
        {"source": "survey_2026", "external_ref": "panel-a", "attributes": {"profession": "Technology", "age": "25-34",
         "interests": ["ai", "devtools"]}, "sample_texts": ["I love trying new dev tools"], "weight": 50},
    ]}).json()
    assert imported["total_profiles"] == 11 and imported["by_source"]["survey_2026"] == 1

    page = api.get("/api/audience-lab/profiles", params={"source": "social", "limit": 3}).json()
    assert page["total"] == 10 and len(page["items"]) == 3
    assert page["items"][0]["attributes"]["profession"] in {"Technology", "Arts"}
    assert "sentiment_mix_pct" in page["items"][0]["behaviour"]

    seg = api.post("/api/audience-lab/segmentations", json={"focus": "how they buy tools"}).json()
    seg = api.get(f"/api/audience-lab/segmentations/{seg['segmentation_id']}").json()
    assert seg["status"] == "COMPLETED", seg["error"]
    assert seg["profile_count"] == 11 and seg["assigned_count"] == 11
    names = {s["name"]: s for s in seg["segments"]}
    assert set(names) == {"Builders", "Creatives"}  # empty model segment dropped
    assert names["Builders"]["member_count"] == 7
    assert names["Builders"]["share"] == pytest.approx(56 / 60)  # survey panel represents 50 people
    assert names["Builders"]["persona"]["agent_instructions"].startswith("You represent")
    assert names["Builders"]["attribute_breakdown"]["profession"]["top"][0]["value"] == "Technology"
    progress = seg["progress"]
    assert progress["stage"] == "completed" and progress["calls"]["finished"] == 1 + 3 + 2  # design + 3 batches + 2 agents
    assert any("Batch 1/3" in e["message"] for e in progress["events"])
    assert {e for n, e in api.muse.efforts if n == "segment_assignment"} == {"low"}

    sim = api.post("/api/audience-lab/simulations", json={"text": "We launched our tool.", "platform": "linkedin",
                                                          "image_data_url": "data:image/png;base64,iVBORw0KGgo="}).json()
    sim = api.get(f"/api/audience-lab/simulations/{sim['simulation_id']}").json()
    assert sim["status"] == "COMPLETED", sim["error"]
    assert sim["media"]["mime"] == "image/png" and "sha256" in sim["media"]
    weighted = sim["baseline"]["weighted"]
    assert weighted["positive"] == pytest.approx((56 * 30 + 4 * 12.5) / 60, abs=0.1)  # Creatives mix renormalised from 80 to 100
    assert sum(weighted[k] for k in ("positive", "neutral", "negative", "sarcastic")) == pytest.approx(100, abs=0.5)
    interested = sim["baseline"]["interested_audience"]
    assert interested["by_segment"][0]["segment"] == "Builders"
    assert sim["analysis"]["verdict"] == "minor_edits"
    assert "free trial" in sim["improved_post"]
    uplift = sim["uplift"]
    assert uplift["available"] and uplift["segments_compared"] == 2
    assert uplift["delta_pp"]["interested"] == pytest.approx(20, abs=0.1)
    assert uplift["relative_pct"]["interested"] > 0
    assert api.get("/api/audience-lab/simulations").json()[0]["headline"] == "Lukewarm"
    assert api.muse.calls.count("segment_reaction") == 4  # 2 agents x (original + rewrite)


def test_partial_agent_failure_is_reported_not_hidden(api):
    api.post("/api/audience-lab/profiles/sync")
    api.post("/api/audience-lab/segmentations", json={})
    api.muse.fail_segment = "Creatives"
    sim = api.post("/api/audience-lab/simulations", json={"text": "Hello world", "platform": "x", "auto_improve": False}).json()
    sim = api.get(f"/api/audience-lab/simulations/{sim['simulation_id']}").json()
    assert sim["status"] == "PARTIAL"
    failed = [s for s in sim["baseline"]["segments"] if s["status"] == "FAILED"]
    assert len(failed) == 1 and "outage" in failed[0]["error"]
    assert sim["improved_post"] is None and sim["uplift"] is None


def test_simulation_requires_segments_and_key(api, db_session):
    assert api.post("/api/audience-lab/simulations", json={"text": "Hi", "platform": "x"}).status_code == 409
    api.app.dependency_overrides[routes.get_client_factory] = lambda: (lambda _s: (_ for _ in ()).throw(LLMError("META_MODEL_API_KEY is not configured")))
    response = api.post("/api/audience-lab/segmentations", json={})
    assert response.status_code == 503 and "META_MODEL_API_KEY" in response.json()["detail"]


def test_crash_marks_job_failed_and_orphans_expire(api, db_session):
    api.post("/api/audience-lab/profiles/sync")
    api.muse.crash = True
    seg = api.post("/api/audience-lab/segmentations", json={}).json()
    seg = api.get(f"/api/audience-lab/segmentations/{seg['segmentation_id']}").json()
    assert seg["status"] == "FAILED" and "RuntimeError" in seg["error"]

    from app.audience_lab.models import AudienceSegmentation
    orphan = AudienceSegmentation(status="RUNNING", model_name="m", params={}, progress={})
    db_session.add(orphan)
    db_session.commit()
    seen = api.get(f"/api/audience-lab/segmentations/{orphan.segmentation_id}").json()
    assert seen["status"] == "FAILED" and "restarted" in seen["error"]


def test_cancel_stops_job(api):
    api.post("/api/audience-lab/profiles/sync")
    from app.audience_lab import tracker
    captured = {}

    def runner(job):
        captured["job"] = job

    api.app.dependency_overrides[routes.get_job_runner] = lambda: runner
    seg = api.post("/api/audience-lab/segmentations", json={}).json()
    assert tracker.is_live(UUID(seg["segmentation_id"]))
    assert api.post(f"/api/audience-lab/segmentations/{seg['segmentation_id']}/cancel").status_code == 200
    captured["job"]()  # job starts after cancel was requested
    seg = api.get(f"/api/audience-lab/segmentations/{seg['segmentation_id']}").json()
    assert seg["status"] == "CANCELLED"
    assert api.muse.calls == []
