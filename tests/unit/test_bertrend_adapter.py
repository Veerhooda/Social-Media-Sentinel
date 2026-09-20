import math
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.trends.berttrend import BERTrendAnalyzer
from app.trends.schemas import (
    AnalysisStatus,
    DiscoveredTopic,
    MicroBatch,
    TrendDocument,
)


def test_bertrend_import_and_application_adapter_are_available() -> None:
    analyzer = BERTrendAnalyzer(min_documents=2)
    BERTopicModel, BERTrend, SentenceTransformer = analyzer._dependencies()
    assert BERTopicModel.__name__ == "BERTopicModel"
    assert BERTrend.__name__ == "BERTrend"
    assert SentenceTransformer.__name__ == "SentenceTransformer"
    assert analyzer.engine_name.startswith("BERTrend/")


def test_bertrend_reports_insufficient_data_without_loading_model() -> None:
    start = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
    batch = MicroBatch(
        window_start=start,
        window_end=start + timedelta(minutes=15),
        documents=[
            TrendDocument(
                event_id=uuid4(),
                platform="x",
                text="one document",
                created_at=start,
            )
        ],
    )
    result = BERTrendAnalyzer(min_documents=2).analyze([batch])
    assert result.status is AnalysisStatus.INSUFFICIENT_DATA
    assert result.topics == []
    assert "minimum of 2" in result.detail


def test_centroid_lineage_matching_is_one_to_one_and_thresholded() -> None:
    start = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
    previous = [
        DiscoveredTopic(
            local_topic_id=0,
            name="previous",
            keywords=["chatgpt"],
            document_ids=[uuid4()],
            window_start=start,
            window_end=start + timedelta(minutes=15),
            lineage_key="existing-lineage",
            centroid=[1.0, 0.0],
        )
    ]
    current = [
        DiscoveredTopic(
            local_topic_id=0,
            name="strongest",
            keywords=["chatgpt", "models"],
            document_ids=[uuid4()],
            window_start=start + timedelta(minutes=15),
            window_end=start + timedelta(minutes=30),
            centroid=[0.726, math.sqrt(1 - 0.726**2)],
        ),
        DiscoveredTopic(
            local_topic_id=1,
            name="second candidate",
            keywords=["chatgpt", "agents"],
            document_ids=[uuid4()],
            window_start=start + timedelta(minutes=15),
            window_end=start + timedelta(minutes=30),
            centroid=[0.704, math.sqrt(1 - 0.704**2)],
        ),
    ]

    matched = BERTrendAnalyzer(min_documents=2, match_similarity=0.7)._assign_lineages(
        current, previous
    )

    assert matched == 1
    assert current[0].lineage_key == "existing-lineage"
    assert current[0].match_score == 0.726
    assert current[1].lineage_key != "existing-lineage"
    assert current[1].match_score is None
