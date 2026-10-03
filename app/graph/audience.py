"""Public profile coverage and aggregate cohort evidence for graph nodes."""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from app.demographics.geography import country_label_for_code
from app.graph.schemas import AudienceDimension, GraphCoverage, PublicNodeProfile

DIMENSIONS = ("language", "geography", "profession")
MIN_KNOWN = 3


def public_profile(record: tuple[Any, Any] | None) -> PublicNodeProfile:
    if record is None:
        return PublicNodeProfile()
    user, _ = record
    return PublicNodeProfile(
        status="stored_profile",
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url if user.avatar_url and user.avatar_url.startswith("https://") else None,
        is_verified=user.is_verified,
    )


def coverage(nodes: set[str], records: Mapping[str, tuple[Any, Any]]) -> GraphCoverage:
    available = [records[node] for node in nodes if node in records]
    return GraphCoverage(
        total_nodes=len(nodes),
        stored_profiles=len(available),
        referenced_only=len(nodes) - len(available),
        avatar_available=sum(bool(public_profile(record).avatar_url) for record in available),
        demographic_records=sum(record[1] is not None for record in available),
    )


def audience_dimensions(
    nodes: set[str], records: Mapping[str, tuple[Any, Any]], *, min_known: int = MIN_KNOWN
) -> dict[str, AudienceDimension]:
    result: dict[str, AudienceDimension] = {}
    for dimension in DIMENSIONS:
        counts: Counter[str] = Counter()
        for node in nodes:
            record = records.get(node)
            demographic = record[1] if record else None
            label = None
            if demographic is not None:
                if dimension == "language":
                    label = demographic.primary_language
                elif dimension == "geography":
                    label = country_label_for_code(demographic.inferred_country)
                else:
                    label = demographic.professional_sector
            if label and label != "Unknown":
                counts[str(label)] += 1
        known = sum(counts.values())
        # A cohort may have three known members but only one member in a
        # particular category. Suppress that small cell, not merely the whole
        # dimension when known coverage is low.
        visible = {label: count for label, count in counts.items() if count >= min_known}
        result[dimension] = AudienceDimension(
            status="AVAILABLE" if visible else "INSUFFICIENT_DATA",
            known=known,
            unknown=len(nodes) - known,
            suppressed=known - sum(visible.values()),
            distribution=visible,
        )
    return result
