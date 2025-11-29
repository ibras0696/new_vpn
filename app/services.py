from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import VpnKey
from app.repositories import AlertRepository, BillingRepository, UserRepository, VpnKeyRepository
from app.wireguard import (
    WireGuardCredentials,
    allocate_client_address,
    build_client_config,
    generate_keypair,
    generate_preshared_key,
)


@dataclass
class KeyCreationResult:
    """Результат создания или ротации ключа.

    :param key: модель ключа.
    :param credentials: реквизиты WireGuard.
    """

    key: VpnKey
    credentials: WireGuardCredentials


class AlertService:
    """Работа с алертами."""

    def __init__(self, repo: AlertRepository):
        """Инициализация.

        :param repo: репозиторий алертов.
        """

        self.repo = repo

    async def emit(self, level: str, message: str, user_id: int | None = None) -> None:
        """Создаёт алерт.

        :param level: уровень важности.
        :param message: текст.
        :param user_id: опциональный пользователь.
        :return: None.
        """

        await self.repo.add(level=level, message=message, user_id=user_id)

    async def latest(self, limit: int = 20):
        """Возвращает последние алерты.

        :param limit: количество записей.
        :return: последовательность алертов.
        """

        return await self.repo.latest(limit=limit)


class BillingService:
    """Простая биллинговая учётка (кредиты)."""

    def __init__(self, session: AsyncSession, repo: BillingRepository, user_repo: UserRepository):
        """Инициализация.

        :param session: активная AsyncSession.
        :param repo: репозиторий биллинга.
        :param user_repo: репозиторий пользователей.
        """

        self.session = session
        self.repo = repo
        self.user_repo = user_repo

    async def charge(self, user_id: int, amount: int, description: str) -> None:
        """Списывает кредиты.

        :param user_id: владелец.
        :param amount: сумма (>0 — списание).
        :param description: назначение.
        :return: None.
        :raises ValueError: если недостаточно средств.
        """

        if amount <= 0:
            return
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("Пользователь не найден")
        if user.balance < amount:
            raise ValueError("Недостаточно средств на балансе")
        user.balance -= amount
        await self.repo.add_event(
            user_id=user_id,
            amount=-amount,
            event_type="charge",
            description=description,
        )

    async def credit(self, user_id: int, amount: int, description: str) -> None:
        """Зачисляет кредиты.

        :param user_id: владелец.
        :param amount: сумма (>0).
        :param description: назначение.
        :return: None.
        """

        if amount <= 0:
            return
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("Пользователь не найден")
        user.balance += amount
        await self.repo.add_event(
            user_id=user_id,
            amount=amount,
            event_type="credit",
            description=description,
        )


class KeyService:
    """Бизнес-логика управления ключами."""

    def __init__(self, session: AsyncSession, settings: Settings):
        """Инициализирует сервис.

        :param session: сессия БД.
        :param settings: конфигурация приложения.
        """

        self.session = session
        self.settings = settings
        self.user_repo = UserRepository(session)
        self.key_repo = VpnKeyRepository(session)
        self.billing_repo = BillingRepository(session)
        self.alert_repo = AlertRepository(session)
        self.alerts = AlertService(self.alert_repo)
        self.billing = BillingService(session, self.billing_repo, self.user_repo)

    async def ensure_user(self, telegram_id: int, username: str | None) -> int:
        """Создаёт или возвращает пользователя.

        :param telegram_id: Telegram ID.
        :param username: username.
        :return: id пользователя в БД.
        """

        user = await self.user_repo.get_or_create(
            telegram_id=telegram_id, username=username, initial_balance=self.settings.initial_balance
        )
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

    async def _build_credentials(self, occupied: set[str]) -> WireGuardCredentials:
        """Генерирует ключи и конфиг.

        :param occupied: занятые адреса.
        :return: креды WireGuard.
        """

        try:
            private_key, public_key = generate_keypair()
        except Exception as exc:  # pylint: disable=broad-except
            raise ValueError("Не удалось сгенерировать WireGuard-ключи (wg)") from exc
        preshared = self.settings.wg_preshared_key or generate_preshared_key()
        client_address = allocate_client_address(self.settings.wg_client_address_cidr, occupied)
        config_text = build_client_config(
            private_key=private_key,
            client_address=client_address,
            settings=self.settings,
            preshared_key=preshared,
        )
        return WireGuardCredentials(
            private_key=private_key,
            public_key=public_key,
            client_address=client_address,
            preshared_key=preshared,
            config_text=config_text,
        )

    async def create_key(
        self,
        user_id: int,
        name: str,
        ttl_hours: int | None = None,
    ) -> KeyCreationResult:
        """Создаёт новый временный ключ с учётом лимитов и биллинга.

        :param user_id: id пользователя.
        :param name: имя ключа.
        :param ttl_hours: срок жизни в часах.
        :return: результат с моделью и конфигом.
        :raises ValueError: если превышен лимит или нет средств.
        """

        user = await self.user_repo.get_by_id(user_id)
        is_admin = bool(user and user.is_admin)

        existing = await self.key_repo.list_for_user(user_id)
        active = [k for k in existing if k.is_active]
        if not is_admin and len(active) >= self.settings.max_keys_per_user:
            raise ValueError("Превышен лимит устройств")

        hours = ttl_hours if ttl_hours is not None else self.settings.default_key_ttl_hours
        if hours <= 0:
            expires_at = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc) + dt.timedelta(
                days=3650
            )
        else:
            expires_at = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc) + dt.timedelta(
                hours=hours
            )

        occupied = await self.key_repo.active_addresses()
        credentials = await self._build_credentials(occupied)

        key = await self.key_repo.create(
            user_id=user_id,
            name=name,
            expires_at=expires_at,
            public_key=credentials.public_key,
            client_address=credentials.client_address,
            preshared_key=credentials.preshared_key,
        )
        return KeyCreationResult(key=key, credentials=credentials)

    async def revoke_key(self, key_id: uuid.UUID, user_id: int | None = None) -> bool:
        """Отзывает ключ и (опционально) проверяет владельца.

        :param key_id: идентификатор ключа.
        :param user_id: владелец, если нужно ограничить по пользователю.
        :return: True, если найден и отозван.
        """

        revoked = await self.key_repo.revoke(key_id, user_id=user_id)
        if revoked:
            await self.alerts.emit(
                level="info", message=f"Ключ {key_id} отозван", user_id=user_id
            )
        return revoked is not None

    async def rotate_key(
        self,
        key_id: uuid.UUID,
        user_id: int,
        ttl_hours: int | None = None,
    ) -> KeyCreationResult:
        """Ротирует ключ: отзывает старый и создаёт новый.

        :param key_id: идентификатор текущего ключа.
        :param user_id: владелец.
        :param ttl_hours: срок жизни нового ключа.
        :return: KeyCreationResult.
        :raises ValueError: если ключ не найден.
        """

        existing = await self.key_repo.get(key_id, user_id=user_id)
        if existing is None:
            raise ValueError("Ключ не найден")
        await self.key_repo.revoke(key_id, user_id=user_id)
        result = await self.create_key(
            user_id=user_id,
            name=f"{existing.name}-rotated",
            ttl_hours=ttl_hours,
        )
        result.key.rotated_from_id = key_id
        return result

    async def cleanup_expired(self) -> int:
        """Отзывает просроченные ключи и создаёт алерт.

        :return: количество отозванных ключей.
        """

        revoked_count = await self.key_repo.revoke_expired()
        if revoked_count:
            await self.alerts.emit(
                level="warn",
                message=f"Автоотзыв просроченных ключей: {revoked_count} шт.",
                user_id=None,
            )
        return revoked_count

    async def list_all(self) -> Sequence[VpnKey]:
        """Возвращает ключи для админ-панели.

        :return: список всех ключей.
        """

        return await self.key_repo.list_all()

    async def latest_alerts(self, limit: int = 10):
        """Возвращает последние алерты.

        :param limit: число записей.
        :return: последовательность алертов.
        """

        return await self.alerts.latest(limit=limit)
