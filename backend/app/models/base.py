"""Umumiy deklarativ `Base` — barcha ORM modellari uchun yagona reestr.

SQLAlchemy 2.x `DeclarativeBase` uslubidan foydalaniladi. Barcha jadval
modellari shu `Base` dan meros oladi, shunda ular bitta `MetaData` reestrida
ro'yxatga olinadi (Alembic migratsiyalari — task 2.2 — shu metama'lumotdan
foydalanadi).

Bog'liq talablar: R1.1, R5.1, R6.1, R7.1, R8.6, R10.1, R11.1, R13.1, R16.1, R18.1
(barcha doimiy jadvallar ORM modeli).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Birlamchi kalit turi: PostgreSQL'da BIGINT (BIGSERIAL), sinov uchun SQLite'da
# esa INTEGER (rowid autoincrement) sifatida ishlaydi. Bu domen/ishlab chiqarish
# sxemasini (BIGSERIAL) o'zgartirmasdan modellarni SQLite ustida ham sinovdan
# o'tkazishga imkon beradi. ForeignKey ustunlari turni nishon (target) ustundan
# meros qilib oladi, shuning uchun ular ham mos variantni oladi.
BigIntType = BigInteger().with_variant(Integer, "sqlite")

# Cheklov nomlash konvensiyasi — Alembic autogenerate uchun barqaror nomlar
# ta'minlaydi (task 2.2). PostgreSQL'da indeks/cheklov nomlari deterministik
# bo'lishi migratsiyalarni qayta ishlab chiqarishni yengillashtiradi.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Barcha ORM modellari uchun deklarativ asos."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """`created_at` ustunini taqdim etuvchi mixin (TIMESTAMPTZ DEFAULT now()).

    design.md: "Barcha ... `created_at` esa `TIMESTAMPTZ DEFAULT now()`".
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


__all__ = ["Base", "TimestampMixin", "NAMING_CONVENTION", "BigIntType"]
