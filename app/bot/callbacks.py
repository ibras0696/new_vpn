from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class MenuAction(CallbackData, prefix="menu"):
    """Действия из главного меню."""

    action: str


class KeyCreateAction(CallbackData, prefix="key_create"):
    """Создание ключа с заданным TTL."""

    hours: int


class KeyRevokeAction(CallbackData, prefix="key_revoke"):
    """Отзыв конкретного ключа."""

    key_id: str


class AdminAction(CallbackData, prefix="admin"):
    """Действия админ-панели."""

    action: str
