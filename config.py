from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os


class Settings(BaseSettings):
    """
    Конфигурация проекта (бота и базы данных), загружаемая из .env.

    По умолчанию используется SQLite (файл data/bot.db).
    При желании можно переключиться на PostgreSQL, изменив DB_ENGINE и переменные подключения.
    """

    # --- Настройки чтения окружения ---
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Telegram Bot ---
    BOT_TOKEN: str = Field(..., description="Токен Telegram-бота")
    ADMIN_ID: int = Field(..., description="ID администратора Telegram")

    # --- Database ---
    DB_ENGINE: str = Field("sqlite+aiosqlite", description="Движок БД (по умолчанию SQLite)")
    DB_NAME: str = Field("data/bot.db", description="Имя файла SQLite или имя базы PostgreSQL")
    POSTGRES_USER: str | None = Field(None, description="Пользователь PostgreSQL (если используется)")
    POSTGRES_PASSWORD: str | None = Field(None, description="Пароль PostgreSQL (если используется)")
    POSTGRES_HOST: str | None = Field(None, description="Хост PostgreSQL")
    POSTGRES_PORT: int | None = Field(None, description="Порт PostgreSQL")

    # --- Прочее ---
    LOG_LEVEL: str = Field("INFO", description="Уровень логирования")

    # --- XRAY CONFIG ---
    XRAY_CONFIG_PATH: str = Field("/etc/xray/config.json", description="Путь к XRay конфигу")
    XRAY_PORT: int = Field(443, description="Порт VLESS входа")
    XRAY_DOMAIN: str = Field("vpn.example.com", description="Домен для TLS")
    XRAY_SECURITY: str = Field("tls", description="tls / none")
    XRAY_NETWORK: str = Field("tcp", description="tcp / ws / grpc")
    XRAY_API_ENABLED: bool = Field(True, description="Включить API XRay")
    XRAY_API_HOST: str = Field("127.0.0.1", description="Хост API XRay (используй host.docker.internal внутри Docker)")
    XRAY_API_PORT: int = Field(10085, description="Порт API")
    XRAY_INBOUND_TAG: str = Field("vless-inbound", description="Тег inbound-а VLESS для API операций")

    @property
    def async_db_url(self) -> str:
        """
        Возвращает строку подключения для SQLAlchemy (асинхронный драйвер).

        :return: Строка подключения формата:
                 sqlite+aiosqlite:///data/bot.db
                 или postgresql+asyncpg://user:pass@host:port/db
        """
        # Создаём папку data/ при необходимости
        if self.DB_ENGINE.startswith("sqlite"):
            db_dir = os.path.dirname(self.DB_NAME)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            return f"sqlite+aiosqlite:///{self.DB_NAME}"

        # Для PostgreSQL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.DB_NAME}"
        )

    @property
    def sync_db_url(self) -> str:
        """
        Возвращает строку подключения для синхронных клиентов (Alembic).
        """
        if self.DB_ENGINE.startswith("sqlite"):
            return f"sqlite:///{self.DB_NAME}"
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.DB_NAME}"
        )


@lru_cache()
def get_settings() -> Settings:
    """Кэширует объект настроек, чтобы не пересоздавался при каждом обращении."""
    return Settings()


settings = get_settings()

if __name__ == '__main__':
    # .config import settings

    print(settings.async_db_url)
    # -> sqlite+aiosqlite:///data/bot.db

    print(settings.sync_db_url)
    # -> sqlite:///data/bot.db
