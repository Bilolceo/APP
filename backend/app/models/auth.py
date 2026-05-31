"""Autentifikatsiya yordamchi jadvallari va push qurilma tokenlari.

design.md — "Autentifikatsiya yordamchi jadvallari" va "device_tokens (R16)":
- refresh_tokens(id, user_id FK, token_hash, expires_at, revoked BOOLEAN)
- token_blacklist(jti, expires_at)
- password_reset_codes(id, user_id FK, code_hash, expires_at, attempts SMALLINT,
  consumed BOOLEAN)
- device_tokens(id, user_id FK, token TEXT, platform VARCHAR(10), is_valid BOOLEAN,
  created_at)
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntType, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(Base):
    """30 kunlik refresh token; logout'da ``revoked=true`` (R2.1, R2.4, R2.6)."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class TokenBlacklist(Base):
    """Bekor qilingan access token JTI'lari (R2.4, R2.5)."""

    __tablename__ = "token_blacklist"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class PasswordResetCode(Base):
    """6 raqamli, 15 daqiqalik parolni tiklash kodi (R3.1, R3.4, R3.7)."""

    __tablename__ = "password_reset_codes"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    attempts: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    consumed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    user: Mapped["User"] = relationship(back_populates="password_reset_codes")


class DeviceToken(TimestampMixin, Base):
    """Push uchun qurilma tokeni; yaroqsiz token o'tkazib yuboriladi (R16.6)."""

    __tablename__ = "device_tokens"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_valid: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    user: Mapped["User"] = relationship(back_populates="device_tokens")


__all__ = [
    "RefreshToken",
    "TokenBlacklist",
    "PasswordResetCode",
    "DeviceToken",
]
