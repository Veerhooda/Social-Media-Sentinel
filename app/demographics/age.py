"""Age-bracket inference boundary.

The available evidence (public bios, short posts, no verified birth data)
cannot support credible individual age inference. This module therefore
exposes the stable application interface while honestly returning unknown.

Per SPECS.md, legacy M3Inference must not be forced into the main runtime.
A future text/profile-based model can implement :class:`AgeModel` without
changing callers; until such a model is validated, the default analyzer
returns unknown for every subject and the aggregate dimension reports
UNAVAILABLE rather than fabricated brackets.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.demographics.schemas import AGE_BRACKETS


@dataclass(frozen=True)
class AgeResult:
    bracket: str | None
    confidence: float | None
    source: str
    reason: str = ""


class AgeModel(Protocol):
    def predict(self, bio: str | None, texts: list[str]) -> AgeResult: ...


class UnavailableAgeModel:
    """Default model: insufficient evidence, always unknown."""

    name = "age-unavailable-v1"

    def predict(self, bio: str | None, texts: list[str]) -> AgeResult:  # noqa: ARG002
        return AgeResult(
            bracket=None,
            confidence=None,
            source=self.name,
            reason="insufficient evidence: no validated age model is configured",
        )


class AgeAnalyzer:
    """Age-bracket analyzer behind the demographic service interface."""

    def __init__(self, model: AgeModel | None = None):
        self._model = model or UnavailableAgeModel()

    @property
    def model_name(self) -> str:
        return getattr(self._model, "name", type(self._model).__name__)

    @property
    def available(self) -> bool:
        return not isinstance(self._model, UnavailableAgeModel)

    def analyze(self, bio: str | None, texts: list[str]) -> AgeResult:
        result = self._model.predict(bio, texts)
        if result.bracket is not None and result.bracket not in AGE_BRACKETS:
            return AgeResult(
                bracket=None,
                confidence=None,
                source=self.model_name,
                reason=f"rejected out-of-taxonomy bracket {result.bracket!r}",
            )
        return result
