from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.trends.batching import create_micro_batches, floor_to_window
from app.trends.schemas import TrendDocument


def document(at: datetime, text: str = "topic text") -> TrendDocument:
    return TrendDocument(
        event_id=uuid4(),
        platform="x",
        text=text,
        created_at=at,
        sentiment_label="positive",
    )


def test_creates_chronological_fifteen_minute_micro_batches_with_empty_gap() -> None:
    start = datetime(2026, 9, 20, 10, 2, tzinfo=UTC)
    batches = create_micro_batches(
        [document(start), document(start + timedelta(minutes=31))],
        window=timedelta(minutes=15),
    )

    assert [batch.window_start.minute for batch in batches] == [0, 15, 30]
    assert [batch.document_count for batch in batches] == [1, 0, 1]
    assert all(batch.window_end - batch.window_start == timedelta(minutes=15) for batch in batches)


def test_empty_document_list_produces_no_batches() -> None:
    assert create_micro_batches([]) == []


def test_floor_to_window_requires_aware_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        floor_to_window(datetime(2026, 9, 20, 10, 0), timedelta(minutes=15))

