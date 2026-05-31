"""Foydalanuvchi repository (R1, R2, R5).

`users` jadvali ustida ma'lumotlarga kirish. Login bloklash (R2.7) holatini
saqlash/tiklash uchun yordamchi metodlar ham shu yerda — ammo bloklash *qoidasi*
(5 urinish -> 15 daqiqa) servis/domen qatlamida hisoblanadi; bu repository faqat
hisoblangan qiymatlarni persist qiladi.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """`users` jadvali uchun repository."""

    model = User

    def get_by_id(self, user_id: int) -> User | None:
        """ID bo'yicha foydalanuvchini qaytaradi (yoki ``None``)."""
        return self.session.get(User, user_id)

    def get_by_phone(self, phone: str) -> User | None:
        """Telefon raqami (hisob identifikatori) bo'yicha foydalanuvchi (R2.1)."""
        return self.session.scalar(select(User).where(User.phone == phone))

    def phone_exists(self, phone: str) -> bool:
        """Telefon raqami allaqachon ro'yxatdan o'tganini tekshiradi (R1.2)."""
        return self.get_by_phone(phone) is not None

    def create(
        self,
        *,
        full_name: str,
        phone: str,
        password_hash: str,
        role_id: int,
        organization_id: int | None = None,
        region_id: int | None = None,
        position: str | None = None,
        experience_years: int | None = None,
        education_level: str | None = None,
        qualification_courses: str | None = None,
        certificates: str | None = None,
        org_type: str | None = None,
    ) -> User:
        """Yangi foydalanuvchi yaratadi va `flush` qiladi (R1.1, R1.4)."""
        user = User(
            full_name=full_name,
            phone=phone,
            password_hash=password_hash,
            role_id=role_id,
            organization_id=organization_id,
            region_id=region_id,
            position=position,
            experience_years=experience_years,
            education_level=education_level,
            qualification_courses=qualification_courses,
            certificates=certificates,
            org_type=org_type,
        )
        return self.add(user)

    def update(self, user: User, **fields: object) -> User:
        """Berilgan maydonlarni yangilaydi (R5.2).

        Faqat ``User`` da mavjud atributlar o'rnatiladi; ``phone`` o'zgarmas
        hisob identifikatori bo'lgani uchun bu yerda himoyalanadi (R5.4 —
        validatsiya servisda, ammo repository ham telefonni e'tiborsiz qoldiradi).
        """
        for key, value in fields.items():
            if key == "phone":
                continue
            if hasattr(user, key):
                setattr(user, key, value)
        self.session.flush()
        return user

    def set_lockout(
        self, user: User, *, locked_until: datetime, failed_login_count: int
    ) -> User:
        """Login bloklash holatini saqlaydi (R2.7).

        Bloklash qoidasi (urinishlar soni, muddat) servis/domen qatlamida
        hisoblanadi; bu metod faqat natijani persist qiladi.
        """
        user.locked_until = locked_until
        user.failed_login_count = failed_login_count
        self.session.flush()
        return user

    def increment_failed_login(self, user: User) -> int:
        """Muvaffaqiyatsiz kirish hisoblagichini bittaga oshiradi (R2.7).

        Returns:
            Yangilangan hisoblagich qiymati.
        """
        user.failed_login_count = (user.failed_login_count or 0) + 1
        self.session.flush()
        return user.failed_login_count

    def reset_lockout(self, user: User) -> User:
        """Muvaffaqiyatli kirishda bloklashni nolga tushiradi (R2.7)."""
        user.failed_login_count = 0
        user.locked_until = None
        self.session.flush()
        return user


__all__ = ["UserRepository"]
