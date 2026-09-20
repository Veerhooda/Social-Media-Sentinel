from __future__ import annotations

from typing import Protocol

from app.core.config import Settings, get_settings
from app.models.events import CanonicalEvent
from app.nlp.emotion import EmotionAnalyzer
from app.nlp.irony import IronyAnalyzer
from app.nlp.schemas import (
    ClassificationResult,
    EmotionResult,
    IronyResult,
    NLPResult,
    StanceResult,
)
from app.nlp.sentiment import SentimentAnalyzer
from app.nlp.stance import FixedTargetStanceAnalyzer


class SentimentProtocol(Protocol):
    def analyze(self, text: str) -> ClassificationResult: ...


class EmotionProtocol(Protocol):
    def analyze(self, text: str) -> EmotionResult: ...


class IronyProtocol(Protocol):
    def analyze(self, text: str) -> IronyResult: ...


class StanceProtocol(Protocol):
    def analyze(self, text: str, target: str | None) -> StanceResult: ...


class NLPService:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        sentiment: SentimentProtocol | None = None,
        emotion: EmotionProtocol | None = None,
        irony: IronyProtocol | None = None,
        stance: StanceProtocol | None = None,
    ):
        settings = settings or get_settings()
        allow_download = settings.nlp_model_download_enabled
        self.sentiment = sentiment or SentimentAnalyzer(allow_download=allow_download)
        self.emotion = emotion or EmotionAnalyzer(allow_download=allow_download)
        self.irony = irony or IronyAnalyzer(allow_download=allow_download)
        self.stance = stance or FixedTargetStanceAnalyzer(allow_download=allow_download)

    def analyze(self, event: CanonicalEvent, *, stance_target: str | None = None) -> NLPResult:
        text = event.content.text
        return NLPResult(
            sentiment=self.sentiment.analyze(text),
            emotions=self.emotion.analyze(text),
            irony=self.irony.analyze(text),
            stance=self.stance.analyze(text, stance_target),
        )

    def analyze_batch(
        self, events: list[CanonicalEvent], *, stance_target: str | None = None
    ) -> list[NLPResult]:
        # Stable batching boundary; model-specific tensor batching can be added without changing callers.
        return [self.analyze(event, stance_target=stance_target) for event in events]

