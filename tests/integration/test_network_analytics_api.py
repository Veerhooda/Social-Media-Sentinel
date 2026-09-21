"""Integration: temporal/influence/community/cascade endpoints on fixture data."""
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_repository
from app.graph.builder import GraphBuilder
from app.main import create_app
from app.models.events import AuthorInfo, CanonicalEvent, ContentInfo, RelationshipInfo

pytestmark = pytest.mark.integration

BASE = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def _reply(post: str, parent: str, root: str, author: str, parent_author: str, minutes: int) -> CanonicalEvent:
    return CanonicalEvent(
        platform="x",
        platform_post_id=post,
        parent_platform_post_id=parent,
        thread_root_id=root,
        interaction_type="reply",
        created_at=BASE + timedelta(minutes=minutes),
        collected_at=BASE + timedelta(minutes=minutes, seconds=2),
        author=AuthorInfo(platform_user_id=author),
        content=ContentInfo(text=f"reply {post}"),
        relationships=RelationshipInfo(parent_author_id=parent_author),
        source_metadata={"replay": False},
    )


def _seed(repository) -> None:  # noqa: ANN001
    root = CanonicalEvent(
        platform="x", platform_post_id="root-1", thread_root_id="root-1",
        interaction_type="post", created_at=BASE, collected_at=BASE + timedelta(seconds=1),
        author=AuthorInfo(platform_user_id="alice"), content=ContentInfo(text="root post"),
        source_metadata={"replay": False},
    )
    repository.insert_event(root)
    for event in (
        _reply("c1", "root-1", "root-1", "bob", "alice", 5),
        _reply("c2", "root-1", "root-1", "carol", "alice", 6),
        _reply("c3", "c1", "root-1", "dave", "bob", 70),
    ):
        repository.insert_event(event)
        repository.insert_graph_edges(GraphBuilder().edges_from_event(event))


def test_network_analytics_endpoints(repository) -> None:
    _seed(repository)
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(app) as client:
        temporal = client.get("/api/network/temporal", params={"window": "1h", "count": 3})
        influence = client.get("/api/network/influence", params={"metric": "pagerank", "limit": 5})
        communities = client.get("/api/network/communities")
        cascades = client.get("/api/network/cascades")
    assert temporal.status_code == 200
    body = temporal.json()
    assert body["window"] == "1h" and body["window_count"] == 3
    assert any(s["edges"] for s in body["snapshots"])
    assert influence.status_code == 200
    assert influence.json()["metric"] == "pagerank"
    assert influence.json()["nodes"] >= 3
    assert communities.status_code == 200
    assert communities.json()["communities"]
    assert cascades.status_code == 200
    assert cascades.json()["count"] == 1
    assert cascades.json()["max_depth"] == 3
    assert cascades.json()["largest_cascade_id"] == "x:root-1"

    with TestClient(app) as client:
        detail = client.get("/api/network/cascades/x:root-1")
        missing = client.get("/api/network/cascades/x:absent")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["event_count"] == 4
    assert payload["depth"] == 3
    assert [step["depth"] for step in payload["propagation_path"]] == [0, 1, 2]
    assert payload["provenance"] == "observed"
    assert payload["topic_status"] == "unavailable"
    assert missing.status_code == 404
