from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from config import settings


class AdminFilter(BaseFilter):
    """
    Универсальный фильтр, пропускающий только администратора из settings.ADMIN_ID.
    Подходит как для сообщений, так и для callback-запросов.
    """

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user if hasattr(event, "from_user") else None
        return bool(user and user.id == settings.ADMIN_ID)
