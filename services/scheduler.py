import asyncio
import logging
from datetime import datetime, UTC
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from data.db import AsyncSessionLocal
from data.repo import VlessKeyRepo
from services.xray_client import remove_vless_user

logger = logging.getLogger(__name__)

async def cleanup_expired():
    """Отключает все истёкшие ключи."""
    async with AsyncSessionLocal() as session:
        repo = VlessKeyRepo(session)
        keys = await repo.list_all(only_active=True)
        for key in keys:
            if key.expires_at and datetime.now(UTC) > key.expires_at:
                key.active = False
                await session.commit()
                remove_vless_user(str(key.id))
                logger.info(f"❌ Ключ {key.id} истёк и отключён")

def start_scheduler():
    """Запускает планировщик в event-loop’е."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(cleanup_expired, "interval", minutes=10)
    scheduler.start()
    logger.info("⏱ Scheduler запущен (интервал 10 мин).")
