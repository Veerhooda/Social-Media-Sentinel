"""Persistence for aggregate demographic signals.

Reuses the existing ``user_demographics`` table. One migration adds the
minimum missing columns (language/geography confidence, inference source,
model versions, updated timestamp) so every prediction carries provenance
and uncertainty.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import SocialEvent, SocialUser, UserDemographic
from app.demographics.geography import country_code_for_label
from app.demographics.schemas import UserDemographicSignal


class DemographicRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_signal(self, signal: UserDemographicSignal) -> UUID:
        values = {
            "user_id": signal.user_id,
            "age_bracket": signal.age_bracket,
            "age_confidence": signal.age_confidence,
            "inferred_country": country_code_for_label(signal.country),
            "inferred_region": signal.region,
            "primary_language": signal.language,
            "professional_sector": signal.professional_sector,
            "profession_confidence": signal.profession_confidence,
            "language_confidence": signal.language_confidence,
            "geography_confidence": signal.geography_confidence,
            "inference_source": signal.inference_source,
            "model_versions": {
                "age": signal.age_source,
                "geography": signal.geography_source,
                "language": signal.language_source,
                "profession": signal.profession_source,
            },
        }
        statement = insert(UserDemographic).values(**values)
        statement = statement.on_conflict_do_update(
            constraint="uq_demographics_user",
            set_={**values, "updated_at": func.now()},
        ).returning(UserDemographic.demographic_id)
        demographic_id = self.session.execute(statement).scalar_one()
        self.session.commit()
        return demographic_id

    def count_subjects(self) -> int:
        return (
            self.session.execute(
                select(func.count()).select_from(UserDemographic)
            ).scalar_one()
        )

    def latest_processed_at(self) -> datetime | None:
        value = self.session.execute(
            select(func.max(UserDemographic.processed_at))
        ).scalar_one_or_none()
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    def list_subjects(
        self, *, platform: str | None = None, limit: int = 10_000
    ) -> list[UserDemographic]:
        query = select(UserDemographic, SocialUser).join(
            SocialUser, SocialUser.user_id == UserDemographic.user_id
        )
        if platform:
            query = query.where(SocialUser.platform == platform)
        rows = self.session.execute(query.limit(limit)).all()
        return [row[0] for row in rows]

    def subject_platform(self, demographic: UserDemographic) -> str | None:
        return self.session.execute(
            select(SocialUser.platform).where(SocialUser.user_id == demographic.user_id)
        ).scalar_one_or_none()

    def collect_user_texts(
        self, user_id: UUID, *, limit: int = 5
    ) -> tuple[SocialUser | None, list[str], list[str | None]]:
        user = self.session.execute(
            select(SocialUser).where(SocialUser.user_id == user_id)
        ).scalar_one_or_none()
        if user is None:
            return None, [], []
        rows = self.session.execute(
            select(SocialEvent.content_text, SocialEvent.language_code)
            .where(
                SocialEvent.author_id == user_id,
                SocialEvent.content_text.isnot(None),
            )
            .order_by(SocialEvent.created_at.desc())
            .limit(limit)
        ).all()
        texts = [text for text, _ in rows if text]
        languages = [language for _, language in rows]
        return user, texts, languages

    def list_users_missing_demographics(self, *, limit: int = 10_000) -> list[UUID]:
        rows = self.session.execute(
            select(SocialUser.user_id)
            .outerjoin(UserDemographic, UserDemographic.user_id == SocialUser.user_id)
            .where(UserDemographic.user_id.is_(None))
            .limit(limit)
        ).all()
        return [row[0] for row in rows]
