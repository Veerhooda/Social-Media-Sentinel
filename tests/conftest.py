from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base
from app.db.repositories.social import SocialRepository
from app.models.events import CanonicalEvent
from app.nlp.schemas import (
    ClassificationResult,
    EmotionResult,
    IronyResult,
    NLPResult,
    StanceResult,
)

TEST_DATABASE_URL = "postgresql+psycopg://localhost/social_analytics_test"


class FakeNLPService:
    def analyze(self, event: CanonicalEvent, *, stance_target: str | None = None) -> NLPResult:
        return NLPResult(
            sentiment=ClassificationResult(
                label="positive",
                confidence=0.8,
                scores={"positive": 0.8, "neutral": 0.15, "negative": 0.05},
                model_name="test/sentiment",
                model_version="fixture-v1",
            ),
            emotions=EmotionResult(
                primary_label="excitement",
                scores={"excitement": 0.7, "nervousness": 0.2, "anxiety": 0.2},
                native_scores={"excitement": 0.7, "nervousness": 0.2},
                model_name="test/emotion",
                model_version="fixture-v1",
            ),
            irony=IronyResult(
                is_ironic=False,
                confidence=0.1,
                scores={"non_irony": 0.9, "irony": 0.1},
                model_name="test/irony",
                model_version="fixture-v1",
            ),
            stance=StanceResult(
                target=stance_target,
                label="favor" if stance_target else None,
                confidence=0.75 if stance_target else None,
                scores={"favor": 0.75, "against": 0.1, "none": 0.15} if stance_target else {},
                supported=stance_target is not None,
                reason=None if stance_target else "No supported fixed target was configured",
                model_name="test/stance" if stance_target else None,
                model_version="fixture-v1" if stance_target else None,
            ),
            processed_at=datetime(2026, 9, 20, 10, 16, tzinfo=UTC),
        )


@pytest.fixture(scope="session")
def db_engine():
    try:
        engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
        with engine.connect():
            pass
    except Exception as exc:
        pytest.skip(f"PostgreSQL integration database unavailable: {exc}")
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Session:
    Base.metadata.drop_all(db_engine)
    Base.metadata.create_all(db_engine)
    with Session(db_engine, expire_on_commit=False) as session:
        yield session
        session.rollback()
    Base.metadata.drop_all(db_engine)


@pytest.fixture()
def repository(db_session: Session) -> SocialRepository:
    return SocialRepository(db_session)


@pytest.fixture()
def fake_nlp_service() -> FakeNLPService:
    return FakeNLPService()


@pytest.fixture()
def x_response_payload() -> dict:
    path = Path(__file__).parent / "fixtures" / "x_search_response.json"
    return json.loads(path.read_text(encoding="utf-8"))

