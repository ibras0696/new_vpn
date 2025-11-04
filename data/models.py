import uuid
from datetime import datetime, timedelta, UTC

from sqlalchemy import String, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data.db import Base


class User(Base):
    """Модель пользователя Telegram.

    :param id: Первичный ключ.
    :param tg_id: Уникальный Telegram ID пользователя.
    :param username: Telegram username.
    :param is_admin: Флаг администратора.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    keys: Mapped[list["VlessKey"]] = relationship(back_populates="owner")


class VlessKey(Base):
    """Модель ключа VLESS для VPN.

    :param id: UUID ключа (используется самим сервером XRay).
    :param user_id: Владелец ключа.
    :param created_at: Дата создания.
    :param expires_at: Дата окончания действия (или None для бессрочных).
    :param active: Флаг активности.
    :param device_limit: Максимум одновременных подключений.
    :param traffic_limit_mb: Лимит трафика в мегабайтах (0 — без лимита).
    """

    __tablename__ = "vless_keys"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    device_limit: Mapped[int] = mapped_column(Integer, default=1)
    traffic_limit_mb: Mapped[int] = mapped_column(Integer, default=0)

    owner: Mapped["User"] = relationship(back_populates="keys")

    # Удобные методы ---------------------------------------------
    def is_expired(self) -> bool:
        """Возвращает True, если срок действия ключа истёк."""
        if self.expires_at is None:
            return False

        # Если expires_at "наивный" (без tzinfo) — делаем aware (UTC)
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)

        now = datetime.now(UTC)
        return now > exp

    def extend(self, days: int) -> None:
        """Продлевает срок действия ключа на заданное количество дней."""
        if not self.expires_at:
            self.expires_at = datetime.now(UTC) + timedelta(days=days)
        else:
            self.expires_at += timedelta(days=days)


class ConnectionLog(Base):
    """Лог активности ключа.

    :param id: Первичный ключ.
    :param key_id: ID ключа (внешний ключ).
    :param ip_address: IP-адрес подключения.
    :param connected_at: Время подключения.
    :param traffic_mb: Переданный трафик в мегабайтах.
    """

    __tablename__ = "connection_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    key_id: Mapped[str] = mapped_column(ForeignKey("vless_keys.id"), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64))
    connected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    traffic_mb: Mapped[float] = mapped_column(default=0.0)
