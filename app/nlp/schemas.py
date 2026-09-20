from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NLPModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClassificationResult(NLPModel):
    label: str
    confidence: float = Field(ge=0, le=1)
    scores: dict[str, float]
    model_name: str
    model_version: str


class EmotionResult(NLPModel):
    primary_label: str | None
    scores: dict[str, float]
    native_scores: dict[str, float]
    model_name: str
    model_version: str


class IronyResult(NLPModel):
    is_ironic: bool
    confidence: float = Field(ge=0, le=1)
    scores: dict[str, float]
    model_name: str
    model_version: str


class StanceResult(NLPModel):
    target: str | None = None
    label: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    scores: dict[str, float] = Field(default_factory=dict)
    supported: bool = False
    reason: str | None = None
    model_name: str | None = None
    model_version: str | None = None


class NLPResult(NLPModel):
    sentiment: ClassificationResult
    emotions: EmotionResult
    irony: IronyResult
    stance: StanceResult
    processed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_persistence(self, event_id: UUID) -> dict[str, Any]:
        model_versions = {
            "sentiment": f"{self.sentiment.model_name}@{self.sentiment.model_version}",
            "emotion": f"{self.emotions.model_name}@{self.emotions.model_version}",
            "irony": f"{self.irony.model_name}@{self.irony.model_version}",
        }
        if self.stance.model_name:
            model_versions["stance"] = f"{self.stance.model_name}@{self.stance.model_version}"
        return {
            "event_id": event_id,
            "sentiment_label": self.sentiment.label,
            "sentiment_confidence": self.sentiment.confidence,
            "sentiment_scores": self.sentiment.scores,
            "is_ironic": self.irony.is_ironic,
            "irony_confidence": self.irony.confidence,
            "irony_scores": self.irony.scores,
            "primary_emotion": self.emotions.primary_label,
            "emotion_scores": {
                "mapped": self.emotions.scores,
                "native": self.emotions.native_scores,
            },
            "stance_target": self.stance.target,
            "stance_label": self.stance.label,
            "stance_confidence": self.stance.confidence,
            "stance_supported": self.stance.supported,
            "model_versions": model_versions,
            "processed_at": self.processed_at,
        }

    @classmethod
    def from_orm_record(cls, record: Any) -> NLPResult:
        model_versions = record.model_versions or {}

        def split_model(key: str) -> tuple[str, str]:
            value = model_versions.get(key, "unknown@unknown")
            name, _, version = value.rpartition("@")
            return (name or value, version or "unknown")

        sentiment_name, sentiment_version = split_model("sentiment")
        emotion_name, emotion_version = split_model("emotion")
        irony_name, irony_version = split_model("irony")
        stance_name, stance_version = split_model("stance")
        emotion_payload = record.emotion_scores or {}
        mapped = emotion_payload.get("mapped", emotion_payload)
        native = emotion_payload.get("native", {})
        return cls(
            sentiment=ClassificationResult(
                label=record.sentiment_label,
                confidence=record.sentiment_confidence,
                scores=record.sentiment_scores,
                model_name=sentiment_name,
                model_version=sentiment_version,
            ),
            emotions=EmotionResult(
                primary_label=record.primary_emotion,
                scores=mapped,
                native_scores=native,
                model_name=emotion_name,
                model_version=emotion_version,
            ),
            irony=IronyResult(
                is_ironic=record.is_ironic,
                confidence=record.irony_confidence,
                scores=record.irony_scores,
                model_name=irony_name,
                model_version=irony_version,
            ),
            stance=StanceResult(
                target=record.stance_target,
                label=record.stance_label,
                confidence=record.stance_confidence,
                supported=record.stance_supported,
                model_name=stance_name if record.stance_supported else None,
                model_version=stance_version if record.stance_supported else None,
                reason=None if record.stance_supported else "No supported fixed target was configured",
            ),
            processed_at=record.processed_at,
        )

