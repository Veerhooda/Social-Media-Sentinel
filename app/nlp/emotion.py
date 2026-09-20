from __future__ import annotations

from typing import Any

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.nlp.schemas import EmotionResult

EMOTION_MODEL = "SamLowe/roberta-base-go_emotions"


class EmotionAnalyzer:
    def __init__(self, model_name: str = EMOTION_MODEL, *, allow_download: bool = False):
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

    def analyze(self, text: str) -> EmotionResult:
        self._load()
        assert self.model is not None and self.tokenizer is not None
        encoded = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            probabilities = torch.sigmoid(self.model(**encoded).logits[0]).tolist()
        native = {
            str(self.model.config.id2label[index]).lower(): float(score)
            for index, score in enumerate(probabilities)
        }
        mapped = dict(native)
        if "nervousness" in native:
            mapped["anxiety"] = native["nervousness"]
        primary = max(mapped, key=mapped.get) if mapped else None  # type: ignore[arg-type]
        return EmotionResult(
            primary_label=primary,
            scores=mapped,
            native_scores=native,
            model_name=self.model_name,
            model_version=getattr(self.model.config, "_commit_hash", None) or "configured-checkpoint",
        )

