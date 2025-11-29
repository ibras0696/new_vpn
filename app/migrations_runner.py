from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import Settings


def run_migrations(settings: Settings) -> None:
    """Выполняет alembic upgrade head.

    :param settings: конфигурация приложения.
    :return: None.
    """

    config_path = Path(__file__).resolve().parent.parent / "alembic.ini"
    alembic_cfg = Config(str(config_path))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(alembic_cfg, "head")
