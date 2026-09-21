"""Platform-independent demographic service.

Input: existing normalized users/events/profile metadata.
Output: per-user signals (internal) plus aggregate distributions with
confidence/uncertainty. The service never contacts external platforms or
geocoders; everything derives from stored public profile indicators,
bio text, and behavioral text already in PostgreSQL.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from app.demographics.age import AgeAnalyzer
from app.demographics.geography import country_label_for_code, normalize_location
from app.demographics.language import user_language
from app.demographics.profession import SectorClassifier
from app.demographics.schemas import (
    AGE_BRACKETS,
    PROFESSIONAL_SECTORS,
    UNKNOWN_LABEL,
    AggregateSegment,
    DemographicsResponse,
    DimensionDistribution,
    UserDemographicSignal,
)

INFERENCE_SOURCE = "demographic-service-v1"


class DemographicService:
    def __init__(
        self,
        *,
        age_analyzer: AgeAnalyzer | None = None,
        sector_classifier: SectorClassifier | None = None,
    ):
        self.age_analyzer = age_analyzer or AgeAnalyzer()
        # Keyword backend is the deterministic default: no model download, no
        # heavy inference. Callers processing the real corpus may pass a
        # semantic classifier explicitly.
        self.sector_classifier = sector_classifier or SectorClassifier(backend="keyword")

    def infer_user(
        self,
        *,
        user_id: UUID,
        platform: str,
        bio: str | None,
        location_raw: str | None,
        texts: list[str],
        platform_languages: list[str | None],
    ) -> UserDemographicSignal:
        age = self.age_analyzer.analyze(bio, texts)
        geography = normalize_location(location_raw)
        language = user_language(texts, platform_languages=platform_languages)
        profession = self.sector_classifier.classify(bio, texts)
        return UserDemographicSignal(
            user_id=user_id,
            platform=platform,
            age_bracket=age.bracket,
            age_confidence=age.confidence,
            age_source=age.source,
            country=geography.country_label,
            region=geography.region,
            geography_confidence=geography.confidence,
            geography_source=geography.source,
            language=language.language,
            language_confidence=language.confidence,
            language_source=language.source,
            professional_sector=profession.sector,
            profession_confidence=profession.confidence,
            profession_source=profession.source,
            inference_source=INFERENCE_SOURCE,
        )

    def aggregate(self, signals: list[UserDemographicSignal]) -> DemographicsResponse:
        total = len(signals)
        if not total:
            empty = "no subjects with usable profile evidence"
            dimensions = {
                name: DimensionDistribution(
                    dimension=name,  # type: ignore[arg-type]
                    status="INSUFFICIENT_DATA",
                    detail=empty,
                    total_subjects=0,
                    unknown_count=0,
                )
                for name in ("age", "geography", "language", "profession")
            }
            return DemographicsResponse(
                status="INSUFFICIENT_DATA", detail=empty,
                total_subjects=0, dimensions=dimensions,
            )
        dimensions = {
            "age": self._age_dimension(signals, total),
            "geography": self._geography_dimension(signals, total),
            "language": self._language_dimension(signals, total),
            "profession": self._profession_dimension(signals, total),
        }
        available = sum(1 for dim in dimensions.values() if dim.status == "AVAILABLE")
        status: str = "AVAILABLE" if available else "INSUFFICIENT_DATA"
        detail = (
            f"{available}/4 demographic dimensions available"
            if available else "no dimension reached availability"
        )
        return DemographicsResponse(
            status=status,  # type: ignore[arg-type]
            detail=detail,
            total_subjects=total,
            dimensions=dimensions,
            updated_at=datetime.now(UTC),
        )

    def _age_dimension(
        self, signals: list[UserDemographicSignal], total: int
    ) -> DimensionDistribution:
        known = [s for s in signals if s.age_bracket]
        if not self.age_analyzer.available or not known:
            return DimensionDistribution(
                dimension="age",
                status="UNAVAILABLE",
                detail=(
                    "age inference unavailable: no validated age model is "
                    "configured and the available evidence cannot support "
                    "credible brackets"
                ),
                total_subjects=total,
                unknown_count=total,
            )
        return self._distribute(
            "age", total, [(s.age_bracket or UNKNOWN_LABEL, s.age_confidence) for s in signals],
            allowed=list(AGE_BRACKETS),
        )

    def _geography_dimension(
        self, signals: list[UserDemographicSignal], total: int
    ) -> DimensionDistribution:
        pairs = [
            (country_label_for_code(s.country) or UNKNOWN_LABEL if s.country else UNKNOWN_LABEL, s.geography_confidence)
            for s in signals
        ]
        unknown = sum(1 for label, _ in pairs if label == UNKNOWN_LABEL)
        if total - unknown == 0:
            return DimensionDistribution(
                dimension="geography", status="INSUFFICIENT_DATA",
                detail="no subject carried a normalizable public location",
                total_subjects=total, unknown_count=unknown,
            )
        dimension = self._distribute("geography", total, pairs)
        dimension.status = "AVAILABLE"
        dimension.detail = "aggregate of normalized public location strings"
        return dimension

    def _language_dimension(
        self, signals: list[UserDemographicSignal], total: int
    ) -> DimensionDistribution:
        pairs = [(s.language or UNKNOWN_LABEL, s.language_confidence) for s in signals]
        unknown = sum(1 for label, _ in pairs if label == UNKNOWN_LABEL)
        if total - unknown == 0:
            return DimensionDistribution(
                dimension="language", status="INSUFFICIENT_DATA",
                detail="no subject carried sufficient language evidence",
                total_subjects=total, unknown_count=unknown,
            )
        dimension = self._distribute("language", total, pairs)
        dimension.status = "AVAILABLE"
        dimension.detail = "platform-observed codes preferred; text-based identification otherwise"
        return dimension

    def _profession_dimension(
        self, signals: list[UserDemographicSignal], total: int
    ) -> DimensionDistribution:
        pairs = [
            (s.professional_sector or UNKNOWN_LABEL, s.profession_confidence)
            for s in signals
        ]
        unknown = sum(1 for label, _ in pairs if label == UNKNOWN_LABEL)
        if total - unknown == 0:
            return DimensionDistribution(
                dimension="profession", status="INSUFFICIENT_DATA",
                detail="no subject carried classifiable professional signals",
                total_subjects=total, unknown_count=unknown,
            )
        dimension = self._distribute(
            "profession", total, pairs, allowed=list(PROFESSIONAL_SECTORS)
        )
        dimension.status = "AVAILABLE"
        dimension.detail = "inferred interest sectors, not verified occupations"
        return dimension

    def _distribute(
        self,
        dimension: str,
        total: int,
        pairs: list[tuple[str, float | None]],
        *,
        allowed: list[str] | None = None,
    ) -> DimensionDistribution:
        counts: dict[str, int] = defaultdict(int)
        confidences: dict[str, list[float]] = defaultdict(list)
        for label, confidence in pairs:
            counts[label] += 1
            if confidence is not None:
                confidences[label].append(confidence)
        segments = [
            AggregateSegment(
                label=label,
                count=count,
                share=round(count / total, 4),
                avg_confidence=(
                    round(sum(confidences[label]) / len(confidences[label]), 3)
                    if confidences[label] else None
                ),
            )
            for label, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)
            if allowed is None or label in allowed or label == UNKNOWN_LABEL
        ]
        unknown_count = counts.get(UNKNOWN_LABEL, 0)
        return DimensionDistribution(
            dimension=dimension,  # type: ignore[arg-type]
            status="AVAILABLE",
            total_subjects=total,
            unknown_count=unknown_count,
            segments=segments,
            updated_at=datetime.now(UTC),
        )

