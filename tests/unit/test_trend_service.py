from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.core.config import Settings
from app.trends.schemas import SignalStatus, TopicCatalogEntry
from app.trends.service import TrendService


def service() -> TrendService:
    return TrendService(
        repository=SimpleNamespace(),  # type: ignore[arg-type]
        analyzer=SimpleNamespace(engine_name="test"),  # type: ignore[arg-type]
        settings=Settings(trend_topic_similarity_threshold=0.4),
    )


def test_topic_matching_requires_configured_keyword_evidence() -> None:
    catalog = [
        TopicCatalogEntry(
            topic_id=1,
            topic_key="one",
            name="open models",
            keywords=["openai", "models", "research", "chatgpt"],
        ),
        TopicCatalogEntry(
            topic_id=2,
            topic_key="two",
            name="energy",
            keywords=["grid", "energy", "power"],
        ),
    ]
    assert service()._find_match(
        ["openai", "models", "research", "agents"], catalog
    ).topic_id == 1
    assert service()._find_match(["unrelated", "subject"], catalog) is None


def test_velocity_acceleration_and_signal_status_require_prior_evidence() -> None:
    window = timedelta(minutes=15)
    current = datetime(2026, 9, 20, 10, 15, tzinfo=UTC)
    previous_start = current - window
    first = TrendService._measurement_values(
        document_count=3, previous=None, window=window, current_window_start=current
    )
    rising = TrendService._measurement_values(
        document_count=4,
        previous=SimpleNamespace(
            document_count=3, velocity_score=None, window_start=previous_start
        ),
        window=window,
        current_window_start=current,
    )
    stable = TrendService._measurement_values(
        document_count=4,
        previous=SimpleNamespace(
            document_count=4, velocity_score=4.0, window_start=previous_start
        ),
        window=window,
        current_window_start=current,
    )
    cooling = TrendService._measurement_values(
        document_count=2,
        previous=SimpleNamespace(
            document_count=4, velocity_score=4.0, window_start=previous_start
        ),
        window=window,
        current_window_start=current,
    )

    assert first == (None, None, None, SignalStatus.EMERGING)
    assert rising == (1 / 3, 4.0, None, SignalStatus.RISING)
    assert stable == (0.0, 0.0, -16.0, SignalStatus.SUSTAINED)
    assert cooling == (-0.5, -8.0, -48.0, SignalStatus.COOLING)


def test_velocity_uses_actual_elapsed_source_time_across_empty_windows() -> None:
    previous_start = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
    current_start = previous_start + timedelta(minutes=45)
    result = TrendService._measurement_values(
        document_count=3,
        previous=SimpleNamespace(
            document_count=8, velocity_score=None, window_start=previous_start
        ),
        window=timedelta(minutes=15),
        current_window_start=current_start,
    )
    assert result == (-0.625, -5 / 0.75, None, SignalStatus.COOLING)
