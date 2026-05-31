"""Portfolio va fayl jadvallari: portfolios, files (R11, R18.2).

design.md — "portfolios (R11) va files":
- portfolios(id, user_id FK, title VARCHAR(200), file_id FK -> files, created_at)
- files(id, storage_key, file_url, file_type VARCHAR(10), size_bytes BIGINT, created_at)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntType, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class File(TimestampMixin, Base):
    """Saqlangan fayl metama'lumoti — `FileStorage` abstraksiyasi (R11.2, R18.2)."""

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    # provayderdan mustaqil noyob kalit
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    portfolio: Mapped["Portfolio | None"] = relationship(back_populates="file")


class Portfolio(TimestampMixin, Base):
    """Foydalanuvchi portfolio yozuvi (R11.1)."""

    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # nom 1–200 belgi (R11.2)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    file_id: Mapped[int | None] = mapped_column(
        ForeignKey("files.id"), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="portfolios")
    file: Mapped["File | None"] = relationship(back_populates="portfolio")


__all__ = ["File", "Portfolio"]
