from __future__ import annotations

from pathlib import Path

from app.settings import settings


def run_schema_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    service_root = Path(__file__).resolve().parents[1]
    config = Config(str(service_root / "alembic.ini"))
    config.set_main_option("script_location", str(service_root / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(config, "head")
