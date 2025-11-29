from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Set

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Собирает конфигурацию приложения из переменных окружения.

    :param bot_token: токен Telegram-бота.
    :param admin_ids: набор Telegram ID, имеющих доступ к админ-панели.
    :param database_url: строка подключения к базе данных.
    :param max_keys_per_user: максимально допустимое количество ключей у пользователя.
    :param default_key_ttl_hours: срок жизни временного ключа в часах по умолчанию.
    """

    bot_token: str
    admin_ids: Set[int]
    database_url: str
    max_keys_per_user: int
    default_key_ttl_hours: int


def load_settings() -> Settings:
    """Читает переменные окружения и возвращает объект конфигурации.

    :return: экземпляр Settings с валидированными значениями.
    """

    admin_ids_raw = os.getenv("ADMIN_IDS", "")
    admin_ids = {int(item) for item in admin_ids_raw.split(",") if item.strip()}
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", "please_set_bot_token"),
        admin_ids=admin_ids,
        database_url=os.getenv(
            "DATABASE_URL", "postgresql+asyncpg://vpn:vpn@db:5432/vpn"
        ),
        max_keys_per_user=int(os.getenv("MAX_KEYS_PER_USER", "3")),
        default_key_ttl_hours=int(os.getenv("DEFAULT_KEY_TTL_HOURS", "24")),
    )
