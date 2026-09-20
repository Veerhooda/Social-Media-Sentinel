from __future__ import annotations

import re

_whitespace = re.compile(r"\s+")
_url = re.compile(r"https?://\S+", re.IGNORECASE)


def preprocess_social_text(text: str) -> str:
    """Apply the Cardiff preprocessing convention without erasing social cues."""
    tokens = []
    for token in _whitespace.split(text.strip()):
        if token.startswith("@") and len(token) > 1:
            tokens.append("@user")
        elif _url.fullmatch(token):
            tokens.append("http")
        else:
            tokens.append(token)
    return " ".join(tokens)

