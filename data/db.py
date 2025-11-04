"""
Модуль для работы с базой данных (SQLAlchemy + aiosqlite).

Создаёт движок, фабрику сессий и предоставляет зависимость get_session для FastAPI.
Совместим как с SQLite, так и с PostgreSQL (через asyncpg).
"""

from __future__ import annotations

from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import settings


# --- Базовый класс моделей ---
class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей (например User, Video и т.д.)."""
    pass


# --- Движок (engine) ---
engine = create_async_engine(
    settings.async_db_url,
    echo=False,  # можно поставить True для отладки SQL-запросов
    future=True,
)

# --- Фабрика асинхронных сессий ---
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# --- Зависимость FastAPI ---
async def get_session() -> AsyncGenerator[AsyncSession | Any, Any]:
    """
    Асинхронный генератор сессий для FastAPI-зависимостей.

    Пример использования:
        async def handler(session: AsyncSession = Depends(get_session)):
            result = await session.execute(select(User))
            ...

    :yield: активная сессия базы данных.
    """
    async with AsyncSessionLocal() as session:
        yield session


# --- Утилита для CLI или Alembic (при необходимости) ---
async def init_db() -> None:
    """
    Инициализация базы данных: создание всех таблиц по моделям.

    ⚠️ Работает только при использовании SQLite (PostgreSQL требует миграций).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
