"""
Хендлеры для управления VLESS-ключами через Telegram-бота.
Используют ORM-репозиторий VlessKeyRepo и проверяют ADMIN_ID.
"""

from aiogram import Router, types
from aiogram.filters import Command

from config import settings
from data.db import AsyncSessionLocal
from data.repo import VlessKeyRepo

router = Router()


# --- Вспомогательная проверка ---
def _is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    return user_id == settings.ADMIN_ID


# === /new_key ===
# @router.message(Command("new_key"))
# async def cmd_new_key(message: types.Message):
#     """
#     Создаёт новый VLESS-ключ (через ORM).
#
#     Пример:
#         /new_key 7     → ключ на 7 дней
#         /new_key 0     → бессрочный
#     """
#     if not _is_admin(message.from_user.id):
#         await message.answer("⛔ У тебя нет прав для этой команды.")
#         return
#
#     parts = message.text.strip().split()
#     if len(parts) < 2:
#         await message.answer("⚠️ Использование: /new_key дней\nНапример: /new_key 30 или /new_key 0 для бессрочного.")
#         return
#
#     try:
#         days = int(parts[1])
#         days = None if days == 0 else days
#     except ValueError:
#         await message.answer("❌ Укажи число дней. Пример: /new_key 30")
#         return
#
#     async with AsyncSessionLocal() as session:
#         repo = VlessKeyRepo(session)
#         key = await repo.create(user_id=1, days=days)  # TODO: user_id=1 → потом из users
#         await message.answer(
#             f"✅ Ключ создан!\n"
#             f"<b>ID:</b> <code>{key.id}</code>\n"
#             f"<b>Срок:</b> {'Бессрочный' if key.expires_at is None else key.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
#             f"<b>Устройства:</b> {key.device_limit}"
#         )


# === /list_keys ===
@router.message(Command("list_keys"))
async def cmd_list_keys(message: types.Message):
    """
    Показывает список активных VLESS-ключей.
    """
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    async with AsyncSessionLocal() as session:
        repo = VlessKeyRepo(session)
        keys = await repo.list_all()

    if not keys:
        await message.answer("📭 Нет активных ключей.")
        return

    text = "📋 <b>Список VLESS-ключей:</b>\n\n"
    for k in keys:
        exp = "♾️ бессрочный" if not k.expires_at else k.expires_at.strftime("%Y-%m-%d")
        status = "✅ активен" if k.active else "⛔ отключён"
        text += f"🔹 <code>{k.id}</code>\n📅 {exp} | {status}\n\n"

    await message.answer(text)


# === /delete_key ===
@router.message(Command("delete_key"))
async def cmd_delete_key(message: types.Message):
    """
    Удаляет VLESS-ключ по UUID.
    """
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("⚠️ Использование: /delete_key <UUID>")
        return

    key_id = parts[1]
    async with AsyncSessionLocal() as session:
        repo = VlessKeyRepo(session)
        result = await repo.delete(key_id)

    if result:
        await message.answer(f"🗑️ Ключ <code>{key_id}</code> удалён.")
    else:
        await message.answer(f"❌ Ключ <code>{key_id}</code> не найден.")
