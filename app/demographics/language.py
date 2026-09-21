"""Language identification for aggregate demographic reporting.

Priority order (honest about provenance):

1. Platform-observed ``language_code`` already stored on the event. This is
   observed metadata, not an inference, and is reported with confidence 1.0.
2. Text-based identification with ``langdetect`` for events without a stored
   code. Short, emoji-only, URL-only, or mention-only inputs return unknown.
3. Unknown when evidence is insufficient. Language is never guessed from a
   single short post with certainty.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

MIN_TEXT_LENGTH = 20

_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_MENTION_RE = re.compile(r"@\w+")
_HASHTAG_RE = re.compile(r"#\w+")
_EMOJI_RE = re.compile(
    "["
    "\U0001f300-\U0001faf6"
    "\u2600-\u27bf"
    "\u2b00-\u2bff"
    "\ufe00-\ufe0f"
    "\u200d"
    "]+"
)


@dataclass(frozen=True)
class LanguageResult:
    language: str | None
    confidence: float | None
    source: str
    reason: str = ""


def _clean_text(text: str) -> str:
    cleaned = _URL_RE.sub(" ", text)
    cleaned = _MENTION_RE.sub(" ", cleaned)
    cleaned = _HASHTAG_RE.sub(" ", cleaned)
    cleaned = _EMOJI_RE.sub(" ", cleaned)
    return " ".join(cleaned.split())


def _is_insufficient(text: str) -> str | None:
    if not text or not text.strip():
        return "empty text"
    cleaned = _clean_text(text)
    if len(cleaned) < MIN_TEXT_LENGTH:
        return f"insufficient text after cleaning ({len(cleaned)} chars)"
    letters = sum(1 for char in cleaned if char.isalpha())
    if letters < 10:
        return "too few alphabetic characters"
    return None


def identify_language(text: str, *, platform_language: str | None = None) -> LanguageResult:
    """Identify one event's language without overstating certainty."""
    if platform_language:
        code = platform_language.strip().lower()
        if code:
            return LanguageResult(
                language=code,
                confidence=1.0,
                source="platform_observed",
                reason="language code already provided by the platform payload",
            )
    shortfall = _is_insufficient(text)
    if shortfall:
        return LanguageResult(
            language=None, confidence=None, source="unknown", reason=shortfall
        )
    try:
        from langdetect import detect_langs  # type: ignore[import-not-found]
    except ImportError:
        return LanguageResult(
            language=None,
            confidence=None,
            source="unknown",
            reason="language identification runtime unavailable",
        )
    try:
        scored = detect_langs(_clean_text(text))
    except Exception as exc:  # noqa: BLE001 -- langdetect raises LangDetectException on failure
        return LanguageResult(
            language=None, confidence=None, source="unknown", reason=str(exc)
        )
    if not scored:
        return LanguageResult(
            language=None, confidence=None, source="unknown", reason="no candidates"
        )
    top = scored[0]
    if top.prob < 0.55:
        return LanguageResult(
            language=None,
            confidence=None,
            source="unknown",
            reason=f"ambiguous result (top={top.lang} p={top.prob:.2f})",
        )
    return LanguageResult(
        language=str(top.lang).lower(),
        confidence=float(top.prob),
        source="langdetect-lid",
        reason="text-based identification",
    )


def user_language(texts: list[str], *, platform_languages: list[str | None]) -> LanguageResult:
    """Aggregate one user's language across their sampled texts."""
    for code in platform_languages:
        if code and code.strip():
            return LanguageResult(
                language=code.strip().lower(),
                confidence=1.0,
                source="platform_observed",
                reason="platform language code observed on at least one event",
            )
    votes: dict[str, float] = {}
    for text in texts:
        result = identify_language(text)
        if result.language and result.confidence:
            votes[result.language] = votes.get(result.language, 0.0) + result.confidence
    if not votes:
        return LanguageResult(
            language=None, confidence=None, source="unknown",
            reason="no event carried sufficient language evidence",
        )
    best = max(votes, key=lambda key: votes[key])
    total = sum(votes.values())
    return LanguageResult(
        language=best,
        confidence=round(votes[best] / total, 3),
        source="langdetect-lid",
        reason=f"majority vote over {len(texts)} sampled texts",
    )
