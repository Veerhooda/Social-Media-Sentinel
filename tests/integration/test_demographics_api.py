"""Integration: fixture users -> demographics -> PostgreSQL -> aggregate API."""
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_repository
from app.demographics.profession import SectorClassifier
from app.demographics.repository import DemographicRepository
from app.demographics.service import DemographicService
from app.main import create_app
from app.models.events import AuthorInfo, CanonicalEvent, ContentInfo

pytestmark = pytest.mark.integration


def _event(platform_post_id: str, user_id: str, text: str, **author) -> CanonicalEvent:
    return CanonicalEvent(
        platform="x",
        platform_post_id=platform_post_id,
        interaction_type="post",
        created_at=datetime(2026, 9, 20, 12, 0, tzinfo=UTC),
        collected_at=datetime(2026, 9, 20, 12, 0, 2, tzinfo=UTC),
        author=AuthorInfo(platform_user_id=user_id, **author),
        content=ContentInfo(text=text, language="en"),
        source_metadata={"replay": True},
    )


def test_demographic_persistence_aggregation_and_api(repository) -> None:
    repository.insert_event(_event(
        "demo-1", "demo-user-1", "Shipping machine learning infrastructure all week.",
        username="ml_builder", bio="Software developer working on AI infrastructure",
        location_raw="Bengaluru, India",
    ))
    repository.insert_event(_event(
        "demo-2", "demo-user-2", "Match day atmosphere is unreal.",
        username="fan_account", bio="Football fan", location_raw="London, UK",
    ))

    service = DemographicService(sector_classifier=SectorClassifier(backend="keyword"))
    demographic_repository = DemographicRepository(repository.session)
    for user_id in demographic_repository.list_users_missing_demographics():
        user, texts, languages = demographic_repository.collect_user_texts(user_id)
        assert user is not None
        demographic_repository.upsert_signal(service.infer_user(
            user_id=user_id, platform=user.platform, bio=user.bio,
            location_raw=user.location_raw, texts=texts, platform_languages=languages,
        ))
    assert demographic_repository.count_subjects() == 2

    # Idempotency: reprocessing the same users must not duplicate rows.
    for user_id in [row.user_id for row in demographic_repository.list_subjects()]:
        user, texts, languages = demographic_repository.collect_user_texts(user_id)
        assert user is not None
        demographic_repository.upsert_signal(service.infer_user(
            user_id=user_id, platform=user.platform, bio=user.bio,
            location_raw=user.location_raw, texts=texts, platform_languages=languages,
        ))
    assert demographic_repository.count_subjects() == 2

    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(app) as client:
        overview = client.get("/api/analytics/demographics")
        age = client.get("/api/analytics/demographics/age")
        language = client.get("/api/analytics/demographics/language")
        geography = client.get("/api/analytics/demographics/geography")
        profession = client.get("/api/analytics/demographics/profession")

    assert overview.status_code == 200
    body = overview.json()
    assert body["total_subjects"] == 2
    assert body["dimensions"]["age"]["status"] == "UNAVAILABLE"
    assert body["dimensions"]["age"]["unknown_count"] == 2
    assert body["dimensions"]["language"]["status"] == "AVAILABLE"
    assert body["dimensions"]["geography"]["status"] == "AVAILABLE"
    countries = {segment["label"] for segment in body["dimensions"]["geography"]["segments"]}
    assert {"India", "United Kingdom"} <= countries
    assert all(age.status_code == 200 for age in (age, language, geography, profession))
    assert profession.json()["status"] == "AVAILABLE"
    # Aggregate-only: no per-user identifiers leak through the API.
    assert "platform_user_id" not in overview.text
    assert "ml_builder" not in overview.text
