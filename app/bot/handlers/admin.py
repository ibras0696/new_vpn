from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.bot.callbacks import AdminAction, MenuAction
from app.bot.keyboards import admin_keyboard, main_menu
from app.config import Settings
from app.db import SessionMaker
from app.services import KeyService

router = Router()


@router.callback_query(MenuAction.filter(F.action == "admin"))
async def admin_panel(callback: CallbackQuery) -> None:
    """Открывает админ-панель.

    :param callback: входящий CallbackQuery.
    :return: None.
    """

    settings: Settings = callback.bot["settings"]
    await callback.message.edit_text(
        "Админ-панель: выбери фильтр.",
        reply_markup=admin_keyboard(),
    )
    await callback.answer()


@router.callback_query(AdminAction.filter())
async def admin_lists(callback: CallbackQuery, callback_data: AdminAction) -> None:
    """Показывает ключи с фильтрами для админов.

    :param callback: входящий CallbackQuery.
    :param callback_data: распарсенная команда панели.
    :return: None.
    """

    settings: Settings = callback.bot["settings"]
    session_maker: SessionMaker = callback.bot["session_maker"]

    async with session_maker() as session:
        service = KeyService(
            session=session,
            max_keys_per_user=settings.max_keys_per_user,
            default_key_ttl_hours=settings.default_key_ttl_hours,
        )
        keys = await service.list_all()
        await session.commit()

    action = callback_data.action
    if action == "active":
        filtered = [k for k in keys if k.is_active]
        title = "Активные ключи:"
    elif action == "expired":
        filtered = [k for k in keys if not k.is_active]
        title = "Просроченные/отозванные:"
    else:
        filtered = keys
        title = "Все ключи:"

    if not filtered:
        lines = ["Нет записей."]
    else:
        lines = [
            f"{'✅' if k.is_active else '⛔'} {k.name} u:{k.user_id} до {k.expires_at:%Y-%m-%d %H:%M UTC}"
            for k in filtered
        ]

    await callback.message.edit_text(
        "\n".join([title, *lines]),
        reply_markup=admin_keyboard(),
    )


@router.callback_query(MenuAction.filter(F.action == "home"))
async def back_to_menu(callback: CallbackQuery) -> None:
    """Возвращает админа в главное меню.

    :param callback: входящий CallbackQuery.
    :return: None.
    """

    settings: Settings = callback.bot["settings"]
    await callback.message.edit_text(
        "Меню действий:",
        reply_markup=main_menu(user_is_admin=True),
    )
    await callback.answer()
