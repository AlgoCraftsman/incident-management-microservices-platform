from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "incidents-service"
    database_url: str = "postgresql+psycopg://incidents:incidents@localhost:5433/incidents"
    redis_url: str = "redis://localhost:6379/0"
    event_stream_name: str = "incident-platform-events"
    platform_api_keys: str = "dev-platform-key"


settings = Settings()

