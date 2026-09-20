from __future__ import annotations

from collections import Counter

from app.analytics.schemas import TrendItem
from app.models.events import CanonicalEvent


def hashtag_trends(events: list[CanonicalEvent], *, limit: int = 20) -> list[TrendItem]:
    counts = Counter(tag.lower() for event in events for tag in event.content.hashtags)
    return [
        TrendItem(topic=f"#{tag}", volume=count, source="hashtag_frequency")
        for tag, count in counts.most_common(limit)
    ]

