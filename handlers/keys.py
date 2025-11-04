from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from data.db import AsyncSessionLocal
from data.repo import VlessKeyRepo
from filters.admin import AdminFilter
from services.xray_client import remove_vless_user
from .keyboards import back_to_menu_kb, cancel_input_kb, main_menu_kb
from .states import AdminStates

router = Router()
logger = logging.getLogger(__name__)


def _render_keys(keys: Iterable) -> str:
    if not keys:
        return "📭 Нет созданных ключей."

    lines = ["📋 <b>Список VLESS-ключей:</b>", ""]
    for key in keys:
        exp = "♾️ бессрочный" if not key.expires_at else key.expires_at.strftime("%Y-%m-%d")
        status = "✅ активен" if key.active else "⛔ отключён"
        lines.append(f"🔹 <code>{key.id}</code>")
        lines.append(f"📅 {exp} | {status}")
        lines.append("")
    return "\n".join(lines).strip()


@router.callback_query(AdminFilter(), F.data == "menu:list")
async def list_keys(callback: CallbackQuery):
    await callback.answer()
    async with AsyncSessionLocal() as session:
        repo = VlessKeyRepo(session)
        keys = await repo.list_all(only_active=False)

    text = _render_keys(keys)
    try:
        await callback.message.edit_text(text, reply_markup=back_to_menu_kb())
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=back_to_menu_kb())


@router.callback_query(AdminFilter(), F.data == "menu:delete")
async def request_delete(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminStates.waiting_delete_id)
    await callback.message.edit_text(
        "Отправь UUID ключа, который нужно удалить:",
        reply_markup=cancel_input_kb("delete"),
    )


@router.message(AdminFilter(), AdminStates.waiting_delete_id)
async def handle_delete(message: Message, state: FSMContext):
    key_id = (message.text or "").strip()
    if not key_id:
        await message.answer("⚠️ Пришли UUID ключа.")
        return

    status = await message.answer("⏳ Удаляю ключ...")
    async with AsyncSessionLocal() as session:
        repo = VlessKeyRepo(session)
        deleted = await repo.delete(key_id)

    if deleted:
        try:
            await asyncio.to_thread(remove_vless_user, key_id)
        except Exception:  # noqa: BLE001
            logger.exception("Не удалось удалить ключ %s из XRay.", key_id)
        text = f"🗑️ Ключ <code>{key_id}</code> удалён."
    else:
        text = f"❌ Ключ <code>{key_id}</code> не найден."

    await state.clear()
    await message.answer(text, reply_markup=main_menu_kb())

    try:
        await status.delete()
    except TelegramBadRequest:
        pass


@router.callback_query(AdminFilter(), F.data == "cancel:delete")
async def cancel_delete(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Отменено")
    try:
        await callback.message.edit_text(
            "Что делаем дальше?",
            reply_markup=main_menu_kb(),
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "Что делаем дальше?",
            reply_markup=main_menu_kb(),
        )


@router.message(AdminFilter(), Command("list_keys"))
async def legacy_list_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Теперь список ключей доступен через меню. Выбирай «📋 Список ключей».",
        reply_markup=main_menu_kb(),
    )


@router.message(AdminFilter(), Command("delete_key"))
async def legacy_delete_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Удаление ключей доступно через меню. Нажми «🗑️ Удалить ключ».",
        reply_markup=main_menu_kb(),
    )
