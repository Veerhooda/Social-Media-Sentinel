from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.trends.schemas import MicroBatch, TrendDocument


def floor_to_window(value: datetime, window: timedelta) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("trend timestamps must be timezone-aware")
    utc_value = value.astimezone(UTC)
    seconds = int(window.total_seconds())
    if seconds <= 0:
        raise ValueError("trend window must be positive")
    epoch = int(utc_value.timestamp())
    return datetime.fromtimestamp(epoch - (epoch % seconds), tz=UTC)


def create_micro_batches(
    documents: list[TrendDocument], *, window: timedelta = timedelta(minutes=15)
) -> list[MicroBatch]:
    if not documents:
        return []
    grouped: dict[datetime, list[TrendDocument]] = {}
    for document in sorted(documents, key=lambda item: item.created_at):
        start = floor_to_window(document.created_at, window)
        grouped.setdefault(start, []).append(document)

    first = min(grouped)
    last = max(grouped)
    batches: list[MicroBatch] = []
    current = first
    while current <= last:
        batches.append(
            MicroBatch(
                window_start=current,
                window_end=current + window,
                documents=grouped.get(current, []),
            )
        )
        current += window
    return batches

