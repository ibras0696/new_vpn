from __future__ import annotations

import asyncio
import io
import logging
from typing import Optional

import qrcode
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from data.db import AsyncSessionLocal
from data.repo import VlessKeyRepo
from filters.admin import AdminFilter
from .keyboards import (
    cancel_input_kb,
    create_key_kb,
    key_created_actions_kb,
    main_menu_kb,
)
from .states import AdminStates
from services.xray_client import add_vless_user
from config import settings

router = Router()
logger = logging.getLogger(__name__)


def _build_vless_link(key_id: str) -> str:
    domain = settings.XRAY_DOMAIN
    port = settings.XRAY_PORT
    network = settings.XRAY_NETWORK
    security = settings.XRAY_SECURITY
    return (
        f"vless://{key_id}@{domain}:{port}"
        f"?encryption=none&security={security}&type={network}#VPN_KEY"
    )


def _format_caption(key, link: str, warning: str) -> str:
    exp_text = "♾️ Бессрочный" if not key.expires_at else key.expires_at.strftime("%Y-%m-%d %H:%M UTC")
    caption = (
        f"✅ <b>Ключ создан!</b>\n\n"
        f"<b>ID:</b> <code>{key.id}</code>\n"
        f"<b>Срок:</b> {exp_text}\n"
        f"<b>Устройства:</b> {key.device_limit}\n\n"
        f"<b>VLESS ссылка:</b>\n<code>{link}</code>\n\n"
        f"📱 Отсканируй QR-код ниже в <b>V2RayNG</b>, <b>Nekoray</b> или <b>v2rayN</b>."
    )
    if warning:
        caption += f"\n\n{warning}"
    return caption


def _build_qr_file(link: str) -> BufferedInputFile:
    qr_img = qrcode.make(link)
    qr_bytes = io.BytesIO()
    qr_img.save(qr_bytes, format="PNG")
    qr_bytes.seek(0)
    return BufferedInputFile(qr_bytes.read(), filename="vless_qr.png")


async def _create_vless_key(days: Optional[int]) -> tuple:
    async with AsyncSessionLocal() as session:
        repo = VlessKeyRepo(session)
        key = await repo.create(user_id=1, days=days)

    warning = ""
    try:
        added = await asyncio.to_thread(add_vless_user, key)
        if not added:
            warning = "⚠️ Ключ уже присутствовал в конфигурации XRay."
    except Exception:  # noqa: BLE001
        logger.exception("Не удалось зарегистрировать ключ %s в XRay", key.id)
        warning = "⚠️ Ключ создан, но XRay API вернул ошибку. Проверь логи."

    return key, warning


async def _render_key_result(message: Message, days: Optional[int]) -> None:
    key, warning = await _create_vless_key(days)
    link = _build_vless_link(str(key.id))
    qr_input = _build_qr_file(link)
    caption = _format_caption(key, link, warning)

    await message.answer_photo(
        qr_input,
        caption=caption,
        parse_mode="HTML",
        reply_markup=key_created_actions_kb(),
    )


@router.callback_query(AdminFilter(), F.data == "menu:create")
async def show_create_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    try:
        await callback.message.edit_text(
            "Выбери срок действия ключа:",
            reply_markup=create_key_kb(),
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "Выбери срок действия ключа:",
            reply_markup=create_key_kb(),
        )


@router.callback_query(AdminFilter(), F.data.startswith("create:days:"))
async def create_with_preset(callback: CallbackQuery):
    await callback.answer()
    try:
        days_raw = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.message.answer("❌ Неизвестный вариант срока действия.", reply_markup=main_menu_kb())
        return

    days = None if days_raw == 0 else days_raw
    try:
        await callback.message.edit_text("⏳ Создаём ключ...")
    except TelegramBadRequest:
        await callback.message.answer("⏳ Создаём ключ...")
    await _render_key_result(callback.message, days)

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass


@router.callback_query(AdminFilter(), F.data == "create:custom")
async def request_custom_days(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminStates.waiting_custom_days)
    try:
        await callback.message.edit_text(
            "Введи срок действия ключа в днях (0 — бессрочный):",
            reply_markup=cancel_input_kb("create"),
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "Введи срок действия ключа в днях (0 — бессрочный):",
            reply_markup=cancel_input_kb("create"),
        )


@router.message(AdminFilter(), AdminStates.waiting_custom_days)
async def handle_custom_days(message: Message, state: FSMContext):
    raw_value = (message.text or "").strip()
    try:
        days_raw = int(raw_value)
    except ValueError:
        await message.answer("❌ Отправь целое число. Используй 0 для бессрочного ключа.")
        return

    if days_raw < 0:
        await message.answer("❌ Срок не может быть отрицательным.")
        return

    await state.clear()
    status = await message.answer("⏳ Создаём ключ...")

    days = None if days_raw == 0 else days_raw
    await _render_key_result(message, days)

    try:
        await status.delete()
    except TelegramBadRequest:
        pass


@router.callback_query(AdminFilter(), F.data == "cancel:create")
async def cancel_custom_days(callback: CallbackQuery, state: FSMContext):
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


@router.message(AdminFilter(), Command("new_key"))
async def legacy_command_redirect(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Теперь создание ключей вынесено в меню. Выбирай действие ниже 👇",
        reply_markup=main_menu_kb(),
    )


@router.message(AdminFilter(), Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    if await state.get_state() is None:
        await message.answer("Нет активной операции.", reply_markup=main_menu_kb())
        return

    await state.clear()
    await message.answer("Операция отменена.", reply_markup=main_menu_kb())
