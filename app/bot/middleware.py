from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.config import Settings
from app.db import SessionMaker


class ContextMiddleware(BaseMiddleware):
    """Пробрасывает settings и session_maker в data для хэндлеров."""

    def __init__(self, settings: Settings, session_maker: SessionMaker):
        """Инициализация.

        :param settings: конфигурация приложения.
        :param session_maker: фабрика сессий.
        """

        self.settings = settings
        self.session_maker = session_maker

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Добавляет зависимости в контекст.

        :param handler: следующий обработчик.
        :param event: входящее событие.
        :param data: контекст данных.
        :return: результат хэндлера.
        """

        data["settings"] = self.settings
        data["session_maker"] = self.session_maker
        return await handler(event, data)
