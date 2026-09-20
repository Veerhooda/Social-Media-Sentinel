from __future__ import annotations

import argparse
import json

from app.core.config import Settings
from app.db.session import SessionLocal
from app.trends.berttrend import BERTrendAnalyzer
from app.trends.repository import TrendRepository
from app.trends.schemas import AnalysisStatus
from app.trends.service import TrendService


def main() -> int:
    parser = argparse.ArgumentParser(description="Run platform-independent BERTrend analysis")
    parser.add_argument("--platform", default=None)
    parser.add_argument("--include-replay", action="store_true")
    parser.add_argument("--allow-model-download", action="store_true")
    parser.add_argument("--min-documents", type=int, default=None)
    args = parser.parse_args()

    settings = Settings(
        trend_model_download_enabled=args.allow_model_download,
        **(
            {"trend_min_documents": args.min_documents}
            if args.min_documents is not None
            else {}
        ),
    )
    analyzer = BERTrendAnalyzer(
        embedding_model_name=settings.trend_embedding_model,
        min_documents=settings.trend_min_documents,
        allow_download=settings.trend_model_download_enabled,
        match_similarity=settings.trend_topic_centroid_similarity_threshold,
    )
    with SessionLocal() as session:
        repository = TrendRepository(session)
        result = TrendService(repository, analyzer=analyzer, settings=settings).run(
            platform=args.platform,
            include_replay=args.include_replay,
        )
        output = {
            **result.model_dump(mode="json"),
            "database_topics": repository.count_topics(),
            "database_measurements": repository.count_measurements(),
        }
    print(json.dumps(output, sort_keys=True))
    if result.status is AnalysisStatus.PASS:
        return 0
    if result.status is AnalysisStatus.INSUFFICIENT_DATA:
        return 3
    if result.status is AnalysisStatus.SKIPPED:
        return 4
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
