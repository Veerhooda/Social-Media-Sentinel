from __future__ import annotations

from typing import Any

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.nlp.preprocessing import preprocess_social_text
from app.nlp.schemas import ClassificationResult

SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"


class SentimentAnalyzer:
    def __init__(self, model_name: str = SENTIMENT_MODEL, *, allow_download: bool = False):
        self.model_name = model_name
        self.allow_download = allow_download
        self.tokenizer: Any | None = None
        self.model: Any | None = None

    def _load(self) -> None:
        if self.model is not None:
            return
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, local_files_only=not self.allow_download
        )
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name, local_files_only=not self.allow_download
        )
        self.model.eval()

    def analyze(self, text: str) -> ClassificationResult:
        self._load()
        assert self.model is not None and self.tokenizer is not None
        encoded = self.tokenizer(
            preprocess_social_text(text), return_tensors="pt", truncation=True, max_length=512
        )
        with torch.no_grad():
            probabilities = torch.softmax(self.model(**encoded).logits[0], dim=-1).tolist()
        labels = self._labels(self.model.config.id2label, len(probabilities))
        scores = {label: float(score) for label, score in zip(labels, probabilities, strict=True)}
        label = max(scores, key=scores.get)  # type: ignore[arg-type]
        return ClassificationResult(
            label=label,
            confidence=scores[label],
            scores=scores,
            model_name=self.model_name,
            model_version=getattr(self.model.config, "_commit_hash", None) or "configured-checkpoint",
        )

    @staticmethod
    def _labels(id2label: dict[int, str], count: int) -> list[str]:
        fallback = ["negative", "neutral", "positive"]
        labels = [str(id2label.get(index, fallback[index] if index < 3 else index)).lower() for index in range(count)]
        if all(label.startswith("label_") for label in labels) and count == 3:
            return fallback
        return labels

