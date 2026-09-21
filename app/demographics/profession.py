"""Professional-interest sector classification.

Sectors are *inferred interest sectors*, not verified occupations. Two
backends sit behind one interface:

- ``semantic``: cosine similarity between the subject's public bio plus
  sampled post texts and per-sector prototype descriptions, using the
  already-cached ``all-MiniLM-L12-v2`` sentence embedding already used by
  the trend engine. No new model download is required.
- ``keyword``: deterministic keyword fallback used when the embedding
  runtime is unavailable and in fast unit tests.

Professions are never invented from usernames alone: an empty bio with no
usable text always yields Unknown.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Protocol

EMBEDDING_MODEL_NAME = "all-MiniLM-L12-v2"
_SEMANTIC_THRESHOLD = 0.30
_AMBIGUITY_MARGIN = 0.05

_SECTOR_PROTOTYPES: dict[str, str] = {
    "Technology": "software engineer developer programmer artificial intelligence machine learning data science technology startup IT cloud cybersecurity",
    "Education": "teacher professor lecturer school university college education student academic curriculum classroom",
    "Finance": "finance banking investment trader stock market accounting financial analyst fintech insurance",
    "Healthcare": "doctor nurse healthcare hospital medicine medical patient clinic health surgeon pharmacy",
    "Business": "business entrepreneur founder CEO marketing sales management consultant business development",
    "Media": "journalist reporter media news anchor content creator influencer blogger photography film music artist writer",
    "Government": "government policy civil servant minister administration public service politics diplomat military police",
    "Research": "researcher scientist PhD research lab academic publication scientist laboratory scholar",
}

_SECTOR_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Technology": ("software", "developer", "engineer", "programmer", "coding", "ai ", "machine learning", "data scien", "startup", "tech ", "cloud", "cyber", "blockchain", "bitcoin", "crypto", "app ", "saas", "devops"),
    "Education": ("teacher", "professor", "lecturer", "school", "university", "college", "coach", "tutor", "principal", "educator"),
    "Finance": ("finance", "bank", "investment", "trader", "trading", "stock", "forex", "accountant", "fintech", "insurance", "financial"),
    "Healthcare": ("doctor", "nurse", "healthcare", "hospital", "medical", "medicine", "clinic", "patient", "surgeon", "pharma", "health "),
    "Business": ("entrepreneur", "founder", "ceo", "marketing", "sales", "management", "consultant", "business", "startup founder", "agency"),
    "Media": ("journalist", "reporter", "news", "anchor", "creator", "influencer", "blogger", "photograph", "film", "music", "artist", "writer", "podcast", "youtuber"),
    "Government": ("government", "policy", "civil servant", "minister", "senator", "parliament", "public service", "politics", "diplomat", "military", "police", "ias", "ips"),
    "Research": ("researcher", "scientist", "phd", "research", "laboratory", "publication", "scholar", "postdoc", "thesis"),
}

_TOKEN_RE = re.compile(r"[a-z][a-z\-]+")


@dataclass(frozen=True)
class ProfessionResult:
    sector: str | None
    confidence: float | None
    source: str
    reason: str = ""


class EmbeddingBackend(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


class SectorClassifier:
    def __init__(
        self,
        backend: str = "semantic",
        embedder: EmbeddingBackend | None = None,
        *,
        allow_download: bool = False,
    ):
        if backend not in ("semantic", "keyword"):
            raise ValueError("backend must be 'semantic' or 'keyword'")
        self.backend = backend
        self._embedder = embedder
        self._allow_download = allow_download
        self._prototype_vectors: dict[str, list[float]] | None = None

    @property
    def model_name(self) -> str:
        if self.backend == "keyword":
            return "sector-keywords-v1"
        return f"sector-semantic-{EMBEDDING_MODEL_NAME}"

    def classify(self, bio: str | None, texts: list[str]) -> ProfessionResult:
        profile = " ".join(part for part in [bio or "", *texts[:5]] if part).strip()
        if len(profile) < 12:
            return ProfessionResult(None, None, "insufficient-evidence", "bio and texts too short")
        if self.backend == "keyword" or self._embedder is not None or not self._allow_download:
            if self._embedder is not None:
                return self._classify_semantic(profile)
            if self.backend == "keyword":
                return self._classify_keyword(profile)
            # Semantic requested but downloads disabled and no embedder injected:
            # fall back to keywords and label the source honestly.
            fallback = self._classify_keyword(profile)
            return ProfessionResult(
                sector=fallback.sector,
                confidence=(fallback.confidence * 0.7) if fallback.confidence else None,
                source="sector-keywords-fallback-v1",
                reason="embedding runtime unavailable; keyword fallback",
            )
        try:
            self._ensure_embedder()
        except Exception as exc:  # noqa: BLE001 -- embedding backend load is best-effort
            fallback = self._classify_keyword(profile)
            return ProfessionResult(
                sector=fallback.sector,
                confidence=(fallback.confidence * 0.7) if fallback.confidence else None,
                source="sector-keywords-fallback-v1",
                reason=f"embedding load failed ({exc}); keyword fallback",
            )
        return self._classify_semantic(profile)

    def _ensure_embedder(self) -> EmbeddingBackend:
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer

            self._embedder = SentenceTransformer(
                EMBEDDING_MODEL_NAME, local_files_only=not self._allow_download
            )
        return self._embedder

    def _prototype_vectors_cached(self) -> dict[str, list[float]]:
        if self._prototype_vectors is None:
            embedder = self._ensure_embedder()
            sectors = sorted(_SECTOR_PROTOTYPES)
            vectors = embedder.encode([_SECTOR_PROTOTYPES[name] for name in sectors])
            self._prototype_vectors = dict(zip(sectors, [list(v) for v in vectors], strict=True))
        return self._prototype_vectors

    def _classify_semantic(self, profile: str) -> ProfessionResult:
        embedder = self._embedder or self._ensure_embedder()
        prototypes = self._prototype_vectors_cached()
        subject = list(embedder.encode([profile])[0])
        scored = sorted(
            ((name, _cosine(subject, vector)) for name, vector in prototypes.items()),
            key=lambda item: item[1],
            reverse=True,
        )
        best_name, best_score = scored[0]
        runner_up = scored[1][1] if len(scored) > 1 else 0.0
        if best_score < _SEMANTIC_THRESHOLD:
            return ProfessionResult(None, None, self.model_name, f"max similarity {best_score:.2f} below threshold")
        confidence = round(min(0.95, max(0.35, (best_score - runner_up) * 2 + best_score * 0.5)), 3)
        if best_score - runner_up < _AMBIGUITY_MARGIN:
            return ProfessionResult("Other", confidence * 0.7, self.model_name, "ambiguous between top sectors")
        return ProfessionResult(best_name, confidence, self.model_name, f"cosine {best_score:.2f}")

    def _classify_keyword(self, profile: str) -> ProfessionResult:
        lowered = f" {profile.lower()} "
        tokens = set(_TOKEN_RE.findall(profile.lower()))
        scored: list[tuple[str, int]] = []
        for sector, keywords in _SECTOR_KEYWORDS.items():
            hits = sum(1 for keyword in keywords if keyword in lowered)
            if hits:
                scored.append((sector, hits))
        if not scored:
            # Single-token heuristic for terse bios like "Trader" or "Doctor".
            for sector, keywords in _SECTOR_KEYWORDS.items():
                stems = {word[:5] for keyword in keywords for word in keyword.split()}
                if tokens & stems:
                    scored.append((sector, 1))
        if not scored:
            return ProfessionResult(None, None, "sector-keywords-v1", "no sector keywords matched")
        scored.sort(key=lambda item: item[1], reverse=True)
        best_name, best_hits = scored[0]
        if len(scored) > 1 and scored[1][1] == best_hits:
            return ProfessionResult("Other", 0.4, "sector-keywords-v1", "tied sectors")
        confidence = round(min(0.9, 0.45 + 0.15 * best_hits), 3)
        return ProfessionResult(best_name, confidence, "sector-keywords-v1", f"{best_hits} keyword hits")


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)
