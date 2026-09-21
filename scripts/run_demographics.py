"""Backfill aggregate demographic signals from stored local users/events.

Local-only: reads existing PostgreSQL rows, runs the platform-independent
demographic service, and upserts one row per user. Never contacts X,
Telegram, or any external API/geocoder.
"""
from __future__ import annotations

import argparse
import logging
import time

from sqlalchemy import select

from app.db.session import SessionLocal
from app.demographics.repository import DemographicRepository
from app.demographics.service import DemographicService

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("demographics")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill demographic signals locally")
    parser.add_argument("--limit", type=int, default=10_000)
    parser.add_argument("--platform", default=None)
    parser.add_argument("--semantic-profession", action="store_true",
                        help="use the cached sentence embedding for profession sectors")
    args = parser.parse_args()

    from app.demographics.profession import SectorClassifier

    classifier = SectorClassifier(
        backend="semantic" if args.semantic_profession else "keyword",
        allow_download=False,
    )
    service = DemographicService(sector_classifier=classifier)
    started = time.perf_counter()
    processed = 0
    with SessionLocal() as session:
        repository = DemographicRepository(session)
        missing = repository.list_users_missing_demographics(limit=args.limit)
        if args.platform:
            from app.db.models import SocialUser

            wanted = set(
                session.scalars(
                    select(SocialUser.user_id).where(SocialUser.platform == args.platform)
                ).all()
            )
            missing = [user_id for user_id in missing if user_id in wanted]
        for user_id in missing:
            user, texts, languages = repository.collect_user_texts(user_id)
            if user is None:
                continue
            signal = service.infer_user(
                user_id=user_id,
                platform=user.platform,
                bio=user.bio,
                location_raw=user.location_raw,
                texts=texts,
                platform_languages=languages,
            )
            repository.upsert_signal(signal)
            processed += 1
    elapsed = time.perf_counter() - started
    logger.info("demographic backfill processed=%d elapsed_s=%.1f", processed, elapsed)
    print(f"PROCESSED={processed} ELAPSED_S={elapsed:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
