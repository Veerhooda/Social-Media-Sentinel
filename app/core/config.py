from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    database_url: str = "postgresql+psycopg://localhost/social_analytics"

    x_bearer_token: str | None = None
    x_client_id: str | None = None
    x_client_secret: str | None = None
    x_query: str = ""
    x_max_results: int = Field(default=100, ge=10, le=100)
    x_stream_enabled: bool = False
    x_search_interval_seconds: int = Field(default=60, ge=10)

    nlp_batch_size: int = Field(default=16, ge=1, le=128)
    nlp_model_download_enabled: bool = False
    graph_interval_seconds: int = Field(default=300, ge=1)
    trend_interval_seconds: int = Field(default=900, ge=1)
    sentiment_window_minutes: int = Field(default=60, ge=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()

