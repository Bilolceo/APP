"""Portfolio repository (R11).

`portfolios` va `files` jadvallari ustida ma'lumotlarga kirish. Portfolio_Moduli
fayl yuklash, ro'yxat va o'chirishni shu repository orqali bajaradi. Faylning
fizik saqlanishi `FileStorage` abstraksiyasi orqali boshqariladi; bu repository
faqat metama'lumot (DB qatori) bilan ishlaydi.

Konvensiyalar `base.py` bilan bir xil.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.portfolio import File, Portfolio
from app.repositories.base import BaseRepository


class PortfolioRepository(BaseRepository[Portfolio]):
    """`portfolios` + `files` uchun repository (R11)."""

    model = Portfolio

    def get_by_id(self, portfolio_id: int) -> Portfolio | None:
        """ID bo'yicha portfolio yozuvini (fayl bilan) qaytaradi."""
        stmt = (
            select(Portfolio)
            .where(Portfolio.id == portfolio_id)
            .options(selectinload(Portfolio.file))
        )
        return self.session.scalar(stmt)

    def get_for_user(
        self, user_id: int, portfolio_id: int
    ) -> Portfolio | None:
        """Portfolioni egalik tekshiruvi bilan qaytaradi (R11.5, R11.6).

        So'rovchiga tegishli bo'lmasa ``None`` (servisda 404/403 ga aylanadi).
        """
        stmt = (
            select(Portfolio)
            .where(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == user_id,
            )
            .options(selectinload(Portfolio.file))
        )
        return self.session.scalar(stmt)

    def list_for_user(self, user_id: int) -> list[Portfolio]:
        """Foydalanuvchi portfoliosini sana bo'yicha kamayuvchi tartibda (R11.1).

        Yozuv bo'lmasa bo'sh ro'yxat qaytariladi.
        """
        stmt = (
            select(Portfolio)
            .where(Portfolio.user_id == user_id)
            .options(selectinload(Portfolio.file))
            .order_by(Portfolio.created_at.desc(), Portfolio.id.desc())
        )
        return list(self.session.scalars(stmt).all())

    def create(
        self,
        *,
        user_id: int,
        title: str,
        storage_key: str,
        file_url: str | None = None,
        file_type: str | None = None,
        size_bytes: int | None = None,
    ) -> Portfolio:
        """Fayl metama'lumoti va portfolio yozuvini yaratadi (R11.2).

        ``files`` qatori avval yaratiladi (ID uchun `flush`), so'ng portfolio
        yozuviga bog'lanadi.
        """
        file_row = File(
            storage_key=storage_key,
            file_url=file_url,
            file_type=file_type,
            size_bytes=size_bytes,
        )
        self.session.add(file_row)
        self.session.flush()
        portfolio = Portfolio(
            user_id=user_id,
            title=title,
            file_id=file_row.id,
        )
        portfolio.file = file_row
        return self.add(portfolio)

    def delete(self, portfolio: Portfolio) -> None:
        """Portfolio yozuvini va bog'langan fayl qatorini o'chiradi (R11.5, R11.7).

        Fizik fayl `FileStorage` orqali servisda o'chiriladi; bu yerda faqat DB
        qatorlari olib tashlanadi.
        """
        file_row = portfolio.file
        self.session.delete(portfolio)
        if file_row is not None:
            self.session.delete(file_row)
        self.session.flush()


__all__ = ["PortfolioRepository"]
