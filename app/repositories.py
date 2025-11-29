from __future__ import annotations

import datetime as dt
import uuid
from typing import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, VpnKey


class UserRepository:
    """CRUD для пользователей."""

    def __init__(self, session: AsyncSession):
        """Инициализирует репозиторий.

        :param session: активная AsyncSession.
        """

        self.session = session

    async def get_or_create(self, telegram_id: int, username: str | None) -> User:
        """Возвращает пользователя или создаёт нового.

        :param telegram_id: Telegram ID.
        :param username: username (может быть None).
        :return: экземпляр User.
        """

        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            return user
        user = User(telegram_id=telegram_id, username=username)
        self.session.add(user)
        await self.session.flush()
        return user

    async def mark_admins(self, admin_ids: Iterable[int]) -> None:
        """Помечает админов на основании списка ID.

        :param admin_ids: Telegram ID администраторов.
        :return: None.
        """

        if not admin_ids:
            return
        result = await self.session.execute(select(User).where(User.telegram_id.in_(admin_ids)))
        existing_users = result.scalars().all()
        existing = {user.telegram_id for user in existing_users}
        for user in existing_users:
            user.is_admin = True
        missing_ids = set(admin_ids) - existing
        for telegram_id in missing_ids:
            self.session.add(User(telegram_id=telegram_id, username=None, is_admin=True))
        await self.session.flush()


class VpnKeyRepository:
    """Работа с временными ключами."""

    def __init__(self, session: AsyncSession):
        """Инициализация репозитория.

        :param session: активная AsyncSession.
        """

        self.session = session

    async def list_for_user(self, user_id: int) -> Sequence[VpnKey]:
        """Возвращает все ключи пользователя.

        :param user_id: id пользователя.
        :return: список ключей.
        """

        result = await self.session.execute(
            select(VpnKey).where(VpnKey.user_id == user_id).order_by(VpnKey.created_at.desc())
        )
        return result.scalars().all()

    async def create(
        self, user_id: int, name: str, expires_at: dt.datetime, public_key: str | None = None
    ) -> VpnKey:
        """Создаёт новый ключ.

        :param user_id: идентификатор пользователя.
        :param name: человекочитаемое имя ключа.
        :param expires_at: срок действия.
        :param public_key: публичный ключ (если уже есть).
        :return: созданный ключ.
        """

        key = VpnKey(
            user_id=user_id,
            name=name,
            expires_at=expires_at,
            public_key=public_key,
        )
        self.session.add(key)
        await self.session.flush()
        return key

    async def revoke(self, key_id: uuid.UUID, user_id: int | None = None) -> VpnKey | None:
        """Отзывает ключ.

        :param key_id: идентификатор ключа.
        :param user_id: опциональный фильтр по владельцу.
        :return: ключ или None, если не найден.
        """

        stmt = select(VpnKey).where(VpnKey.id == key_id)
        if user_id is not None:
            stmt = stmt.where(VpnKey.user_id == user_id)
        result = await self.session.execute(stmt)
        key = result.scalar_one_or_none()
        if key is None:
            return None
        key.revoked_at = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
        await self.session.flush()
        return key

    async def list_all(self) -> Sequence[VpnKey]:
        """Возвращает все ключи (для админов).

        :return: список ключей.
        """

        result = await self.session.execute(select(VpnKey).order_by(VpnKey.created_at.desc()))
        return result.scalars().all()
