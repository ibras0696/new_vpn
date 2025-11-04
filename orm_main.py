import asyncio
from datetime import datetime, timedelta, UTC

from data.db import init_db, AsyncSessionLocal
from data.repo import VlessKeyRepo


async def pipline_main():
    # 1️⃣ Создаём таблицы (только при первом запуске, для SQLite)
    print("📦 Инициализация базы данных...")
    await init_db()

    # 2️⃣ Открываем сессию
    async with AsyncSessionLocal() as session:
        repo = VlessKeyRepo(session)

        print("\n🆕 Создание ключа...")
        key = await repo.create(
            user_id=1,
            expires_at=datetime.now(UTC) + timedelta(days=3),
            device_limit=2,
        )
        print(f"Создан ключ: {key.id}, истекает: {key.expires_at}, активен: {key.active}")

        # 3️⃣ Продлеваем ключ
        print("\n🔄 Продление ключа на 7 дней...")
        extended = await repo.extend_key(key.id, 7)
        print(f"Новый срок действия: {extended.expires_at}")

        # 4️⃣ Проверяем просроченность
        print("\n📅 Проверка срока...")
        print(f"Ключ истёк? {extended.is_expired()}")

        # 5️⃣ Удаляем ключ
        print("\n🗑️ Удаление ключа...")
        deleted = await repo.delete(key.id)
        print(f"Ключ удалён: {deleted}")


if __name__ == "__main__":
    pass
