from __future__ import annotations

from typing import Any

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.nlp.preprocessing import preprocess_social_text
from app.nlp.schemas import IronyResult

IRONY_MODEL = "cardiffnlp/twitter-roberta-base-irony"


class IronyAnalyzer:
    def __init__(
        self, model_name: str = IRONY_MODEL, *, threshold: float = 0.5, allow_download: bool = False
    ):
        self.model_name = model_name
        self.threshold = threshold
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

    def analyze(self, text: str) -> IronyResult:
        self._load()
        assert self.model is not None and self.tokenizer is not None
        encoded = self.tokenizer(
            preprocess_social_text(text), return_tensors="pt", truncation=True, max_length=512
        )
        with torch.no_grad():
            probabilities = torch.softmax(self.model(**encoded).logits[0], dim=-1).tolist()
        labels = [str(self.model.config.id2label[index]).lower().replace(" ", "_") for index in range(len(probabilities))]
        if all(label.startswith("label_") for label in labels) and len(labels) == 2:
            labels = ["non_irony", "irony"]
        scores = {label: float(score) for label, score in zip(labels, probabilities, strict=True)}
        irony_score = scores.get("irony", scores.get("ironic", probabilities[-1]))
        return IronyResult(
            is_ironic=irony_score >= self.threshold,
            confidence=float(irony_score),
            scores=scores,
            model_name=self.model_name,
            model_version=getattr(self.model.config, "_commit_hash", None) or "configured-checkpoint",
        )

