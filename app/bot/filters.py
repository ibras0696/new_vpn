from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message


class AdminFilter(BaseFilter):
    """Пропускает только сообщения/коллбеки от админов."""

    def __init__(self, admin_ids: set[int]):
        """Инициализация фильтра.

        :param admin_ids: Telegram ID администраторов.
        """

        self.admin_ids = admin_ids

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        """Проверяет, является ли пользователь админом.

        :param event: входящее событие.
        :return: True, если админ.
        """

        if event.from_user is None:
            return False
        return event.from_user.id in self.admin_ids
