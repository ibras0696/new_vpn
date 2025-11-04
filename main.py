import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from services.xray_configurator import configure_xray
from services.scheduler import start_scheduler
from data.db import init_db
from handlers import router

# --- Настройка логов ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)


async def main_async() -> None:
    """
    Инициализирует базу данных и запускает Telegram-бота.
    """
    logging.info("🚀 Инициализация базы данных...")
    await init_db()

    logging.info('Start Sheduler')
    start_scheduler()

    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    logging.info("🤖 Запуск Telegram-бота...")
    async with Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    ) as bot:
        await dispatcher.start_polling(bot)

    logging.info("🛑 Бот остановлен.")


if __name__ == "__main__":
    logging.info("⚙️ Конфигурация XRay...")
    configure_xray()
    asyncio.run(main_async())
