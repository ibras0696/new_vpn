from __future__ import annotations

from aiogram import Bot, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import SkipHandler

from app.bot.callbacks import MenuAction
from app.bot.keyboards import main_menu
from app.config import Settings
from app.db import SessionMaker
from app.services import KeyService

router = Router()


def _is_admin(settings: Settings, user_id: int) -> bool:
    """Проверяет, является ли пользователь админом.

    :param settings: конфигурация приложения.
    :param user_id: Telegram ID пользователя.
    :return: True, если админ.
    """

    return user_id in settings.admin_ids


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Обрабатывает /start и показывает главное меню.

    :param message: входящее сообщение.
    :return: None.
    """

    if message.from_user is None:
        return
    bot: Bot = message.bot
    settings: Settings = bot["settings"]
    session_maker: SessionMaker = bot["session_maker"]

    async with session_maker() as session:
        service = KeyService(
            session=session,
            max_keys_per_user=settings.max_keys_per_user,
            default_key_ttl_hours=settings.default_key_ttl_hours,
        )
        await service.set_admins(settings.admin_ids)
        await service.ensure_user(message.from_user.id, message.from_user.username)
        await session.commit()

    text = (
        "Привет! Я помогу управлять VPN-ключами. "
        "Создавай временные ключи, смотри активные и отзывать ненужные."
    )
    await message.answer(
        text,
        reply_markup=main_menu(user_is_admin=_is_admin(settings, message.from_user.id)),
    )


@router.callback_query(MenuAction.filter())
async def handle_menu(callback: CallbackQuery, callback_data: MenuAction) -> None:
    """Навигация по меню (home/help).

    :param callback: исходный CallbackQuery.
    :param callback_data: распарсенные данные меню.
    :return: None.
    """

    if callback.from_user is None:
        return

    settings: Settings = callback.bot["settings"]
    action = callback_data.action

    if action == "admin":
        raise SkipHandler  # передаём в админский роутер

    if action == "home":
        await callback.message.edit_text(
            "Меню действий:",
            reply_markup=main_menu(
                user_is_admin=_is_admin(settings, callback.from_user.id),
            ),
        )
    elif action == "help":
        await callback.answer()
        await callback.message.answer(
            "🆘 Помощь:\n"
            "— \"Новый ключ\" создаёт временный доступ.\n"
            "— \"Мои ключи\" показывает активные/просроченные.\n"
            "— Отзывайте ключи, когда они не нужны.\n"
            "Админы видят отдельную панель.",
            reply_markup=main_menu(
                user_is_admin=_is_admin(settings, callback.from_user.id),
            ),
        )
    else:
        await callback.answer()
