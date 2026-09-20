from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

from app.analytics.schemas import TemporalPoint
from app.models.events import CanonicalEvent
from app.nlp.schemas import NLPResult

AnalyzedEvent = tuple[CanonicalEvent, NLPResult]


def _floor_time(value: datetime, step: timedelta) -> datetime:
    value = value.astimezone(UTC)
    seconds = int(step.total_seconds())
    epoch = int(value.timestamp())
    return datetime.fromtimestamp(epoch - (epoch % seconds), tz=UTC)


def aggregate_rolling(
    records: list[AnalyzedEvent],
    *,
    window: timedelta = timedelta(hours=1),
    step: timedelta = timedelta(minutes=15),
) -> list[TemporalPoint]:
    if not records:
        return []
    ordered = sorted(records, key=lambda item: item[0].created_at)
    first_end = _floor_time(ordered[0][0].created_at, step) + step
    last_end = _floor_time(ordered[-1][0].created_at, step) + step
    points = []
    current = first_end
    while current <= last_end:
        selected = [item for item in ordered if current - window <= item[0].created_at < current]
        if selected:
            points.append(_aggregate_window(selected, current - window, current))
        current += step
    return points


def aggregate_daily(records: list[AnalyzedEvent]) -> list[TemporalPoint]:
    grouped: dict[datetime, list[AnalyzedEvent]] = defaultdict(list)
    for record in records:
        created = record[0].created_at.astimezone(UTC)
        day = datetime(created.year, created.month, created.day, tzinfo=UTC)
        grouped[day].append(record)
    return [
        _aggregate_window(grouped[day], day, day + timedelta(days=1))
        for day in sorted(grouped)
    ]


def _aggregate_window(
    records: list[AnalyzedEvent], window_start: datetime, window_end: datetime
) -> TemporalPoint:
    count = len(records)
    sentiment = Counter(result.sentiment.label for _, result in records)
    emotion_totals: Counter[str] = Counter()
    stance = Counter()
    for _, result in records:
        emotion_totals.update(result.emotions.scores)
        if result.stance.supported and result.stance.label:
            stance[result.stance.label] += 1
    stance_total = sum(stance.values())
    return TemporalPoint(
        window_start=window_start,
        window_end=window_end,
        event_count=count,
        positive_ratio=sentiment["positive"] / count,
        neutral_ratio=sentiment["neutral"] / count,
        negative_ratio=sentiment["negative"] / count,
        emotion_distribution={label: value / count for label, value in emotion_totals.items()},
        anxiety_average=emotion_totals["anxiety"] / count,
        excitement_average=emotion_totals["excitement"] / count,
        irony_rate=sum(result.irony.is_ironic for _, result in records) / count,
        stance_distribution={
            label: value / stance_total for label, value in stance.items()
        } if stance_total else {},
    )

