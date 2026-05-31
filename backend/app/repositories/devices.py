"""Qurilma tokeni repository (R16).

`device_tokens` jadvali ustida ma'lumotlarga kirish. Bildirishnoma_Xizmati push
yuborish uchun yaroqli qurilma tokenlarini shu repository orqali oladi; yaroqsiz
token o'tkazib yuboriladi (R16.6).

Konvensiyalar `base.py` bilan bir xil.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import DeviceToken
from app.repositories.base import BaseRepository


class DeviceTokenRepository(BaseRepository[DeviceToken]):
    """`device_tokens` uchun repository (R16)."""

    model = DeviceToken

    def get_by_token(self, token: str) -> DeviceToken | None:
        """Token qiymati bo'yicha qurilma yozuvini qaytaradi."""
        stmt = select(DeviceToken).where(DeviceToken.token == token)
        return self.session.scalar(stmt)

    def register(
        self, *, user_id: int, token: str, platform: str | None = None
    ) -> DeviceToken:
        """Qurilma tokenini ro'yxatdan o'tkazadi (R16.1).

        Bir xil token allaqachon mavjud bo'lsa, uni egasiga/platformaga
        yangilab, yaroqli (``is_valid=true``) holatga keltiradi (idempotent
        ro'yxatga olish).
        """
        existing = self.get_by_token(token)
        if existing is not None:
            existing.user_id = user_id
            existing.platform = platform
            existing.is_valid = True
            self.session.flush()
            return existing
        device = DeviceToken(
            user_id=user_id,
            token=token,
            platform=platform,
            is_valid=True,
        )
        return self.add(device)

    def invalidate(self, token: str) -> DeviceToken | None:
        """Tokenni yaroqsiz deb belgilaydi — ``is_valid=false`` (R16.6).

        Token topilmasa ``None`` qaytaradi (xato emas).
        """
        device = self.get_by_token(token)
        if device is None:
            return None
        device.is_valid = False
        self.session.flush()
        return device

    def list_valid_for_users(
        self, user_ids: Sequence[int]
    ) -> list[DeviceToken]:
        """Berilgan foydalanuvchilarning yaroqli qurilma tokenlarini qaytaradi (R16.5, R16.6).

        Faqat ``is_valid=true`` tokenlar qaytariladi. Bo'sh ro'yxat berilsa bo'sh
        natija qaytadi (keraksiz so'rovsiz).
        """
        if not user_ids:
            return []
        stmt = (
            select(DeviceToken)
            .where(
                DeviceToken.user_id.in_(list(user_ids)),
                DeviceToken.is_valid.is_(True),
            )
            .order_by(DeviceToken.id)
        )
        return list(self.session.scalars(stmt).all())


__all__ = ["DeviceTokenRepository"]
