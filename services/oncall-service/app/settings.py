from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "oncall-service"
    database_url: str = "postgresql+psycopg://oncall:oncall@localhost:5435/oncall"
    redis_url: str = "redis://localhost:6379/0"
    event_stream_name: str = "incident-platform-events"
    event_consumer_group: str = "oncall-service"
    platform_api_keys: str = "dev-platform-key"
    incidents_service_url: str = "http://localhost:8001"
    internal_api_key: str = "dev-platform-key"


settings = Settings()
