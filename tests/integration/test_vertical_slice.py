from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.dependencies import get_repository
from app.main import create_app
from app.pipeline.service import EventPipeline
from app.platforms.x.mapper import XEventMapper


def test_x_fixture_to_postgres_nlp_graph_temporal_and_api(
    repository, fake_nlp_service, x_response_payload
) -> None:
    event = XEventMapper().map_response(
        x_response_payload,
        collected_at=datetime(2026, 9, 20, 10, 15, 5, tzinfo=UTC),
        mode="fixture",
        query="#OpenData",
    )[0]
    result = EventPipeline(repository, fake_nlp_service).process(event, stance_target="climate")

    assert result.stored is True
    assert result.nlp_processed is True
    assert result.graph_edges_created == 2

    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(app) as client:
        health = client.get("/api/health")
        events = client.get("/api/events")
        sentiment = client.get("/api/analytics/sentiment")
        emotions = client.get("/api/analytics/emotions")
        trends = client.get("/api/analytics/trends")
        network = client.get("/api/network/summary")

    assert health.status_code == 200
    assert health.json()["database"]["status"] == "PASS"
    assert events.json()["items"][0]["platform_post_id"] == "2002"
    assert sentiment.json()["rolling_1h"][0]["positive_ratio"] == 1.0
    assert emotions.json()["rolling_1h"][0]["anxiety_average"] == 0.2
    assert trends.json()["items"][0]["topic"] == "#opendata"
    # The reply and mention target the same user, so persisted relationships aggregate
    # into one weighted directed graph edge.
    assert network.json()["summary"]["nodes"] == 2
    assert network.json()["summary"]["edges"] == 1
