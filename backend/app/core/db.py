"""Ma'lumotlar bazasi dvigateli (engine) va sessiya sozlamasi.

`app.core.config.settings.database_url` dan o'qiydi va SQLAlchemy 2.x
`Engine` hamda `sessionmaker` ni sozlaydi. Servis/repository qatlamlari (task
2.3+) sessiyaga `get_session` orqali kiradi.

Bog'liq talablar:
- R8.6: natijalarni doimiy saqlash (PostgreSQL).
- R14.8: referensial yaxlitlik (ORM/DB qatlami).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.base import Base


def create_db_engine(database_url: str | None = None, *, echo: bool = False) -> Engine:
    """Sozlamalardagi (yoki berilgan) URL bo'yicha SQLAlchemy `Engine` yaratadi.

    Args:
        database_url: ulanish satri; ``None`` bo'lsa ``settings.database_url``.
        echo: SQL'ni jurnalga chiqarish (debug uchun).

    Returns:
        Sozlangan `Engine`.
    """
    url = database_url or settings.database_url
    return create_engine(
        url,
        echo=echo,
        future=True,
        pool_pre_ping=True,
    )


# Modul darajasidagi yagona engine va sessiya faktori.
engine: Engine = create_db_engine(echo=settings.debug)

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


@contextmanager
def get_session() -> Iterator[Session]:
    """Tranzaksiya doirasidagi sessiya kontekst-menejeri.

    Muvaffaqiyatda `commit`, xatoda `rollback` qiladi va har holda sessiyani
    yopadi. Repository/servis qatlamlari uchun qulay kirish nuqtasi.

    Yields:
        Faol `Session`.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Barcha jadvallarni metama'lumotdan yaratadi (test/dev qulayligi uchun).

    Ishlab chiqarish (production) muhitida sxema Alembic migratsiyalari (task
    2.2) orqali boshqariladi; bu funksiya asosan lokal sinov uchun.
    """
    # Modellarni import qilish — ular `Base.metadata` ga ro'yxatdan o'tishi uchun.
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


__all__ = [
    "engine",
    "SessionLocal",
    "get_session",
    "create_db_engine",
    "init_db",
]
