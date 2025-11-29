from __future__ import annotations

import uuid

from aiogram import Bot, Router, F
from aiogram.types import CallbackQuery

from app.bot.callbacks import KeyCreateAction, KeyRevokeAction, MenuAction
from app.bot.keyboards import key_create_keyboard, keys_keyboard, main_menu
from app.config import Settings
from app.db import SessionMaker
from app.services import KeyService

router = Router()


@router.callback_query(MenuAction.filter(F.action == "create"))
async def show_create_menu(callback: CallbackQuery) -> None:
    """Показывает выбор длительности для нового ключа.

    :param callback: входящий CallbackQuery.
    :return: None.
    """

    await callback.message.edit_text(
        "Выбери срок действия временного ключа:",
        reply_markup=key_create_keyboard(),
    )


@router.callback_query(KeyCreateAction.filter())
async def create_key(callback: CallbackQuery, callback_data: KeyCreateAction) -> None:
    """Создаёт временный ключ и показывает результат.

    :param callback: входящий CallbackQuery.
    :param callback_data: данные с выбранным TTL.
    :return: None.
    """

    if callback.from_user is None:
        return
    bot = callback.bot
    settings: Settings = bot["settings"]
    session_maker: SessionMaker = bot["session_maker"]

    async with session_maker() as session:
        service = KeyService(
            session=session,
            max_keys_per_user=settings.max_keys_per_user,
            default_key_ttl_hours=settings.default_key_ttl_hours,
        )
        user_id = await service.ensure_user(callback.from_user.id, callback.from_user.username)
        await service.set_admins(settings.admin_ids)
        try:
            key = await service.create_key(
                user_id=user_id,
                name=f"key-{callback_data.hours}h",
                ttl_hours=callback_data.hours,
            )
            await session.commit()
        except ValueError as exc:
            await session.rollback()
            await callback.answer(str(exc), show_alert=True)
            return

    await callback.message.edit_text(
        (
            "✅ Ключ создан.\n"
            f"ID: {key.id}\n"
            f"Имя: {key.name}\n"
            f"Действует до: {key.expires_at:%Y-%m-%d %H:%M UTC}\n\n"
            "⚠️ Генерацию/выдачу реального WireGuard-конфига нужно будет подключить к API."
        ),
        reply_markup=main_menu(
            user_is_admin=callback.from_user.id in settings.admin_ids,
        ),
    )


@router.callback_query(MenuAction.filter(F.action == "list"))
async def list_keys(callback: CallbackQuery) -> None:
    """Показывает ключи пользователя.

    :param callback: входящий CallbackQuery.
    :return: None.
    """

    if callback.from_user is None:
        return
    bot = callback.bot
    settings: Settings = bot["settings"]
    session_maker: SessionMaker = bot["session_maker"]

    async with session_maker() as session:
        service = KeyService(
            session=session,
            max_keys_per_user=settings.max_keys_per_user,
            default_key_ttl_hours=settings.default_key_ttl_hours,
        )
        user_id = await service.ensure_user(callback.from_user.id, callback.from_user.username)
        keys = await service.list_keys(user_id)
        await session.commit()

    if not keys:
        text = "Пока нет ключей. Создай новый."
    else:
        lines = []
        for key in keys:
            status = "✅ активен" if key.is_active else "⛔ истёк/отозван"
            lines.append(
                f"{status}: {key.name} (до {key.expires_at:%Y-%m-%d %H:%M UTC}, id={key.id})"
            )
        text = "\n".join(lines)

    await callback.message.edit_text(text, reply_markup=keys_keyboard(keys))


@router.callback_query(KeyRevokeAction.filter())
async def revoke_key(callback: CallbackQuery, callback_data: KeyRevokeAction) -> None:
    """Отзывает выбранный ключ.

    :param callback: входящий CallbackQuery.
    :param callback_data: данные с идентификатором ключа.
    :return: None.
    """

    if callback.from_user is None:
        return
    bot = callback.bot
    settings: Settings = bot["settings"]
    session_maker: SessionMaker = bot["session_maker"]

    key_id = uuid.UUID(callback_data.key_id)
    async with session_maker() as session:
        service = KeyService(
            session=session,
            max_keys_per_user=settings.max_keys_per_user,
            default_key_ttl_hours=settings.default_key_ttl_hours,
        )
        user_id = await service.ensure_user(callback.from_user.id, callback.from_user.username)
        success = await service.revoke_key(key_id, user_id=user_id)
        await session.commit()

    if success:
        await callback.answer("Ключ отозван", show_alert=True)
    else:
        await callback.answer("Ключ не найден", show_alert=True)
    await callback.message.edit_reply_markup(
        reply_markup=main_menu(user_is_admin=callback.from_user.id in settings.admin_ids)
    )
