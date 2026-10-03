from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.graph.audience import audience_dimensions, coverage, public_profile
from app.graph.communities import community_profiles
from app.graph.schemas import EdgeRecord


def _edge(source: str, target: str, kind: str = "reply", minute: int = 0) -> EdgeRecord:
    return EdgeRecord(
        event_id=uuid4(), platform="x", source_platform_user_id=source,
        target_platform_user_id=target, interaction_type=kind, weight=0.8,
        occurred_at=datetime(2026, 9, 20, tzinfo=UTC) + timedelta(minutes=minute),
    )


def test_cross_community_edges_do_not_duplicate_membership() -> None:
    assignments = {"x:a": 1, "x:b": 1, "x:c": 2, "x:d": 2}
    profiles = community_profiles(
        [_edge("a", "b"), _edge("b", "c", minute=1), _edge("c", "d", minute=2)],
        assignments,
    )
    assert {profile.community_id: profile.size for profile in profiles} == {1: 2, 2: 2}
    assert sum(profile.size for profile in profiles) == len(assignments)
    # Cross-community interactions are incident to both cohorts, while each
    # endpoint remains assigned to exactly one cohort.
    assert {profile.community_id: profile.interaction_volume for profile in profiles} == {1: 2, 2: 2}


def test_audience_coverage_keeps_missing_profiles_unknown() -> None:
    nodes = {"x:a", "x:b", "x:c", "x:d"}
    stored = {
        "x:a": (SimpleNamespace(username="alice", display_name="Alice", avatar_url="https://example.org/a.png", is_verified=False), SimpleNamespace(primary_language="en", inferred_country="US", professional_sector="Technology")),
        "x:b": (SimpleNamespace(username=None, display_name="Bob", avatar_url=None, is_verified=None), SimpleNamespace(primary_language="en", inferred_country=None, professional_sector="Unknown")),
        "x:c": (SimpleNamespace(username="carol", display_name="Carol", avatar_url=None, is_verified=None), SimpleNamespace(primary_language="en", inferred_country=None, professional_sector=None)),
    }
    counts = coverage(nodes, stored)
    assert (counts.total_nodes, counts.stored_profiles, counts.referenced_only, counts.avatar_available) == (4, 3, 1, 1)
    categories = audience_dimensions(nodes, stored)
    assert categories["language"].status == "AVAILABLE"
    assert categories["language"].distribution == {"en": 3}
    assert categories["language"].unknown == 1
    assert categories["geography"].status == "INSUFFICIENT_DATA"
    assert categories["geography"].distribution == {}
    assert categories["geography"].unknown == 3
    assert categories["geography"].suppressed == 1
    assert categories["profession"].distribution == {}
    assert categories["profession"].suppressed == 1
    assert public_profile(None).status == "referenced_only"
    assert public_profile(stored["x:a"]).avatar_url == "https://example.org/a.png"
