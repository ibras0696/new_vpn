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
    wg_endpoint: str
    wg_server_public_key: str
    wg_allowed_ips: set[str]
    wg_dns: tuple[str, ...]
    wg_client_address_cidr: str
    wg_preshared_key: str | None
    initial_balance: int
    billing_cost_per_key: int
    billing_enabled: bool
    cleanup_interval_minutes: int


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
        wg_endpoint=os.getenv("WG_ENDPOINT", "vpn.example.com:51820"),
        wg_server_public_key=os.getenv("WG_SERVER_PUBLIC_KEY", "server_pub_key"),
        wg_allowed_ips={item.strip() for item in os.getenv("WG_ALLOWED_IPS", "0.0.0.0/0").split(",") if item.strip()},
        wg_dns=tuple(item.strip() for item in os.getenv("WG_DNS", "1.1.1.1").split(",") if item.strip()),
        wg_client_address_cidr=os.getenv("WG_CLIENT_ADDRESS_CIDR", "10.8.0.0/24"),
        wg_preshared_key=os.getenv("WG_PRESHARED_KEY") or None,
        initial_balance=int(os.getenv("INITIAL_BALANCE", "10")),
        billing_cost_per_key=int(os.getenv("BILLING_COST_PER_KEY", "1")),
        billing_enabled=os.getenv("BILLING_ENABLED", "false").lower() == "true",
        cleanup_interval_minutes=int(os.getenv("CLEANUP_INTERVAL_MINUTES", "10")),
    )
