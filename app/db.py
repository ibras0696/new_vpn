from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.models import Base

SessionMaker = async_sessionmaker[AsyncSession]


def get_engine(settings: Settings):
    """Создаёт асинхронный движок SQLAlchemy.

    :param settings: конфигурация приложения.
    :return: асинхронный движок для работы с БД.
    """

    return create_async_engine(settings.database_url, future=True, echo=False)


def get_session_maker(settings: Settings) -> SessionMaker:
    """Возвращает фабрику сессий.

    :param settings: конфигурация приложения.
    :return: фабрика AsyncSession.
    """

    engine = get_engine(settings)
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_models(session_maker: SessionMaker) -> None:
    """Гарантирует, что таблицы созданы.

    :param session_maker: фабрика сессий.
    :return: None.
    """

    async with session_maker() as session:
        async with session.bind.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
