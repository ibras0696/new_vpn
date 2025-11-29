from __future__ import annotations

import datetime as dt
import uuid
from typing import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Alert, BillingEvent, User, VpnKey


class UserRepository:
    """CRUD для пользователей."""

    def __init__(self, session: AsyncSession):
        """Инициализирует репозиторий.

        :param session: активная AsyncSession.
        """

        self.session = session

    async def get_or_create(
        self, telegram_id: int, username: str | None, initial_balance: int = 0
    ) -> User:
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
        user = User(telegram_id=telegram_id, username=username, balance=initial_balance)
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

    async def get_by_id(self, user_id: int) -> User | None:
        """Возвращает пользователя по id.

        :param user_id: идентификатор.
        :return: User или None.
        """

        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


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
        self,
        user_id: int,
        name: str,
        expires_at: dt.datetime,
        public_key: str,
        client_address: str,
        preshared_key: str | None,
        rotated_from_id: uuid.UUID | None = None,
    ) -> VpnKey:
        """Создаёт новый ключ.

        :param user_id: идентификатор пользователя.
        :param name: человекочитаемое имя ключа.
        :param expires_at: срок действия.
        :param public_key: публичный ключ.
        :param client_address: адрес клиента в туннеле.
        :param preshared_key: предварительно разделяемый ключ.
        :param rotated_from_id: ссылка на предыдущий ключ.
        :return: созданный ключ.
        """

        key = VpnKey(
            user_id=user_id,
            name=name,
            expires_at=expires_at,
            public_key=public_key,
            client_address=client_address,
            preshared_key=preshared_key,
            rotated_from_id=rotated_from_id,
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

    async def active_addresses(self) -> set[str]:
        """Возвращает адреса, занятые активными ключами.

        :return: множество адресов.
        """

        now = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
        result = await self.session.execute(
            select(VpnKey.client_address).where(
                VpnKey.revoked_at.is_(None), VpnKey.expires_at > now
            )
        )
        return {row[0] for row in result if row[0]}

    async def get(self, key_id: uuid.UUID, user_id: int | None = None) -> VpnKey | None:
        """Возвращает ключ по идентификатору.

        :param key_id: идентификатор ключа.
        :param user_id: опциональный владелец.
        :return: VpnKey или None.
        """

        stmt = select(VpnKey).where(VpnKey.id == key_id)
        if user_id is not None:
            stmt = stmt.where(VpnKey.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_expired(self) -> int:
        """Отзывает просроченные ключи.

        :return: количество отозванных ключей.
        """

        now = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
        result = await self.session.execute(
            select(VpnKey).where(VpnKey.revoked_at.is_(None), VpnKey.expires_at <= now)
        )
        keys = result.scalars().all()
        for key in keys:
            key.revoked_at = now
        await self.session.flush()
        return len(keys)


class BillingRepository:
    """Работа с биллингом."""

    def __init__(self, session: AsyncSession):
        """Инициализация.

        :param session: активная AsyncSession.
        """

        self.session = session

    async def add_event(self, user_id: int, amount: int, event_type: str, description: str) -> None:
        """Добавляет запись биллинга.

        :param user_id: владелец.
        :param amount: сумма (пополнение >0, списание <0).
        :param event_type: тип события.
        :param description: описание.
        :return: None.
        """

        event = BillingEvent(
            user_id=user_id,
            amount=amount,
            event_type=event_type,
            description=description,
        )
        self.session.add(event)
        await self.session.flush()


class AlertRepository:
    """Хранение алертов."""

    def __init__(self, session: AsyncSession):
        """Инициализация.

        :param session: активная AsyncSession.
        """

        self.session = session

    async def add(self, level: str, message: str, user_id: int | None = None) -> None:
        """Добавляет алерт.

        :param level: уровень (info/warn/error).
        :param message: текст алерта.
        :param user_id: опциональный пользователь.
        :return: None.
        """

        alert = Alert(level=level, message=message, user_id=user_id)
        self.session.add(alert)
        await self.session.flush()

    async def latest(self, limit: int = 20) -> Sequence[Alert]:
        """Возвращает последние алерты.

        :param limit: количество записей.
        :return: последовательность алертов.
        """

        result = await self.session.execute(
            select(Alert).order_by(Alert.created_at.desc()).limit(limit)
        )
        return result.scalars().all()
