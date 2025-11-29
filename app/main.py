from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from app.bot.filters import AdminFilter
from app.bot.handlers import admin, common, user_keys
from app.config import load_settings
from app.db import get_session_maker, init_models


async def main() -> None:
    """Точка входа для бота и инициализации БД.

    :return: None.
    """

    settings = load_settings()
    session_maker = get_session_maker(settings)
    await init_models(session_maker)

    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
    bot["settings"] = settings
    bot["session_maker"] = session_maker

    dp = Dispatcher()
    admin.router.callback_query.filter(AdminFilter(settings.admin_ids))
    admin.router.message.filter(AdminFilter(settings.admin_ids))

    dp.include_router(common.router)
    dp.include_router(user_keys.router)
    dp.include_router(admin.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
