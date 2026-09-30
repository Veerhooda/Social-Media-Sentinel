"""Deterministic tests for temporal snapshots, influence, communities, cascades."""
from datetime import UTC, datetime
from uuid import uuid4

from app.graph.builder import GraphBuilder
from app.graph.cascades import (
    CascadeEvent,
    propagation_path,
    reconstruct_cascades,
    sentiment_composition,
)
from app.graph.communities import community_profiles, detect_communities
from app.graph.metrics import calculate_network_metrics
from app.graph.schemas import EdgeRecord
from app.graph.snapshots import build_snapshots, influence_changes


def _edge(source: str, target: str, hours_ago: float, kind: str = "reply") -> EdgeRecord:
    base = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    from datetime import timedelta

    occurred = base - timedelta(hours=hours_ago)
    return EdgeRecord(
        event_id=uuid4(), platform="x", source_platform_user_id=source,
        target_platform_user_id=target, interaction_type=kind, weight=0.8,
        occurred_at=occurred,
    )


def test_snapshots_use_source_time_windows() -> None:
    edges = [_edge("a", "b", 0.2), _edge("b", "c", 0.4), _edge("c", "d", 5.0)]
    snapshots, anchored = build_snapshots(edges, window="1h", count=6)
    assert len(snapshots) == 6
    assert anchored > max(edge.occurred_at for edge in edges)
    populated = [s for s in snapshots if s.edges]
    assert len(populated) == 2
    assert all(s.window_end > s.window_start for s in snapshots)


def test_latest_edge_is_included_in_the_last_snapshot() -> None:
    newest = _edge("newest", "target", 0)
    snapshots, _ = build_snapshots([newest], window="1h", count=1)
    assert snapshots[0].edges == 1
    assert snapshots[0].window_start <= newest.occurred_at < snapshots[0].window_end


def test_snapshots_empty_without_edges() -> None:
    snapshots, anchored = build_snapshots([], window="1h", count=4)
    assert snapshots == [] and anchored is None


def test_influence_changes_require_two_measurements() -> None:
    edges = [_edge("a", "b", 0.2), _edge("solo", "other", 5.0)]
    detailed, _ = build_snapshots(edges, window="1h", count=6, include_metrics=True)
    deltas = influence_changes(detailed)
    measured = {d.node_id for d in deltas}
    # solo/other appear in one window only: no direction may be claimed.
    assert "x:solo" not in measured and "x:other" not in measured
    for delta in deltas:
        assert delta.windows_measured >= 2
        assert delta.metric in {"pagerank", "betweenness_centrality"}


def test_community_profiles_report_volume_and_types() -> None:
    edges = [_edge("a", "b", 0.1), _edge("b", "a", 0.2, "mention"), _edge("c", "d", 0.3)]
    graph = GraphBuilder.build_graph(edges)
    profiles = community_profiles(edges, detect_communities(graph))
    assert sum(p.interaction_volume for p in profiles) == 3
    assert all(p.size >= 1 for p in profiles)
    assert profiles[0].dominant_interaction_types


def test_cascade_reconstruction_depth_width_duration() -> None:
    base = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    from datetime import timedelta

    def ev(post: str, parent: str | None, minutes: int, author: str) -> CascadeEvent:
        return CascadeEvent(
            event_id=uuid4(), platform="x", platform_post_id=post,
            parent_platform_post_id=parent, thread_root_id="root",
            author_label=f"x:{author}", created_at=base + timedelta(minutes=minutes),
            interaction_type="reply", sentiment="positive",
        )

    events = [ev("root", None, 0, "alice"), ev("c1", "root", 5, "bob"),
              ev("c2", "root", 6, "carol"), ev("c3", "c1", 10, "dave")]
    cascades = reconstruct_cascades(events)
    assert len(cascades) == 1
    cascade = cascades[0]
    assert cascade.cascade_id == "x:root"
    assert cascade.event_count == 4
    assert cascade.depth == 3
    assert cascade.width == 2
    assert cascade.duration_seconds == 600.0
    assert cascade.provenance == "observed"
    assert len(cascade.participants) == 4


def test_cascade_marks_partially_observable_provenance() -> None:
    events = [CascadeEvent(
        event_id=uuid4(), platform="x", platform_post_id="orphan",
        parent_platform_post_id="missing-parent", thread_root_id="orphan",
        author_label="x:bob", created_at=datetime(2026, 9, 20, 12, tzinfo=UTC),
        interaction_type="reply",
    )]
    cascade = reconstruct_cascades(events)[0]
    assert cascade.provenance == "partially observable"
    assert cascade.missing_parents == 1


def test_missing_parent_does_not_create_an_observed_path() -> None:
    base = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    root = CascadeEvent(
        event_id=uuid4(), platform="x", platform_post_id="root",
        parent_platform_post_id=None, thread_root_id="root",
        author_label="x:root", created_at=base, interaction_type="post",
    )
    orphan = CascadeEvent(
        event_id=uuid4(), platform="x", platform_post_id="orphan",
        parent_platform_post_id="uncollected", thread_root_id="root",
        author_label="x:orphan", created_at=base, interaction_type="reply",
    )
    cascade = reconstruct_cascades([root, orphan])[0]
    assert cascade.provenance == "partially observable"
    assert cascade.depth == 1
    assert len(propagation_path(cascade)) == 1


def test_parent_created_after_child_is_not_an_observed_path() -> None:
    from datetime import timedelta

    base = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    parent = CascadeEvent(
        event_id=uuid4(), platform="x", platform_post_id="parent",
        parent_platform_post_id=None, thread_root_id="parent",
        author_label="x:parent", created_at=base + timedelta(minutes=1), interaction_type="post",
    )
    child = CascadeEvent(
        event_id=uuid4(), platform="x", platform_post_id="child",
        parent_platform_post_id="parent", thread_root_id="parent",
        author_label="x:child", created_at=base, interaction_type="reply",
    )
    cascade = reconstruct_cascades([parent, child])[0]
    assert cascade.provenance == "partially observable"
    assert cascade.depth == 1


def test_propagation_path_is_chronological_with_nlp() -> None:
    base = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    from datetime import timedelta

    def ev(post: str, parent: str | None, minutes: int, author: str) -> CascadeEvent:
        return CascadeEvent(
            event_id=uuid4(), platform="x", platform_post_id=post,
            parent_platform_post_id=parent, thread_root_id="root",
            author_label=f"x:{author}", created_at=base + timedelta(minutes=minutes),
            interaction_type="reply", sentiment="negative", emotion="anger", is_ironic=False,
        )

    events = [
        ev(post, parent, minutes, author)
        for post, parent, minutes, author in [("root", None, 0, "a"), ("c1", "root", 5, "b"), ("c2", "c1", 9, "c")]
    ]
    cascade = reconstruct_cascades(events)[0]
    steps = propagation_path(cascade, communities={"x:a": 0, "x:b": 0, "x:c": 1})
    assert [s["depth"] for s in steps] == [0, 1, 2]
    assert [s["occurred_at"] for s in steps] == sorted(s["occurred_at"] for s in steps)
    assert steps[0]["sentiment"] == "negative" and steps[0]["community"] == 0
    counts, composition = sentiment_composition(cascade)
    assert counts == {"negative": 3} and composition == {"negative": 1.0}


def test_sentiment_composition_empty_without_nlp() -> None:
    events = [CascadeEvent(
        event_id=uuid4(), platform="x", platform_post_id="p1", parent_platform_post_id=None,
        thread_root_id="p1", author_label="x:a",
        created_at=datetime(2026, 9, 20, 12, tzinfo=UTC), interaction_type="post",
    )]
    counts, composition = sentiment_composition(reconstruct_cascades(events)[0])
    assert counts == {} and composition == {}


def test_metrics_still_cover_required_algorithms() -> None:
    summary = calculate_network_metrics(GraphBuilder.build_graph([_edge("a", "b", 0.1)]))
    metric = summary.metrics[0]
    assert metric.pagerank >= 0 and metric.hub_score >= 0 and metric.authority_score >= 0
    assert summary.interpretation
