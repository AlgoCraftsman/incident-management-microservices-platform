from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "status-page-service"
    database_url: str = "postgresql+psycopg://status_page:status_page@localhost:5436/status_page"
    redis_url: str = "redis://localhost:6379/0"
    event_stream_name: str = "incident-platform-events"
    event_consumer_group: str = "status-page-service"
    event_consumer_name: str | None = None
    platform_api_keys: str = "dev-platform-key"


settings = Settings()
