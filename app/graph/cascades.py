"""Observed interaction cascade reconstruction.

Cascades are built only from stored parent/reference relationships
(``parent_platform_post_id`` chains grouped under ``thread_root_id``).
Missing parents are never inferred: when referenced posts are absent from
storage the cascade is marked partially observable and only the observed
subset is returned.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CascadeEvent:
    event_id: UUID
    platform: str
    platform_post_id: str
    parent_platform_post_id: str | None
    thread_root_id: str | None
    author_label: str
    created_at: datetime
    interaction_type: str
    sentiment: str | None = None
    emotion: str | None = None
    is_ironic: bool | None = None


@dataclass
class ObservedCascade:
    cascade_id: str
    platform: str
    root_platform_post_id: str
    events: list[CascadeEvent] = field(default_factory=list)
    missing_parents: int = 0

    @property
    def event_count(self) -> int:
        return len(self.events)

    @property
    def depth(self) -> int:
        by_post = {event.platform_post_id: event for event in self.events}
        children: dict[str, list[str]] = {}
        for event in self.events:
            if (
                event.parent_platform_post_id in by_post
                and by_post[event.parent_platform_post_id].created_at <= event.created_at
            ):
                children.setdefault(event.parent_platform_post_id, []).append(event.platform_post_id)
        roots = [
            event.platform_post_id
            for event in self.events
            if event.parent_platform_post_id not in by_post
            or by_post[event.parent_platform_post_id].created_at > event.created_at
        ]

        def longest(post_id: str, visiting: frozenset[str]) -> int:
            if post_id in visiting:
                return 0
            best = 0
            for child in children.get(post_id, []):
                best = max(best, longest(child, visiting | {post_id}))
            return best + 1

        return max((longest(root, frozenset()) for root in roots), default=0)

    @property
    def width(self) -> int:
        counts = Counter(
            event.parent_platform_post_id for event in self.events if event.parent_platform_post_id
        )
        siblings = len([event for event in self.events if not event.parent_platform_post_id])
        return max([siblings, *counts.values()], default=0)

    @property
    def duration_seconds(self) -> float | None:
        if len(self.events) < 2:
            return None
        ordered = sorted(self.events, key=lambda item: item.created_at)
        return (ordered[-1].created_at - ordered[0].created_at).total_seconds()

    @property
    def participants(self) -> set[str]:
        return {event.author_label for event in self.events}

    @property
    def provenance(self) -> str:
        return "partially observable" if self.missing_parents else "observed"


def reconstruct_cascades(events: list[CascadeEvent]) -> list[ObservedCascade]:
    """Group stored events into observed cascades by thread root."""
    by_post: dict[tuple[str, str], CascadeEvent] = {
        (event.platform, event.platform_post_id): event for event in events
    }
    groups: dict[tuple[str, str], list[CascadeEvent]] = {}
    for event in events:
        root = event.thread_root_id or event.platform_post_id
        groups.setdefault((event.platform, root), []).append(event)
    cascades: list[ObservedCascade] = []
    for (platform, root), members in groups.items():
        missing = sum(
            1
            for event in members
            if event.parent_platform_post_id
            and (
                (platform, event.parent_platform_post_id) not in by_post
                or by_post[(platform, event.parent_platform_post_id)].created_at > event.created_at
            )
        )
        cascades.append(
            ObservedCascade(
                cascade_id=f"{platform}:{root}",
                platform=platform,
                root_platform_post_id=root,
                events=sorted(members, key=lambda item: item.created_at),
                missing_parents=missing,
            )
        )
    cascades.sort(key=lambda item: item.event_count, reverse=True)
    return cascades


def propagation_path(
    cascade: ObservedCascade, *, communities: dict[str, int] | None = None
) -> list[dict]:
    """Longest root-to-leaf chain; chronological; no invented edges."""
    communities = communities or {}
    by_post = {event.platform_post_id: event for event in cascade.events}
    children: dict[str, list[CascadeEvent]] = {}
    for event in cascade.events:
        if (
            event.parent_platform_post_id in by_post
            and by_post[event.parent_platform_post_id].created_at <= event.created_at
        ):
            children.setdefault(event.parent_platform_post_id, []).append(event)
    roots = [
        event for event in cascade.events
        if event.parent_platform_post_id not in by_post
        or by_post[event.parent_platform_post_id].created_at > event.created_at
    ]

    def longest(event: CascadeEvent, visiting: frozenset[str]) -> list[CascadeEvent]:
        best: list[CascadeEvent] = [event]
        for child in sorted(children.get(event.platform_post_id, []), key=lambda item: item.created_at):
            if child.platform_post_id in visiting:
                continue
            candidate = [event, *longest(child, visiting | {event.platform_post_id})]
            if len(candidate) > len(best):
                best = candidate
        return best

    path = max((longest(root, frozenset()) for root in roots), key=len, default=[])
    steps = []
    for depth, event in enumerate(path):
        steps.append(
            {
                "depth": depth,
                "node_id": event.author_label,
                "event_id": event.event_id,
                "platform_post_id": event.platform_post_id,
                "interaction_type": event.interaction_type,
                "occurred_at": event.created_at,
                "community": communities.get(event.author_label),
                "sentiment": event.sentiment,
                "emotion": event.emotion,
                "is_ironic": event.is_ironic,
            }
        )
    return steps


def sentiment_composition(cascade: ObservedCascade) -> tuple[dict[str, int], dict[str, float]]:
    counts = Counter(event.sentiment for event in cascade.events if event.sentiment)
    total = sum(counts.values())
    if not total:
        return {}, {}
    return dict(counts), {label: round(count / total, 4) for label, count in counts.items()}
