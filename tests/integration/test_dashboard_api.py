from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_repository
from app.graph.builder import GraphBuilder
from app.main import create_app
from app.models.events import AuthorInfo, CanonicalEvent, ContentInfo


def test_dashboard_event_and_graph_contracts(repository, fake_nlp_service) -> None:
    event = CanonicalEvent(
        platform="x",
        platform_post_id="dashboard-event",
        interaction_type="mention",
        created_at=datetime(2026, 9, 20, 12, 0, tzinfo=UTC),
        collected_at=datetime(2026, 9, 20, 12, 0, 2, tzinfo=UTC),
        author=AuthorInfo(platform_user_id="dashboard-source", username="source"),
        content=ContentInfo(text="Dashboard analytics event", mentions=["target"]),
        source_metadata={"replay": False, "mention_ids": ["dashboard-target"]},
    )
    repository.insert_event(event)
    repository.upsert_nlp_result(event.event_id, fake_nlp_service.analyze(event))
    repository.insert_graph_edges(GraphBuilder().edges_from_event(event))

    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(app) as client:
        events = client.get(
            "/api/events",
            params={"limit": 1, "offset": 0, "newest_first": True},
        )
        enriched = client.get("/api/events/enriched", params={"limit": 1})
        graph = client.get("/api/network/graph")
        health = client.get("/api/health")

    assert events.status_code == 200
    assert events.json()["total"] == 1
    assert events.json()["limit"] == 1
    assert enriched.status_code == 200
    assert enriched.json()["items"][0]["analysis"]["sentiment"]["label"] == "positive"
    assert enriched.json()["items"][0]["analysis"]["emotions"]["scores"]["anxiety"] == 0.2
    assert graph.status_code == 200
    assert graph.json()["node_count"] == 2
    assert graph.json()["edge_count"] == 1
    assert graph.json()["edges"][0]["interaction_type"] == "mention"
    assert health.status_code == 200
    assert health.json()["platforms"] == [
        {
            "platform": "x",
            "event_count": 1,
            "real_event_count": 1,
            "replay_event_count": 0,
            "latest_created_at": "2026-09-20T12:00:00Z",
            "latest_collected_at": "2026-09-20T12:00:02Z",
        }
    ]
    assert health.json()["updated_at"]


def test_dashboard_network_excludes_replay_edges(repository) -> None:
    live = CanonicalEvent(
        platform="x", platform_post_id="live-edge", interaction_type="mention",
        created_at=datetime(2026, 9, 20, 12, 0, tzinfo=UTC), collected_at=datetime(2026, 9, 20, 12, 0, 1, tzinfo=UTC),
        author=AuthorInfo(platform_user_id="live-source"), content=ContentInfo(text="live", mentions=["target"]),
        source_metadata={"replay": False, "mention_ids": ["live-target"]},
    )
    replay = live.model_copy(
        update={
            "event_id": uuid4(),
            "platform_post_id": "replay-edge",
            "author": AuthorInfo(platform_user_id="replay-source"),
            "source_metadata": {"replay": True, "mention_ids": ["replay-target"]},
        }
    )
    for event in [live, replay]:
        repository.insert_event(event)
        repository.insert_graph_edges(GraphBuilder().edges_from_event(event))
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(app) as client:
        graph = client.get("/api/network/graph")
    assert graph.json()["edge_count"] == 1
    assert graph.json()["edges"][0]["source"] == "x:live-source"
