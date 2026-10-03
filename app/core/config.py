from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
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
    frontend_origin: str = "http://localhost:5173"

    database_url: str = "postgresql+psycopg://localhost/social_analytics"

    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    telegram_session_string: str | None = None
    telegram_channels: str = ""
    telegram_poll_interval_seconds: int = Field(default=120, ge=10)
    telegram_max_messages_per_poll: int = Field(default=100, ge=1, le=1000)

    x_bearer_token: str | None = None
    x_client_id: str | None = None
    x_client_secret: str | None = None
    x_query: str = ""
    x_max_results: int = Field(default=100, ge=10, le=100)
    x_stream_enabled: bool = False
    x_search_interval_seconds: int = Field(default=60, ge=10)
    x_max_pages_per_run: int = Field(default=1, ge=1, le=100)

    youtube_api_key: str | None = None
    youtube_video_id: str = ""
    youtube_video_ids: str = ""
    youtube_max_results: int = Field(default=50, ge=1, le=500)
    youtube_max_pages: int = Field(default=2, ge=1, le=20)
    youtube_max_api_calls: int = Field(default=10, ge=1, le=100)
    youtube_poll_interval_seconds: int = Field(default=60, ge=10)

    nlp_batch_size: int = Field(default=16, ge=1, le=128)
    nlp_model_download_enabled: bool = False
    nlp_processing_interval_seconds: int = Field(default=30, ge=1)
    demographics_interval_seconds: int = Field(default=600, ge=10)
    audience_sync_interval_seconds: int = Field(default=900, ge=10)
    graph_interval_seconds: int = Field(default=300, ge=1)
    trend_interval_seconds: int = Field(default=900, ge=1)
    trend_window_minutes: int = Field(default=15, ge=1, le=1440)
    trend_min_documents: int = Field(default=10, ge=2)
    trend_embedding_model: str = "all-MiniLM-L12-v2"
    trend_model_download_enabled: bool = False
    trend_topic_similarity_threshold: float = Field(default=0.4, ge=0, le=1)
    trend_topic_centroid_similarity_threshold: float = Field(default=0.7, ge=0, le=1)
    sentiment_window_minutes: int = Field(default=60, ge=1)

    scheduler_enabled: bool = False
    scheduler_tick_seconds: float = Field(default=1.0, gt=0, le=60)
    analytics_job_batch_size: int = Field(default=100, ge=1, le=10_000)
    analytics_include_replay: bool = False

    @property
    def telegram_channel_list(self) -> list[str]:
        return [item.strip() for item in self.telegram_channels.split(",") if item.strip()]

    @property
    def youtube_video_list(self) -> list[str]:
        items = [item.strip() for item in self.youtube_video_ids.split(",") if item.strip()]
        if self.youtube_video_id.strip() and self.youtube_video_id.strip() not in items:
            items.insert(0, self.youtube_video_id.strip())
        return items

    @field_validator("telegram_api_id", mode="before")
    @classmethod
    def empty_telegram_api_id_is_unconfigured(cls, value):
        return None if value == "" else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
