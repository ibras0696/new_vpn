"""
Репозиторий для управления таблицей VLESS-ключей.
Реализует CRUD-операции для модели VlessKey.
"""
import uuid
from datetime import datetime, UTC, timedelta

from sqlalchemy import select, delete

from data.models import VlessKey


class VlessKeyRepo:
    """Репозиторий для работы с VLESS-ключами."""

    def __init__(self, session):
        """
        Инициализация репозитория.

        :param session: Активная асинхронная сессия SQLAlchemy.
        """
        self.session = session

    # ----------------------------------------------------------------------
    async def create(self, user_id: int, days: int | None = None, device_limit: int = 1) -> VlessKey:
        """
        Создаёт новый VLESS-ключ.

        :param user_id: ID пользователя-владельца.
        :param days: Срок действия ключа (в днях). Если None — ключ бессрочный.
        :param device_limit: Максимум устройств, которые могут подключаться.
        :return: Объект VlessKey.
        """
        expires_at = None
        if days is not None:
            expires_at = datetime.now(UTC) + timedelta(days=days)

        key = VlessKey(user_id=user_id, expires_at=expires_at, device_limit=device_limit)
        self.session.add(key)
        await self.session.commit()
        await self.session.refresh(key)
        return key

    # ----------------------------------------------------------------------
    async def extend_key(self, key_id: str, days: int) -> VlessKey | None:
        """
        Продлевает срок действия ключа на указанное количество дней.

        :param key_id: UUID ключа.
        :param days: Количество дней продления.
        :return: Обновлённый объект VlessKey или None, если не найден.
        """
        key = await self.session.get(VlessKey, key_id)
        if not key:
            return None

        if key.expires_at:
            key.expires_at += timedelta(days=days)
        else:
            key.expires_at = datetime.now(UTC) + timedelta(days=days)

        await self.session.commit()
        await self.session.refresh(key)
        return key

    # ----------------------------------------------------------------------
    async def delete(self, key_id: str) -> bool:
        """
        Удаляет ключ по UUID (строке или объекту uuid.UUID).

        :param key_id: UUID ключа в виде строки или uuid.UUID.
        :return: True, если удалён; False, если не найден.
        """
        # Преобразуем строку в UUID, если нужно
        if isinstance(key_id, str):
            try:
                key_id = uuid.UUID(key_id)
            except ValueError:
                # если некорректный формат — просто вернуть False
                return False

        stmt = delete(VlessKey).where(VlessKey.id == key_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    # ----------------------------------------------------------------------
    async def list_all(self, only_active: bool = True) -> list[VlessKey]:
        """
        Возвращает список всех VLESS-ключей.

        :param only_active: Если True — возвращает только активные.
        :return: Список ORM-объектов VlessKey.
        """
        stmt = select(VlessKey)
        if only_active:
            stmt = stmt.where(VlessKey.active == True)

        result = await self.session.execute(stmt.order_by(VlessKey.created_at.desc()))
        return result.scalars().all()

    # ----------------------------------------------------------------------
    async def get(self, key_id: str) -> VlessKey | None:
        """
        Получает один ключ по UUID.

        :param key_id: UUID ключа.
        :return: Объект VlessKey или None.
        """
        return await self.session.get(VlessKey, key_id)

# from datetime import datetime, timedelta, UTC
#
# from sqlalchemy import select, update, delete
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from data.models import VlessKey
#
#
# class VlessKeyRepo:
#     """Репозиторий для работы с таблицей VlessKey."""
#
#     def __init__(self, session: AsyncSession):
#         self.session = session
#
#     async def create(
#             self,
#             user_id: int,
#             days: int | None = None,
#             device_limit: int = 1,
#             traffic_limit_mb: int = 0,
#     ) -> VlessKey:
#         """
#         Создаёт новый VLESS-ключ.
#
#         :param user_id: Идентификатор владельца (ForeignKey -> users.id).
#         :param days: Срок действия ключа в днях. Если None — ключ бессрочный.
#         :param device_limit: Максимальное число устройств.
#         :param traffic_limit_mb: Лимит трафика в мегабайтах (0 — без лимита).
#         :return: Объект VlessKey.
#         """
#
#         # Вычисляем дату истечения (aware datetime в UTC)
#         expires_at = None
#         if days is not None:
#             expires_at = datetime.now(UTC) + timedelta(days=days)
#
#         key = VlessKey(
#             user_id=user_id,
#             expires_at=expires_at,
#             device_limit=device_limit,
#             traffic_limit_mb=traffic_limit_mb,
#         )
#
#         self.session.add(key)
#         await self.session.commit()
#         await self.session.refresh(key)
#         return key
#
#     async def get(self, key_id) -> VlessKey | None:
#         """
#         Возвращает ключ по UUID.
#
#         :param key_id: UUID ключа.
#         :return: Объект VlessKey или None.
#         """
#         result = await self.session.execute(select(VlessKey).where(VlessKey.id == key_id))
#         return result.scalar_one_or_none()
#
#     async def delete(self, key_id) -> bool:
#         """
#         Удаляет ключ из базы.
#
#         :param key_id: UUID ключа.
#         :return: True, если удаление успешно.
#         """
#         result = await self.session.execute(delete(VlessKey).where(VlessKey.id == key_id))
#         await self.session.commit()
#         return result.rowcount > 0
#
#     async def extend_key(self, key_id, days: int) -> VlessKey | None:
#         """
#         Продлевает срок действия ключа на N дней.
#
#         :param key_id: UUID ключа.
#         :param days: Количество дней продления.
#         :return: Обновлённый объект VlessKey или None.
#         """
#         key = await self.get(key_id)
#         if not key:
#             return None
#         key.extend(days)
#         await self.session.commit()
#         await self.session.refresh(key)
#         return key
#
#     async def deactivate_expired(self) -> int:
#         """
#         Деактивирует все истёкшие ключи.
#
#         :return: Количество деактивированных записей.
#         """
#         result = await self.session.execute(
#             update(VlessKey)
#             .where(VlessKey.expires_at < datetime.utcnow(), VlessKey.active == True)
#             .values(active=False)
#         )
#         await self.session.commit()
#         return result.rowcount
