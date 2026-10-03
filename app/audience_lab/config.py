"""Settings for the Audience Lab (model-built segments + per-segment reaction agents).

Kept separate from ``app.core.config`` so this module can evolve without
touching shared settings. Values are read from the same ``.env`` file.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AudienceLabSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False)

    # Meta Model API (OpenAI-compatible Chat Completions), https://dev.meta.ai/docs
    # Deliberately NOT reading the generic MODEL_API_KEY: other tools on the machine may export a different key.
    meta_model_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("META_MODEL_API_KEY", "MUSE_SPARK_API_KEY")
    )
    meta_model_base_url: str = "https://api.meta.ai/v1"
    audience_lab_model: str = "muse-spark-1.3-contributor"
    # minimal | low | medium | high | xhigh ; empty = provider default.
    # Judgement calls (segment design, personas, reactions, analysis) use the main effort;
    # bulk mechanical calls (placing profiles into segments) use the fast effort.
    audience_lab_reasoning_effort: str = ""
    audience_lab_fast_reasoning_effort: str = "low"
    audience_lab_timeout_seconds: int = Field(default=300, ge=10, le=900)
    audience_lab_max_retries: int = Field(default=2, ge=0, le=8)
    audience_lab_max_parallel_agents: int = Field(default=8, ge=1, le=32)
    audience_lab_temperature: float = Field(default=0.4, ge=0, le=2)

    # Segmentation knobs (the model decides the actual number inside these bounds)
    audience_lab_min_segments: int = Field(default=3, ge=1, le=30)
    audience_lab_max_segments: int = Field(default=8, ge=1, le=30)
    audience_lab_discovery_sample: int = Field(default=160, ge=10, le=1000)
    audience_lab_assign_batch: int = Field(default=40, ge=5, le=300)
    audience_lab_persona_sample: int = Field(default=25, ge=3, le=200)
    audience_lab_max_image_bytes: int = Field(default=5_000_000, ge=10_000)

    @property
    def api_key(self) -> str | None:
        return self.meta_model_api_key.get_secret_value() if self.meta_model_api_key else None


@lru_cache
def get_lab_settings() -> AudienceLabSettings:
    return AudienceLabSettings()
