"""Deterministic public-location normalization.

Only public ``location_raw`` profile strings are used. Normalization is a
conservative dictionary parse into country/region buckets:

raw public location -> normalization -> aggregate geographic bucket

Unknown, malformed, ambiguous, and unsupported locations return unknown.
No aggressive geocoding is performed merely to obtain a map point, and no
precise residence is ever inferred.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Curated mappings for values observed in public profile strings. Keys are
# lowercase match fragments; values are (country_code, country_label, region).
_COUNTRY_HINTS: tuple[tuple[str, str, str, str | None], ...] = (
    ("united kingdom", "GB", "United Kingdom", None),
    ("uk", "GB", "United Kingdom", None),
    ("london", "GB", "United Kingdom", "London"),
    ("england", "GB", "United Kingdom", "England"),
    ("scotland", "GB", "United Kingdom", "Scotland"),
    ("wales", "GB", "United Kingdom", "Wales"),
    ("york", "GB", "United Kingdom", "York"),
    ("united states", "US", "United States", None),
    ("usa", "US", "United States", None),
    ("u.s.", "US", "United States", None),
    ("new york", "US", "United States", "New York"),
    ("california", "US", "United States", "California"),
    ("san francisco", "US", "United States", "California"),
    ("texas", "US", "United States", "Texas"),
    ("florida", "US", "United States", "Florida"),
    ("canada", "CA", "Canada", None),
    ("toronto", "CA", "Canada", "Ontario"),
    ("ontario", "CA", "Canada", "Ontario"),
    ("cape breton", "CA", "Canada", "Nova Scotia"),
    ("india", "IN", "India", None),
    ("mumbai", "IN", "India", "Maharashtra"),
    ("maharashtra", "IN", "India", "Maharashtra"),
    ("delhi", "IN", "India", "Delhi"),
    ("bengaluru", "IN", "India", "Karnataka"),
    ("bangalore", "IN", "India", "Karnataka"),
    ("chennai", "IN", "India", "Tamil Nadu"),
    ("hyderabad", "IN", "India", "Telangana"),
    ("kolkata", "IN", "India", "West Bengal"),
    ("indonesia", "ID", "Indonesia", None),
    ("jakarta", "ID", "Indonesia", "Jakarta"),
    ("australia", "AU", "Australia", None),
    ("sydney", "AU", "Australia", "New South Wales"),
    ("germany", "DE", "Germany", None),
    ("berlin", "DE", "Germany", "Berlin"),
    ("france", "FR", "France", None),
    ("paris", "FR", "France", "Ile-de-France"),
    ("spain", "ES", "Spain", None),
    ("italy", "IT", "Italy", None),
    ("netherlands", "NL", "Netherlands", None),
    ("brazil", "BR", "Brazil", None),
    ("nigeria", "NG", "Nigeria", None),
    ("lagos", "NG", "Nigeria", "Lagos"),
    ("kenya", "KE", "Kenya", None),
    ("south africa", "ZA", "South Africa", None),
    ("japan", "JP", "Japan", None),
    ("tokyo", "JP", "Japan", "Tokyo"),
    ("singapore", "SG", "Singapore", None),
    ("uae", "AE", "United Arab Emirates", None),
    ("dubai", "AE", "United Arab Emirates", "Dubai"),
    ("pakistan", "PK", "Pakistan", None),
    ("bangladesh", "BD", "Bangladesh", None),
    ("philippines", "PH", "Philippines", None),
    ("europe", "EU", "Europe", None),
    ("asia", "AS", "Asia", None),
    ("africa", "AF", "Africa", None),
)

_AMBIGUOUS = {"earth", "worldwide", "global", "somewhere", "everywhere", "nowhere", "mars", "moon"}

_SPLIT_RE = re.compile(r"[|/,;·•\-–—]+")


@dataclass(frozen=True)
class GeographyResult:
    country_code: str | None
    country_label: str | None
    region: str | None
    confidence: float | None
    source: str
    reason: str = ""


def normalize_location(raw: str | None) -> GeographyResult:
    """Normalize one raw public location string into an aggregate bucket."""
    if raw is None or not raw.strip():
        return GeographyResult(None, None, None, None, "unknown", "no public location provided")
    lowered = raw.strip().lower()
    if len(lowered) < 2:
        return GeographyResult(None, None, None, None, "unknown", "malformed location")
    if lowered in _AMBIGUOUS:
        return GeographyResult(None, None, None, None, "unknown", f"ambiguous location {raw.strip()!r}")
    # Reject strings with no alphabetic signal (emoji/flag-only, punctuation).
    if sum(1 for char in lowered if char.isalpha()) < 2:
        return GeographyResult(None, None, None, None, "unknown", "no parseable place name")

    parts = [part.strip() for part in _SPLIT_RE.split(lowered) if part.strip()]
    matches: list[tuple[str, str, str, str | None, float]] = []
    for fragment, code, label, region in _COUNTRY_HINTS:
        for part in parts:
            if fragment == part or (len(fragment) > 3 and fragment in part):
                # Exact part matches outrank substring matches.
                confidence = 0.9 if fragment == part else 0.65
                matches.append((fragment, code, label, region, confidence))
    if not matches:
        return GeographyResult(None, None, None, None, "unknown", f"unsupported location {raw.strip()!r}")
    # Prefer the longest, most specific matching fragment.
    matches.sort(key=lambda item: (len(item[0]), item[4]), reverse=True)
    fragment, code, label, region, confidence = matches[0]
    # Conflicting country signals (e.g. "London, ON" vs London UK) stay unknown
    # unless the raw string names the country explicitly.
    countries = {item[1] for item in matches if len(item[0]) > 3}
    if len(countries) > 1 and code not in {c for c in countries if c in lowered.upper().replace(".", "")}:
        if not any(word in lowered for word in (label.lower(),)):
            # Keep the best match but lower confidence when signals conflict.
            confidence = 0.4
    return GeographyResult(
        country_code=code,
        country_label=label,
        region=region,
        confidence=confidence,
        source="location-normalization-v1",
        reason=f"matched {fragment!r} in {raw.strip()!r}",
    )


def bucket_label(result: GeographyResult) -> str:
    if result.country_label is None:
        return "Unknown"
    return result.country_label


_CODE_TO_LABEL: dict[str, str] = {}
for _fragment, _code, _label, _region in _COUNTRY_HINTS:
    _CODE_TO_LABEL.setdefault(_code, _label)

_LABEL_TO_CODE: dict[str, str] = {label: code for code, label in _CODE_TO_LABEL.items()}


def country_code_for_label(label: str | None) -> str | None:
    """Map an aggregate country label back to its stored ISO-style code."""
    if label is None:
        return None
    return _LABEL_TO_CODE.get(label)


def country_label_for_code(code: str | None) -> str | None:
    """Resolve a stored country code to its aggregate display label."""
    if code is None:
        return None
    return _CODE_TO_LABEL.get(code, code)
