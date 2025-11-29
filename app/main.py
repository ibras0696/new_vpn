from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from app.bot.filters import AdminFilter
from app.bot.handlers import admin, common, user_keys
from app.bot.middleware import ContextMiddleware
from app.config import Settings, load_settings
from app.db import get_session_maker
from app.migrations_runner import run_migrations
from app.services import KeyService


async def cleanup_worker(settings: Settings, session_maker) -> None:
    """Периодически отзывает просроченные ключи.

    :param settings: конфигурация приложения.
    :param session_maker: фабрика сессий.
    :return: None.
    """

    interval = settings.cleanup_interval_minutes * 60
    while True:
        try:
            async with session_maker() as session:
                service = KeyService(session=session, settings=settings)
                count = await service.cleanup_expired()
                await session.commit()
                if count:
                    logging.info("Cleanup: revoked %s expired keys", count)
        except Exception as exc:  # pylint: disable=broad-except
            logging.exception("Cleanup worker failed: %s", exc)
        await asyncio.sleep(interval)


async def main(settings: Settings) -> None:
    """Точка входа для бота и инициализации БД.

    :param settings: конфигурация приложения.
    :return: None.
    """

    session_maker = get_session_maker(settings)

    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)

    dp = Dispatcher()
    dp.update.middleware(ContextMiddleware(settings=settings, session_maker=session_maker))
    dp.callback_query.middleware(ContextMiddleware(settings=settings, session_maker=session_maker))
    dp.message.middleware(ContextMiddleware(settings=settings, session_maker=session_maker))

    admin.router.callback_query.filter(AdminFilter(settings.admin_ids))
    admin.router.message.filter(AdminFilter(settings.admin_ids))

    dp.include_router(common.router)
    dp.include_router(user_keys.router)
    dp.include_router(admin.router)

    cleanup_task = asyncio.create_task(cleanup_worker(settings, session_maker))
    try:
        await dp.start_polling(bot)
    finally:
        cleanup_task.cancel()


def run() -> None:
    """Запускает миграции и бот."""

    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    if not settings.bot_token or ":" not in settings.bot_token:
        raise SystemExit("BOT_TOKEN не задан или неверный. Укажи корректный токен в .env")
    run_migrations(settings)
    asyncio.run(main(settings))


if __name__ == "__main__":
    run()
