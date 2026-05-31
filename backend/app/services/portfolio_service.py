"""Portfolio_Moduli — fayl yuklash, ro'yxat va o'chirish servisi (R11).

Ushbu servis framework'dan mustaqil (FastAPI'siz): konstruktorga SQLAlchemy
`Session` yoki tayyor `PortfolioRepository` hamda `FileStorageBackend`
implementatsiyasi (`LocalFileStorage` — MVP) beriladi. Biznes qoidalari shu
yerda hal qilinadi; repository qatlami metama'lumot (DB qatori) bilan, xotira
backend'i esa fizik fayl bilan ishlaydi.

Mas'uliyat (design.md — "Portfolio_Moduli"):
- ``list_portfolio(user_id)`` — yaratilgan sana bo'yicha kamayish tartibida
  (R11.1); yozuv bo'lmasa bo'sh ro'yxat.
- ``upload(user_id, filename, file_bytes, content_type, title)`` — fayl turi
  (PDF/JPG/PNG/DOC/DOCX; kengaytma + MIME/magic-bytes), hajmi (≤10 485 760 bayt)
  va nom (1–200 belgi) validatsiyasi; yaroqsiz bo'lsa hech narsa saqlanmaydi
  (R11.2, R11.3, R11.4, R17.4).
- ``delete(user_id, portfolio_id)`` — egalik tekshiruvi (begona -> 403, R11.6),
  yo'q bo'lsa 404 (R11.7); DB qatorlari va fizik fayl o'chiriladi (R11.5).

Xato tiplari: ``ValidationError`` va ``NotFoundError`` `app.services.errors` dan
qayta ishlatiladi. Egalik buzilishi (403) uchun `app.services.errors` da maxsus
tip yo'q, shuning uchun shu modulda `ServiceError` ustiga ``PermissionDeniedError``
(``code="forbidden"``) belgilanadi — bu router qatlamida 403 ga keltiriladi.
``errors.py`` o'zgartirilmaydi.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.portfolio import Portfolio
from app.repositories.portfolio import PortfolioRepository
from app.services.errors import NotFoundError, ServiceError, ValidationError
from app.storage.base import FileStorageBackend


# ---------------------------------------------------------------------------
# Egalik buzilishi (403) — errors.py da maxsus tip yo'q, shu yerda belgilanadi.
# ---------------------------------------------------------------------------
class PermissionDeniedError(ServiceError):
    """So'rovchi resursga ega emas — HTTP 403 (R11.6, R4.5).

    `app.services.errors` da Forbidden/Authorization tipi mavjud emas; uni
    o'zgartirmaslik uchun shu servis modulida `ServiceError` ustiga aniq
    semantik tip belgilanadi. Router qatlami ``code="forbidden"`` ni 403 ga
    keltiradi.
    """

    code = "forbidden"


# ---------------------------------------------------------------------------
# Fayl turi katalogi va validatsiya cheklovlari (R11.2, R11.3, R17.4)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _FileType:
    """Ruxsat etilgan fayl turi tavsifi (kengaytma + magic + MIME)."""

    name: str
    extensions: frozenset[str]
    magic_prefixes: tuple[bytes, ...]
    content_types: frozenset[str]


# Ruxsat etilgan turlar: PDF, JPG, PNG, DOC, DOCX (R11.2).
_FILE_TYPES: tuple[_FileType, ...] = (
    _FileType(
        name="pdf",
        extensions=frozenset({"pdf"}),
        magic_prefixes=(b"%PDF",),
        content_types=frozenset({"application/pdf"}),
    ),
    _FileType(
        name="jpg",
        extensions=frozenset({"jpg", "jpeg"}),
        magic_prefixes=(b"\xff\xd8\xff",),
        content_types=frozenset({"image/jpeg", "image/jpg"}),
    ),
    _FileType(
        name="png",
        extensions=frozenset({"png"}),
        magic_prefixes=(b"\x89PNG\r\n\x1a\n",),
        content_types=frozenset({"image/png"}),
    ),
    _FileType(
        name="doc",
        extensions=frozenset({"doc"}),
        # OLE2 (Compound File Binary) imzosi.
        magic_prefixes=(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
        content_types=frozenset({"application/msword"}),
    ),
    _FileType(
        name="docx",
        extensions=frozenset({"docx"}),
        # DOCX — ZIP konteyner (PK..).
        magic_prefixes=(b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
        content_types=frozenset(
            {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/zip",
            }
        ),
    ),
)

#: Kengaytma -> fayl turi tavsifi (tez qidirish uchun).
_EXTENSION_INDEX: dict[str, _FileType] = {
    ext: ft for ft in _FILE_TYPES for ext in ft.extensions
}

#: Ruxsat etilgan kengaytmalar to'plami (xato xabarlari uchun).
ALLOWED_EXTENSIONS: frozenset[str] = frozenset(_EXTENSION_INDEX)

#: Generik/noma'lum MIME turlari — bu holatda kengaytma + magic'ga tayaniladi.
_GENERIC_CONTENT_TYPES: frozenset[str] = frozenset(
    {"", "application/octet-stream", "binary/octet-stream"}
)

#: Maksimal fayl hajmi — 10 MB (R11.4); sozlamadan o'qiladi.
MAX_UPLOAD_SIZE_BYTES: int = settings.max_upload_size_bytes

#: Nom uzunligi chegarasi (R11.2).
MIN_TITLE_LENGTH = 1
MAX_TITLE_LENGTH = 200


@dataclass(frozen=True)
class PortfolioItem:
    """Portfolio yozuvi — o'qish uchun transient ko'rinish (R11.1)."""

    id: int
    title: str
    file_url: str | None
    file_type: str | None
    size_bytes: int | None
    storage_key: str | None
    created_at: datetime | None


def _to_item(portfolio: Portfolio) -> PortfolioItem:
    """`Portfolio` ORM yozuvini transient `PortfolioItem` ga aylantiradi."""
    file_row = portfolio.file
    return PortfolioItem(
        id=portfolio.id,
        title=portfolio.title,
        file_url=getattr(file_row, "file_url", None),
        file_type=getattr(file_row, "file_type", None),
        size_bytes=getattr(file_row, "size_bytes", None),
        storage_key=getattr(file_row, "storage_key", None),
        created_at=getattr(portfolio, "created_at", None),
    )


def _validation_error(message: str, field: str | None) -> ValidationError:
    """Yaroqsiz maydonni ko'rsatuvchi `ValidationError` yaratadi (R20.6)."""
    return ValidationError(message, field=field)


class PortfolioService:
    """Portfolio fayllarini boshqaruvchi servis (R11)."""

    def __init__(
        self,
        repo: PortfolioRepository | Session,
        storage: FileStorageBackend,
    ) -> None:
        """`PortfolioRepository` yoki `Session` hamda fayl xotirasi backend'i.

        Args:
            repo: tayyor `PortfolioRepository` yoki uni qurish uchun `Session`.
            storage: `FileStorageBackend` implementatsiyasi (`LocalFileStorage`).
        """
        self._repo = (
            repo if isinstance(repo, PortfolioRepository) else PortfolioRepository(repo)
        )
        self._storage = storage

    # -- O'qish -------------------------------------------------------------

    def list_portfolio(self, user_id: int) -> list[PortfolioItem]:
        """Foydalanuvchi portfoliosini sana bo'yicha kamayuvchi tartibda (R11.1).

        Yozuv bo'lmasa bo'sh ro'yxat qaytariladi (xato emas).
        """
        return [_to_item(p) for p in self._repo.list_for_user(user_id)]

    # -- Yuklash ------------------------------------------------------------

    def upload(
        self,
        user_id: int,
        filename: str,
        file_bytes: bytes,
        *,
        content_type: str | None = None,
        title: str | None = None,
    ) -> PortfolioItem:
        """Faylni validatsiya qilib saqlaydi va portfolio yozuvini yaratadi.

        Validatsiya (har biri muvaffaqiyatsizda hech narsa saqlanmaydi):
        - nom 1–200 belgi va faqat bo'sh joydan iborat emas (R11.2);
        - tur PDF/JPG/PNG/DOC/DOCX — kengaytma hamda magic-bytes/MIME (R11.3,
          R17.4);
        - hajm ≤ 10 485 760 bayt (R11.4).

        Args:
            user_id: yozuv egasi.
            filename: original fayl nomi (kengaytma va, ``title`` berilmasa,
                nom uchun manba).
            file_bytes: fayl mazmuni.
            content_type: yuklash MIME turi (ixtiyoriy; mavjud bo'lsa tekshiriladi).
            title: portfolio nomi; ``None`` bo'lsa ``filename`` ishlatiladi.

        Returns:
            Yaratilgan `PortfolioItem`.

        Raises:
            ValidationError: nom, tur yoki hajm yaroqsiz bo'lsa (hech narsa
                saqlanmaydi).
        """
        # 1) Nom validatsiyasi (R11.2).
        clean_title = self._validate_title(title if title is not None else filename)

        # 2) Tur validatsiyasi — kengaytma + magic-bytes/MIME (R11.3, R17.4).
        file_type = self._validate_type(filename, file_bytes, content_type)

        # 3) Hajm validatsiyasi (R11.4).
        size = len(file_bytes)
        if size > MAX_UPLOAD_SIZE_BYTES:
            raise _validation_error(
                f"Fayl hajmi {MAX_UPLOAD_SIZE_BYTES} baytdan oshmasligi kerak",
                "file",
            )

        # Validatsiya to'liq o'tdi -> saqlash. Avval fizik fayl, keyin DB yozuvi.
        storage_key = self._generate_storage_key(filename)
        stored = self._storage.save(storage_key, file_bytes, content_type=content_type)

        portfolio = self._repo.create(
            user_id=user_id,
            title=clean_title,
            storage_key=stored.storage_key,
            file_url=stored.url,
            file_type=file_type.name,
            size_bytes=stored.size_bytes,
        )
        return _to_item(portfolio)

    # -- O'chirish ----------------------------------------------------------

    def delete(self, user_id: int, portfolio_id: int) -> None:
        """Portfolio yozuvini va bog'langan faylni o'chiradi (R11.5–R11.7).

        Args:
            user_id: so'rovchi foydalanuvchi.
            portfolio_id: o'chiriladigan yozuv identifikatori.

        Raises:
            NotFoundError: yozuv mavjud bo'lmasa (R11.7).
            PermissionDeniedError: yozuv boshqa foydalanuvchiga tegishli bo'lsa
                (R11.6) — holat o'zgarmaydi.
        """
        portfolio = self._repo.get_by_id(portfolio_id)
        if portfolio is None:
            raise NotFoundError(f"Portfolio yozuvi topilmadi (id={portfolio_id})")
        if portfolio.user_id != user_id:
            # Begona yozuv: hech narsa o'zgartirmasdan/oshkor qilmasdan 403 (R11.6).
            raise PermissionDeniedError("Bu portfolio yozuviga ruxsat yo'q")

        # Fizik faylni o'chirish uchun kalitni avval olamiz.
        storage_key = getattr(portfolio.file, "storage_key", None)

        # DB qatorlarini (portfolio + fayl) o'chirish (R11.5).
        self._repo.delete(portfolio)

        # Fizik faylni xotiradan o'chirish (idempotent).
        if storage_key:
            self._storage.delete(storage_key)

    # -- Ichki validatsiya / yordamchilar -----------------------------------

    @staticmethod
    def _validate_title(value: Any) -> str:
        """Nom 1–200 belgi va bo'sh joydan iborat emasligini tekshiradi (R11.2)."""
        if value is None or not isinstance(value, str):
            raise _validation_error("Portfolio nomi matn bo'lishi kerak", "title")
        if not value.strip():
            raise _validation_error("Portfolio nomi bo'sh bo'lishi mumkin emas", "title")
        if len(value) < MIN_TITLE_LENGTH or len(value) > MAX_TITLE_LENGTH:
            raise _validation_error(
                f"Portfolio nomi {MIN_TITLE_LENGTH}–{MAX_TITLE_LENGTH} belgi bo'lishi kerak",
                "title",
            )
        return value

    @staticmethod
    def _extension_of(filename: str | None) -> str:
        """Fayl nomidan kengaytmani (nuqtasiz, kichik harf) qaytaradi."""
        if not filename:
            return ""
        return Path(filename).suffix.lower().lstrip(".")

    def _validate_type(
        self, filename: str | None, file_bytes: bytes, content_type: str | None
    ) -> _FileType:
        """Fayl turini kengaytma va magic-bytes/MIME bo'yicha tekshiradi (R11.3, R17.4).

        Returns:
            Aniqlangan `_FileType`.

        Raises:
            ValidationError: kengaytma ruxsat etilmagan, magic-bytes mos kelmasa
                yoki MIME tur aniq ziddiyatli bo'lsa.
        """
        ext = self._extension_of(filename)
        file_type = _EXTENSION_INDEX.get(ext)
        if file_type is None:
            raise _validation_error(
                "Fayl turi qo'llab-quvvatlanmaydi (ruxsat etilgan: PDF, JPG, PNG, DOC, DOCX)",
                "file",
            )

        # Magic-bytes: mazmun e'lon qilingan kengaytmaga mos kelishi shart.
        if not any(file_bytes.startswith(prefix) for prefix in file_type.magic_prefixes):
            raise _validation_error(
                "Fayl mazmuni e'lon qilingan turga mos kelmaydi",
                "file",
            )

        # MIME turi: berilgan va generik bo'lmasa, mos kelishi shart (where feasible).
        if content_type is not None:
            normalized = content_type.split(";", 1)[0].strip().lower()
            if normalized not in _GENERIC_CONTENT_TYPES and normalized not in file_type.content_types:
                raise _validation_error(
                    "Fayl MIME turi qo'llab-quvvatlanmaydi yoki kengaytmaga mos kelmaydi",
                    "file",
                )

        return file_type

    @staticmethod
    def _generate_storage_key(filename: str | None) -> str:
        """Provayderdan mustaqil noyob `storage_key` yaratadi (kengaytma saqlanadi)."""
        suffix = ""
        if filename:
            suffix = Path(filename).suffix.lower()
        return f"{uuid4().hex}{suffix}"


__all__ = [
    "PortfolioService",
    "PortfolioItem",
    "PermissionDeniedError",
    "ALLOWED_EXTENSIONS",
    "MAX_UPLOAD_SIZE_BYTES",
    "MIN_TITLE_LENGTH",
    "MAX_TITLE_LENGTH",
]
