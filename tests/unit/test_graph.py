from datetime import UTC, datetime

import networkx as nx

from app.graph.builder import GraphBuilder
from app.graph.metrics import calculate_network_metrics
from app.models.events import AuthorInfo, CanonicalEvent, ContentInfo, RelationshipInfo


def test_constructs_reply_and_mention_edges_with_configured_weights() -> None:
    event = CanonicalEvent(
        platform="x",
        platform_post_id="edge-1",
        parent_platform_post_id="parent-1",
        interaction_type="reply",
        created_at=datetime(2026, 9, 20, 10, 0, tzinfo=UTC),
        collected_at=datetime(2026, 9, 20, 10, 0, 1, tzinfo=UTC),
        author=AuthorInfo(platform_user_id="source"),
        content=ContentInfo(text="hello", mentions=["mentioned"]),
        relationships=RelationshipInfo(parent_author_id="parent"),
        source_metadata={"mention_ids": ["mentioned-id"]},
    )
    edges = GraphBuilder().edges_from_event(event)
    by_type = {edge.interaction_type: edge for edge in edges}
    assert by_type["reply"].weight == 0.8
    assert by_type["mention"].weight == 0.5
    assert by_type["reply"].target_platform_user_id == "parent"


def test_calculates_required_network_metrics() -> None:
    builder = GraphBuilder()
    event = CanonicalEvent(
        platform="x",
        platform_post_id="edge-2",
        interaction_type="mention",
        created_at=datetime(2026, 9, 20, 10, 0, tzinfo=UTC),
        collected_at=datetime(2026, 9, 20, 10, 0, 1, tzinfo=UTC),
        author=AuthorInfo(platform_user_id="source"),
        content=ContentInfo(text="hello", mentions=["target"]),
        source_metadata={"mention_ids": ["target"]},
    )
    summary = calculate_network_metrics(builder.build_graph(builder.edges_from_event(event)))
    assert summary.nodes == 2
    assert summary.edges == 1
    assert summary.communities == 1
    assert {metric.node_id for metric in summary.metrics} == {"x:source", "x:target"}


def test_telegram_reply_and_forward_use_existing_graph_semantics() -> None:
    event = CanonicalEvent(
        platform="telegram",
        platform_post_id="-100777:10",
        parent_platform_post_id="-100777:9",
        interaction_type="reply",
        created_at=datetime(2026, 9, 20, 10, 0, tzinfo=UTC),
        collected_at=datetime(2026, 9, 20, 10, 0, 1, tzinfo=UTC),
        author=AuthorInfo(platform_user_id="reply-author"),
        content=ContentInfo(text="Forward in a reply"),
        relationships=RelationshipInfo(
            parent_author_id="parent-author",
            forwarded_from_id="source-channel",
        ),
    )

    edges = GraphBuilder().edges_from_event(event)
    by_type = {edge.interaction_type: edge for edge in edges}

    assert by_type["reply"].target_platform_user_id == "parent-author"
    assert by_type["reply"].weight == 0.8
    assert by_type["forward"].target_platform_user_id == "source-channel"
    assert by_type["forward"].weight == 1.0


def test_betweenness_treats_interaction_weights_as_strength() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", weight=5.0)
    graph.add_edge("b", "c", weight=5.0)
    graph.add_edge("a", "c", weight=1.0)

    summary = calculate_network_metrics(graph)
    middle = next(item for item in summary.metrics if item.node_id == "b")

    assert middle.betweenness_centrality > 0
    assert graph["a"]["b"]["distance"] == 0.2
