"""Token repository (R2, R3).

`refresh_tokens`, `token_blacklist` va `password_reset_codes` jadvallari ustida
ma'lumotlarga kirish. Autentifikatsiya_Moduli refresh tokenlarni saqlash/bekor
qilish, access token ``jti`` larni blacklistga qo'shish va parolni tiklash
kodlarini boshqarish uchun shu repository dan foydalanadi.

Eslatma: token va kod **xeshlangan** holda saqlanadi (``token_hash``,
``code_hash``). Xeshlash core/servis qatlamida (`app.core.tokens.hash_token`,
`app.core.security`) bajariladi; bu repository faqat xeshlangan qiymatlarni
persist qiladi va xesh bo'yicha qidiradi.

Konvensiyalar `base.py` bilan bir xil: konstruktorda `Session`, SQLAlchemy 2.x
`select()` uslubi, `add()` `flush` qiladi (commit emas).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import PasswordResetCode, RefreshToken, TokenBlacklist
from app.repositories.base import BaseRepository


class TokenRepository(BaseRepository[RefreshToken]):
    """Refresh token, blacklist va reset-kod uchun repository (R2, R3)."""

    model = RefreshToken

    # --- Refresh tokenlar (R2.3, R2.4, R2.6) ---

    def store_refresh(
        self, *, user_id: int, token_hash: str, expires_at: datetime
    ) -> RefreshToken:
        """Refresh token xeshini saqlaydi (R2.1, R2.6)."""
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked=False,
        )
        return self.add(token)

    def get_refresh_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Xesh bo'yicha refresh tokenni qaytaradi (R2.3, R2.6)."""
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash
        )
        return self.session.scalar(stmt)

    def revoke_refresh(self, token: RefreshToken) -> RefreshToken:
        """Refresh tokenni bekor qiladi — ``revoked=true`` (R2.4, R2.6)."""
        token.revoked = True
        self.session.flush()
        return token

    def revoke_all_for_user(self, user_id: int) -> int:
        """Foydalanuvchining barcha faol refresh tokenlarini bekor qiladi (R2.4).

        Returns:
            Bekor qilingan tokenlar soni.
        """
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked.is_(False),
        )
        tokens = list(self.session.scalars(stmt).all())
        for token in tokens:
            token.revoked = True
        self.session.flush()
        return len(tokens)

    # --- Access token blacklist (R2.4, R2.5) ---

    def blacklist_jti(self, jti: str, expires_at: datetime) -> TokenBlacklist:
        """Access token ``jti`` ni blacklistga qo'shadi (R2.4, R2.5).

        Allaqachon qora ro'yxatda bo'lsa mavjud yozuvni qaytaradi (idempotent).
        """
        existing = self.session.get(TokenBlacklist, jti)
        if existing is not None:
            return existing
        entry = TokenBlacklist(jti=jti, expires_at=expires_at)
        self.session.add(entry)
        self.session.flush()
        return entry

    def is_jti_blacklisted(self, jti: str) -> bool:
        """Berilgan ``jti`` qora ro'yxatda ekanligini tekshiradi (R2.5)."""
        return self.session.get(TokenBlacklist, jti) is not None

    # --- Parolni tiklash kodlari (R3) ---

    def create_reset_code(
        self, *, user_id: int, code_hash: str, expires_at: datetime
    ) -> PasswordResetCode:
        """Parolni tiklash kodi xeshini yaratadi (R3.1, R3.4)."""
        code = PasswordResetCode(
            user_id=user_id,
            code_hash=code_hash,
            expires_at=expires_at,
            attempts=0,
            consumed=False,
        )
        self.session.add(code)
        self.session.flush()
        return code

    def get_active_reset_code(
        self, user_id: int
    ) -> PasswordResetCode | None:
        """Foydalanuvchining eng so'nggi sarflanmagan reset kodini qaytaradi (R3.3).

        Faqat ``consumed=false`` yozuv qaytariladi; amal qilish muddati (R3.4) va
        urinishlar soni (R3.7) servis/domen qatlamida tekshiriladi.
        """
        stmt = (
            select(PasswordResetCode)
            .where(
                PasswordResetCode.user_id == user_id,
                PasswordResetCode.consumed.is_(False),
            )
            .order_by(PasswordResetCode.id.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def increment_reset_attempts(
        self, code: PasswordResetCode
    ) -> int:
        """Reset kod urinishlar hisoblagichini bittaga oshiradi (R3.7).

        Returns:
            Yangilangan urinishlar soni.
        """
        code.attempts = (code.attempts or 0) + 1
        self.session.flush()
        return code.attempts

    def consume_reset_code(
        self, code: PasswordResetCode
    ) -> PasswordResetCode:
        """Reset kodni sarflangan (bir martalik) deb belgilaydi (R3.6, R3.7)."""
        code.consumed = True
        self.session.flush()
        return code


__all__ = ["TokenRepository"]
