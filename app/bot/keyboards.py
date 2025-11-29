from __future__ import annotations

from typing import Iterable, Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks import AdminAction, KeyCreateAction, KeyRevokeAction, MenuAction
from app.models import VpnKey


def main_menu(user_is_admin: bool) -> InlineKeyboardMarkup:
    """Главное меню."""

    buttons = [
        [InlineKeyboardButton(text="➕ Новый ключ", callback_data=MenuAction(action="create").pack())],
        [InlineKeyboardButton(text="🔑 Мои ключи", callback_data=MenuAction(action="list").pack())],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data=MenuAction(action="help").pack())],
    ]
    if user_is_admin:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🛠 Админ-панель", callback_data=MenuAction(action="admin").pack()
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def key_create_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора срока ключа."""

    hours_options = (12, 24, 72)
    rows = [
        [
            InlineKeyboardButton(
                text=f"{hours} ч", callback_data=KeyCreateAction(hours=hours).pack()
            )
            for hours in hours_options[:2]
        ],
        [
            InlineKeyboardButton(
                text=f"{hours} ч", callback_data=KeyCreateAction(hours=hours).pack()
            )
            for hours in hours_options[2:]
        ],
    ]
    rows.append(
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data=MenuAction(action="home").pack())
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def keys_keyboard(keys: Sequence[VpnKey]) -> InlineKeyboardMarkup:
    """Клавиатура отзыва для активных ключей."""

    rows: list[list[InlineKeyboardButton]] = []
    for key in keys:
        if not key.is_active:
            continue
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"❌ Отозвать {key.name}",
                    callback_data=KeyRevokeAction(key_id=str(key.id)).pack(),
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=MenuAction(action="home").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Активные",
                    callback_data=AdminAction(action="active").pack(),
                ),
                InlineKeyboardButton(
                    text="Просроченные",
                    callback_data=AdminAction(action="expired").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Все ключи",
                    callback_data=AdminAction(action="all").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ В меню", callback_data=MenuAction(action="home").pack()
                )
            ],
        ]
    )
