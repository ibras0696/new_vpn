import asyncio
import logging
from datetime import datetime, UTC
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from data.db import AsyncSessionLocal
from data.repo import VlessKeyRepo
from config import settings
from services.xray_client import check_xray_api, remove_vless_user

logger = logging.getLogger(__name__)

async def cleanup_expired():
    """Отключает все истёкшие ключи."""
    if not settings.XRAY_API_ENABLED:
        logger.debug("XRAY API отключён — задача очистки пропускается.")
        return

    available = await asyncio.to_thread(check_xray_api)
    if not available:
        logger.warning("XRAY API недоступен — очистка истёкших ключей пропущена.")
        return

    async with AsyncSessionLocal() as session:
        repo = VlessKeyRepo(session)
        keys = await repo.list_all(only_active=True)
        for key in keys:
            if key.expires_at and datetime.now(UTC) > key.expires_at:
                key.active = False
                await session.commit()
                try:
                    removed = await asyncio.to_thread(remove_vless_user, str(key.id))
                    if removed:
                        logger.info(f"❌ Ключ {key.id} истёк и отключён")
                    else:
                        logger.debug("Ключ %s отсутствовал в XRay во время очищения.", key.id)
                except Exception:  # noqa: BLE001
                    logger.exception("Ошибка при удалении ключа %s из XRay.", key.id)

def start_scheduler():
    """Запускает планировщик в event-loop’е."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(cleanup_expired, "interval", minutes=10)
    scheduler.start()
    logger.info("⏱ Scheduler запущен (интервал 10 мин).")
