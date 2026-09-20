from __future__ import annotations

from typing import Any

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.nlp.preprocessing import preprocess_social_text
from app.nlp.schemas import StanceResult

SUPPORTED_TARGETS = {
    "abortion": "cardiffnlp/twitter-roberta-base-stance-abortion",
    "atheism": "cardiffnlp/twitter-roberta-base-stance-atheism",
    "climate": "cardiffnlp/twitter-roberta-base-stance-climate",
    "feminist": "cardiffnlp/twitter-roberta-base-stance-feminist",
    "hillary": "cardiffnlp/twitter-roberta-base-stance-hillary",
}


class FixedTargetStanceAnalyzer:
    """TweetEval fixed-target stance only; arbitrary targets are rejected explicitly."""

    def __init__(self, *, allow_download: bool = False):
        self.allow_download = allow_download
        self._loaded: dict[str, tuple[Any, Any]] = {}

    def analyze(self, text: str, target: str | None) -> StanceResult:
        if target is None:
            return StanceResult(
                supported=False,
                reason="No stance target configured; arbitrary-target stance is not inferred",
            )
        normalized = target.strip().lower()
        if normalized not in SUPPORTED_TARGETS:
            return StanceResult(
                target=target,
                supported=False,
                reason=(
                    f"Unsupported arbitrary target {target!r}; supported fixed targets are "
                    f"{', '.join(sorted(SUPPORTED_TARGETS))}"
                ),
            )
        model_name = SUPPORTED_TARGETS[normalized]
        tokenizer, model = self._load(normalized, model_name)
        encoded = tokenizer(
            preprocess_social_text(text), return_tensors="pt", truncation=True, max_length=512
        )
        with torch.no_grad():
            probabilities = torch.softmax(model(**encoded).logits[0], dim=-1).tolist()
        labels = [str(model.config.id2label[index]).lower() for index in range(len(probabilities))]
        if all(label.startswith("label_") for label in labels) and len(labels) == 3:
            labels = ["none", "against", "favor"]
        scores = {label: float(score) for label, score in zip(labels, probabilities, strict=True)}
        label = max(scores, key=scores.get)  # type: ignore[arg-type]
        return StanceResult(
            target=normalized,
            label=label,
            confidence=scores[label],
            scores=scores,
            supported=True,
            model_name=model_name,
            model_version=getattr(model.config, "_commit_hash", None) or "configured-checkpoint",
        )

    def _load(self, target: str, model_name: str) -> tuple[Any, Any]:
        if target not in self._loaded:
            tokenizer = AutoTokenizer.from_pretrained(
                model_name, local_files_only=not self.allow_download
            )
            model = AutoModelForSequenceClassification.from_pretrained(
                model_name, local_files_only=not self.allow_download
            )
            model.eval()
            self._loaded[target] = (tokenizer, model)
        return self._loaded[target]


class GeneralTargetStanceAnalyzer:
    def analyze(self, text: str, target: str) -> StanceResult:
        return StanceResult(
            target=target,
            supported=False,
            reason="General-target/NLI stance checkpoint has not yet been validated",
        )

