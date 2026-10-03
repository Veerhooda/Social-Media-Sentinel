"""Verify the Muse Spark key/model with one tiny structured call.

Usage:  uv run python scripts/audience_lab_live_check.py
Prints PASS/FAIL; never prints the key.
"""
from __future__ import annotations

import os
import sys
import time

from pydantic import BaseModel

from app.audience_lab.config import get_lab_settings
from app.audience_lab.llm import LLMError, MuseSparkClient


class Ping(BaseModel):
    ok: bool
    reply: str


def _fingerprint(value: str | None) -> str:
    if not value:
        return "missing"
    return f"{value[:4]}…{value[-3:]} len={len(value)} pipes={value.count('|')} underscores={value.count('_')}"


def main() -> int:
    settings = get_lab_settings()
    for name in ("META_MODEL_API_KEY", "MUSE_SPARK_API_KEY"):
        if name in os.environ:
            print(f"NOTE: shell environment sets {name} ({_fingerprint(os.environ[name])}); it overrides .env")
    print(f"key in use: {_fingerprint(settings.api_key)}")
    try:
        client = MuseSparkClient(settings)
        started = time.perf_counter()
        result = client.chat_json(
            system="You are a health check. Answer with ok=true and a three-word reply.",
            user="ping", output=Ping, name="health_check", temperature=0,
        )
    except LLMError as exc:
        print(f"FAIL {settings.audience_lab_model} @ {settings.meta_model_base_url}: {exc}")
        return 1
    print(f"PASS {client.model_name} in {time.perf_counter() - started:.1f}s → {result.model_dump()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
