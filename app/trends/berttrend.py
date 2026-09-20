from __future__ import annotations

import hashlib
import logging
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import numpy as np
import pandas as pd

from app.trends.schemas import (
    AnalysisStatus,
    BackendAnalysisResult,
    DiscoveredTopic,
    MicroBatch,
)

logger = logging.getLogger(__name__)


class BERTrendAnalyzer:
    """Thin application adapter around BERTrend/BERTopic.

    It accepts platform-independent micro-batches and returns application schemas;
    no platform objects or persistence concerns enter this boundary.
    """

    def __init__(
        self,
        *,
        embedding_model_name: str = "all-MiniLM-L12-v2",
        min_documents: int = 10,
        allow_download: bool = False,
        match_similarity: float = 0.7,
    ):
        self.embedding_model_name = embedding_model_name
        self.min_documents = min_documents
        self.allow_download = allow_download
        self.match_similarity = match_similarity
        try:
            package_version = version("bertrend")
        except PackageNotFoundError:
            package_version = "unavailable"
        self.engine_name = f"BERTrend/{package_version}"

    def analyze(self, batches: list[MicroBatch]) -> BackendAnalysisResult:
        eligible = [batch for batch in batches if batch.document_count >= self.min_documents]
        if not eligible:
            available = sum(batch.document_count for batch in batches)
            return BackendAnalysisResult(
                status=AnalysisStatus.INSUFFICIENT_DATA,
                engine=self.engine_name,
                eligible_batches=0,
                detail=(
                    f"No micro-batch reached the minimum of {self.min_documents} documents; "
                    f"{available} documents were available"
                ),
            )

        try:
            BERTopicModel, BERTrend, SentenceTransformer = self._dependencies()
            all_documents = [document for batch in eligible for document in batch.documents]
            texts = [document.text for document in all_documents]
            embedding_model = SentenceTransformer(
                self.embedding_model_name,
                local_files_only=not self.allow_download,
            )
            embeddings = embedding_model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            smallest_batch = min(batch.document_count for batch in eligible)
            topic_model = BERTopicModel(self._topic_config(smallest_batch))
            trend_model = BERTrend(topic_model=topic_model)

            discovered: list[DiscoveredTopic] = []
            previous_topics: list[DiscoveredTopic] = []
            matched_topics = 0
            offset = 0
            for batch in eligible:
                indexes = list(range(offset, offset + batch.document_count))
                frame = pd.DataFrame(
                    {
                        "document_id": [str(document.event_id) for document in batch.documents],
                        "text": [document.text for document in batch.documents],
                        "source": [document.platform for document in batch.documents],
                        "url": ["" for _ in batch.documents],
                    },
                    index=indexes,
                )
                trend_model.train_topic_models(
                    {pd.Timestamp(batch.window_start): frame},
                    embedding_model=self.embedding_model_name,
                    embeddings=embeddings,
                    save_topic_models=False,
                )
                if (
                    trend_model.last_topic_model is None
                    or trend_model.last_topic_model_timestamp != pd.Timestamp(batch.window_start)
                ):
                    return BackendAnalysisResult(
                        status=AnalysisStatus.FAIL,
                        engine=self.engine_name,
                        topics=discovered,
                        eligible_batches=len(eligible),
                        detail=f"BERTrend failed to produce a model for {batch.window_start.isoformat()}",
                    )
                current_topics = self._extract_topics(
                    trend_model.last_topic_model,
                    batch,
                    embeddings[indexes],
                )
                matched_topics += self._assign_lineages(current_topics, previous_topics)
                discovered.extend(current_topics)
                previous_topics = current_topics
                offset += batch.document_count

            if not discovered:
                return BackendAnalysisResult(
                    status=AnalysisStatus.INSUFFICIENT_DATA,
                    engine=self.engine_name,
                    eligible_batches=len(eligible),
                    detail="BERTrend classified every document as an outlier; no topic was fabricated",
                )
            return BackendAnalysisResult(
                status=AnalysisStatus.PASS,
                engine=self.engine_name,
                topics=discovered,
                eligible_batches=len(eligible),
                matched_topics=matched_topics,
                detail=f"BERTrend discovered {len(discovered)} window topics",
            )
        except Exception as exc:
            logger.exception(
                "BERTrend analysis failed",
                extra={
                    "service": "bertrend",
                    "operation": "topic_analysis",
                    "status": "FAIL",
                    "error": str(exc),
                },
            )
            return BackendAnalysisResult(
                status=AnalysisStatus.FAIL,
                engine=self.engine_name,
                eligible_batches=len(eligible),
                detail=f"{type(exc).__name__}: {exc}",
            )

    @staticmethod
    def _dependencies() -> tuple[type[Any], type[Any], type[Any]]:
        from bertrend.BERTopicModel import BERTopicModel
        from bertrend.BERTrend import BERTrend
        from sentence_transformers import SentenceTransformer

        return BERTopicModel, BERTrend, SentenceTransformer

    @staticmethod
    def _topic_config(document_count: int) -> dict[str, dict[str, Any]]:
        return {
            "global": {"language": "English"},
            "bertopic_model": {
                "top_n_words": 10,
                "verbose": False,
                "representation_model": ["MaximalMarginalRelevance"],
            },
            "umap_model": {
                "n_neighbors": max(2, min(5, document_count - 1)),
                "n_components": max(2, min(5, document_count - 2)),
                "min_dist": 0.0,
                "metric": "cosine",
                "random_state": 42,
            },
            "hdbscan_model": {
                "min_cluster_size": 2,
                "min_samples": 1,
                "metric": "euclidean",
                "cluster_selection_method": "eom",
                "prediction_data": True,
                "cluster_selection_persistence": 0.0,
            },
            "vectorizer_model": {
                "ngram_range": [1, 2],
                "stop_words": True,
                "min_df": 1,
            },
        }

    @staticmethod
    def _extract_topics(
        topic_model: Any, batch: MicroBatch, batch_embeddings: np.ndarray
    ) -> list[DiscoveredTopic]:
        assignments = [int(topic) for topic in topic_model.topics_]
        discovered: list[DiscoveredTopic] = []
        for topic_id in sorted(set(assignments)):
            if topic_id == -1:
                continue
            word_scores = topic_model.get_topic(topic_id) or []
            keywords = [str(word) for word, _score in word_scores if word][:10]
            if not keywords:
                continue
            document_ids = [
                document.event_id
                for document, assigned_topic in zip(
                    batch.documents, assignments, strict=True
                )
                if assigned_topic == topic_id
            ]
            mask = np.asarray(assignments) == topic_id
            centroid = batch_embeddings[mask].mean(axis=0)
            norm = np.linalg.norm(centroid)
            if norm:
                centroid = centroid / norm
            discovered.append(
                DiscoveredTopic(
                    local_topic_id=topic_id,
                    name=" · ".join(keywords[:3]),
                    keywords=keywords,
                    document_ids=document_ids,
                    window_start=batch.window_start,
                    window_end=batch.window_end,
                    centroid=centroid.tolist(),
                )
            )
        return discovered

    def _assign_lineages(
        self,
        current_topics: list[DiscoveredTopic],
        previous_topics: list[DiscoveredTopic],
    ) -> int:
        if not previous_topics:
            for topic in current_topics:
                topic.lineage_key = self._new_lineage_key(topic)
            return 0

        candidates: list[tuple[float, int, int]] = []
        for current_index, current in enumerate(current_topics):
            current_centroid = np.asarray(current.centroid)
            for previous_index, previous in enumerate(previous_topics):
                previous_centroid = np.asarray(previous.centroid)
                score = float(current_centroid @ previous_centroid)
                if score >= self.match_similarity:
                    candidates.append((score, current_index, previous_index))

        used_current: set[int] = set()
        used_previous: set[int] = set()
        matched = 0
        for score, current_index, previous_index in sorted(candidates, reverse=True):
            if current_index in used_current or previous_index in used_previous:
                continue
            current_topics[current_index].lineage_key = previous_topics[
                previous_index
            ].lineage_key
            current_topics[current_index].match_score = score
            used_current.add(current_index)
            used_previous.add(previous_index)
            matched += 1

        for index, topic in enumerate(current_topics):
            if index not in used_current:
                topic.lineage_key = self._new_lineage_key(topic)
        return matched

    @staticmethod
    def _new_lineage_key(topic: DiscoveredTopic) -> str:
        evidence = "|".join(
            [
                topic.window_start.isoformat(),
                str(topic.local_topic_id),
                *sorted(word.casefold() for word in topic.keywords),
            ]
        )
        return hashlib.sha256(evidence.encode("utf-8")).hexdigest()[:32]
