from __future__ import annotations

import datetime as dt
import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import VpnKey
from app.repositories import UserRepository, VpnKeyRepository


class KeyService:
    """Бизнес-логика управления ключами."""

    def __init__(
        self,
        session: AsyncSession,
        max_keys_per_user: int,
        default_key_ttl_hours: int,
    ):
        """Инициализирует сервис.

        :param session: сессия БД.
        :param max_keys_per_user: лимит ключей на пользователя.
        :param default_key_ttl_hours: срок жизни ключа по умолчанию.
        """

        self.session = session
        self.max_keys_per_user = max_keys_per_user
        self.default_key_ttl_hours = default_key_ttl_hours
        self.user_repo = UserRepository(session)
        self.key_repo = VpnKeyRepository(session)

    async def ensure_user(self, telegram_id: int, username: str | None) -> int:
        """Создаёт или возвращает пользователя.

        :param telegram_id: Telegram ID.
        :param username: username.
        :return: id пользователя в БД.
        """

        user = await self.user_repo.get_or_create(telegram_id=telegram_id, username=username)
        return user.id

    async def set_admins(self, admin_ids: set[int]) -> None:
        """Маркирует администраторов.

        :param admin_ids: список Telegram ID админов.
        :return: None.
        """

        await self.user_repo.mark_admins(admin_ids)

    async def list_keys(self, user_id: int) -> Sequence[VpnKey]:
        """Список ключей пользователя.

        :param user_id: id пользователя.
        :return: последовательность ключей.
        """

        return await self.key_repo.list_for_user(user_id)

    async def create_key(
        self, user_id: int, name: str, ttl_hours: int | None = None, public_key: str | None = None
    ) -> VpnKey:
        """Создаёт новый временный ключ с учётом лимитов.

        :param user_id: id пользователя.
        :param name: имя ключа.
        :param ttl_hours: срок жизни в часах.
        :param public_key: опционально публичный ключ.
        :return: созданный ключ.
        :raises ValueError: если превышен лимит.
        """

        existing = await self.key_repo.list_for_user(user_id)
        active = [k for k in existing if k.is_active]
        if len(active) >= self.max_keys_per_user:
            raise ValueError("Превышен лимит устройств")

        hours = ttl_hours or self.default_key_ttl_hours
        expires_at = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc) + dt.timedelta(hours=hours)
        key = await self.key_repo.create(
            user_id=user_id,
            name=name,
            expires_at=expires_at,
            public_key=public_key,
        )
        return key

    async def revoke_key(self, key_id: uuid.UUID, user_id: int | None = None) -> bool:
        """Отзывает ключ и (опционально) проверяет владельца.

        :param key_id: идентификатор ключа.
        :param user_id: владелец, если нужно ограничить по пользователю.
        :return: True, если найден и отозван.
        """

        revoked = await self.key_repo.revoke(key_id, user_id=user_id)
        return revoked is not None

    async def list_all(self) -> Sequence[VpnKey]:
        """Возвращает ключи для админ-панели.

        :return: список всех ключей.
        """

        return await self.key_repo.list_all()
