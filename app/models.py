from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс моделей."""

    pass


def utcnow() -> dt.datetime:
    """Возвращает текущую дату/время в UTC.

    :return: datetime с tzinfo=UTC.
    """

    return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)


class VpnKey(Base):
    """Временный VPN-ключ (stub под WireGuard-пир)."""

    __tablename__ = "vpn_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(120))
    public_key: Mapped[str | None] = mapped_column(String(512))
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="keys")

    @property
    def is_active(self) -> bool:
        """Проверяет, действует ли ключ.

        :return: True, если ключ не просрочен и не отозван.
        """

        now = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
        return self.revoked_at is None and self.expires_at > now
class User(Base):
    """Пользователь Telegram."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    keys: Mapped[list["VpnKey"]] = relationship(back_populates="user")
