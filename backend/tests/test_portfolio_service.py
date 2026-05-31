"""LocalFileStorage va PortfolioService uchun unit testlar (task 13.1).

`app/storage/local.py` va `app/services/portfolio_service.py` ni in-memory
SQLite engine (real `PortfolioRepository`) hamda vaqtinchalik katalog ustidagi
`LocalFileStorage` bilan, mock'siz tekshiradi.

Bog'liq talablar:
- R11.1: portfolio ro'yxati sana bo'yicha kamayuvchi tartibda; bo'sh ro'yxat.
- R11.2: yaroqli fayl saqlanadi va yozuv yaratiladi (nom 1–200, tur, hajm).
- R11.3: yaroqsiz fayl turi rad etiladi, hech narsa saqlanmaydi.
- R11.4: 10 485 760 baytdan katta fayl rad etiladi, hech narsa saqlanmaydi.
- R11.5: o'z yozuvini o'chirish — DB qatorlari va fizik fayl o'chiriladi.
- R11.6: begona yozuvni o'chirish 403 (PermissionDeniedError); holat o'zgarmaydi.
- R11.7: mavjud bo'lmagan yozuvni o'chirish 404 (NotFoundError).
- R17.4: kengaytma + magic-bytes/MIME bo'yicha tur tekshiruvi.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (modellarni metadata'ga ro'yxatdan o'tkazadi)
from app.core.db import create_db_engine
from app.models.base import Base
from app.models.portfolio import File, Portfolio
from app.models.user import User
from app.repositories.portfolio import PortfolioRepository
from app.repositories.reference import RoleRepository
from app.services.errors import NotFoundError, ValidationError
from app.services.portfolio_service import (
    MAX_UPLOAD_SIZE_BYTES,
    MAX_TITLE_LENGTH,
    PermissionDeniedError,
    PortfolioService,
)
from app.storage.local import LocalFileStorage

# Minimal yaroqli fayl mazmunlari (magic-bytes bilan).
PDF_BYTES = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 16
DOCX_BYTES = b"PK\x03\x04" + b"\x00" * 32
DOC_BYTES = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 32


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine():
    """Sxema yaratilgan in-memory SQLite engine."""
    eng = create_db_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        Base.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture()
def session(engine):
    """Test uchun bitta sessiya."""
    with Session(engine) as sess:
        yield sess


@pytest.fixture()
def storage(tmp_path: Path) -> LocalFileStorage:
    """Vaqtinchalik katalogdagi LocalFileStorage."""
    return LocalFileStorage(tmp_path / "uploads")


@pytest.fixture()
def user(session: Session) -> User:
    """Namunaviy foydalanuvchi."""
    role = RoleRepository(session).create(name="Rahbar")
    u = User(
        full_name="Ali Valiyev",
        phone="+998901112233",
        password_hash="hashed",
        role_id=role.id,
    )
    session.add(u)
    session.commit()
    return u


@pytest.fixture()
def other_user(session: Session, user: User) -> User:
    """Ikkinchi foydalanuvchi (egalik testlari uchun)."""
    u = User(
        full_name="Vali Aliyev",
        phone="+998901112244",
        password_hash="hashed",
        role_id=user.role_id,
    )
    session.add(u)
    session.commit()
    return u


@pytest.fixture()
def service(session: Session, storage: LocalFileStorage) -> PortfolioService:
    """Sessiya va LocalFileStorage orqali qurilgan PortfolioService."""
    return PortfolioService(session, storage)


# ===========================================================================
# LocalFileStorage
# ===========================================================================


def test_local_storage_save_get_delete_round_trip(storage: LocalFileStorage) -> None:
    """save -> get -> delete to'liq round-trip ishlaydi (R11.2, R11.5)."""
    key = storage.generate_key("hujjat.pdf")
    stored = storage.save(key, PDF_BYTES, content_type="application/pdf")

    assert stored.storage_key == key
    assert stored.size_bytes == len(PDF_BYTES)
    assert stored.content_type == "application/pdf"
    assert stored.url.startswith("file://")

    # get original baytlarni qaytaradi.
    assert storage.get(key) == PDF_BYTES

    # delete dan keyin fayl yo'q (va idempotent).
    storage.delete(key)
    with pytest.raises(FileNotFoundError):
        storage.get(key)
    storage.delete(key)  # ikkinchi o'chirish xato chiqarmaydi


def test_local_storage_generate_key_unique_and_preserves_extension(
    storage: LocalFileStorage,
) -> None:
    """generate_key noyob kalit beradi va kengaytmani saqlaydi."""
    k1 = storage.generate_key("a.PDF")
    k2 = storage.generate_key("a.PDF")
    assert k1 != k2
    assert k1.endswith(".pdf")  # kichik harfga keltiriladi


def test_local_storage_rejects_path_traversal(storage: LocalFileStorage) -> None:
    """Katalogdan tashqariga chiqishga urinish rad etiladi (R17.4)."""
    with pytest.raises(ValueError):
        storage.save("../evil.pdf", PDF_BYTES)


# ===========================================================================
# PortfolioService.list_portfolio (R11.1)
# ===========================================================================


def test_list_portfolio_empty(service: PortfolioService, user: User) -> None:
    """Yozuv bo'lmasa bo'sh ro'yxat (R11.1)."""
    assert service.list_portfolio(user.id) == []


def test_list_portfolio_orders_by_created_desc(
    service: PortfolioService, session: Session, user: User
) -> None:
    """Ro'yxat yaratilgan sana bo'yicha kamayuvchi tartibda (R11.1)."""
    first = service.upload(user.id, "a.pdf", PDF_BYTES, content_type="application/pdf")
    second = service.upload(user.id, "b.png", PNG_BYTES, content_type="image/png")
    session.commit()

    listed = service.list_portfolio(user.id)
    ids = [item.id for item in listed]
    # Repository created_at desc, keyin id desc bo'yicha tartiblaydi.
    assert ids == [second.id, first.id]


# ===========================================================================
# PortfolioService.upload — muvaffaqiyatli (R11.2)
# ===========================================================================


@pytest.mark.parametrize(
    ("filename", "data", "content_type", "expected_type"),
    [
        ("hujjat.pdf", PDF_BYTES, "application/pdf", "pdf"),
        ("rasm.png", PNG_BYTES, "image/png", "png"),
        ("rasm.jpg", JPG_BYTES, "image/jpeg", "jpg"),
        (
            "hujjat.docx",
            DOCX_BYTES,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "docx",
        ),
        ("hujjat.doc", DOC_BYTES, "application/msword", "doc"),
    ],
)
def test_upload_accepts_allowed_types(
    service: PortfolioService,
    storage: LocalFileStorage,
    session: Session,
    user: User,
    filename: str,
    data: bytes,
    content_type: str,
    expected_type: str,
) -> None:
    """Ruxsat etilgan turlar saqlanadi va yozuv yaratiladi (R11.2)."""
    item = service.upload(user.id, filename, data, content_type=content_type)
    session.commit()

    assert item.file_type == expected_type
    assert item.size_bytes == len(data)
    assert item.title == filename
    # Fizik fayl mavjud.
    assert storage.get(item.storage_key) == data
    # DB yozuvi mavjud.
    assert len(service.list_portfolio(user.id)) == 1


def test_upload_uses_explicit_title(
    service: PortfolioService, session: Session, user: User
) -> None:
    """Berilgan title ishlatiladi (R11.2)."""
    item = service.upload(
        user.id, "a.pdf", PDF_BYTES, content_type="application/pdf", title="Sertifikat"
    )
    session.commit()
    assert item.title == "Sertifikat"


def test_upload_accepts_max_size_boundary(
    service: PortfolioService, session: Session, user: User
) -> None:
    """Aynan 10 485 760 baytli fayl qabul qilinadi (R11.4 chegarasi)."""
    pad = MAX_UPLOAD_SIZE_BYTES - len(b"\x89PNG\r\n\x1a\n")
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * pad
    assert len(data) == MAX_UPLOAD_SIZE_BYTES
    item = service.upload(user.id, "big.png", data, content_type="image/png")
    session.commit()
    assert item.size_bytes == MAX_UPLOAD_SIZE_BYTES


def test_upload_accepts_max_length_title(
    service: PortfolioService, session: Session, user: User
) -> None:
    """Aynan 200 belgili nom qabul qilinadi (R11.2 chegarasi)."""
    title = "x" * MAX_TITLE_LENGTH
    item = service.upload(
        user.id, "a.pdf", PDF_BYTES, content_type="application/pdf", title=title
    )
    session.commit()
    assert item.title == title


# ===========================================================================
# PortfolioService.upload — yaroqsiz tur (R11.3) / hajm (R11.4) / nom (R11.2)
# ===========================================================================


def test_upload_rejects_unsupported_extension(
    service: PortfolioService, session: Session, user: User
) -> None:
    """Ruxsat etilmagan kengaytma rad etiladi; hech narsa saqlanmaydi (R11.3)."""
    with pytest.raises(ValidationError) as exc:
        service.upload(user.id, "skript.exe", b"MZ\x90\x00", content_type=None)
    assert getattr(exc.value, "field", None) == "file"
    session.rollback()
    assert service.list_portfolio(user.id) == []


def test_upload_rejects_magic_byte_mismatch(
    service: PortfolioService, session: Session, user: User
) -> None:
    """Kengaytma PDF, lekin mazmun mos emas -> rad etiladi (R11.3, R17.4)."""
    with pytest.raises(ValidationError):
        service.upload(user.id, "fake.pdf", b"not a pdf at all", content_type="application/pdf")
    session.rollback()
    assert service.list_portfolio(user.id) == []


def test_upload_rejects_mismatched_content_type(
    service: PortfolioService, session: Session, user: User
) -> None:
    """MIME tur kengaytmaga zid bo'lsa rad etiladi (R17.4)."""
    with pytest.raises(ValidationError):
        service.upload(user.id, "a.pdf", PDF_BYTES, content_type="image/png")
    session.rollback()
    assert service.list_portfolio(user.id) == []


def test_upload_rejects_oversize_file(
    service: PortfolioService, storage: LocalFileStorage, session: Session, user: User
) -> None:
    """10 485 760 baytdan katta fayl rad etiladi; hech narsa saqlanmaydi (R11.4)."""
    pad = MAX_UPLOAD_SIZE_BYTES - len(b"\x89PNG\r\n\x1a\n") + 1
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * pad
    assert len(data) == MAX_UPLOAD_SIZE_BYTES + 1
    with pytest.raises(ValidationError) as exc:
        service.upload(user.id, "big.png", data, content_type="image/png")
    assert getattr(exc.value, "field", None) == "file"
    session.rollback()
    assert service.list_portfolio(user.id) == []


@pytest.mark.parametrize("title", ["", "   ", "y" * (MAX_TITLE_LENGTH + 1)])
def test_upload_rejects_invalid_title(
    service: PortfolioService, session: Session, user: User, title: str
) -> None:
    """Bo'sh/whitespace yoki 200 belgidan uzun nom rad etiladi (R11.2)."""
    with pytest.raises(ValidationError) as exc:
        service.upload(user.id, "a.pdf", PDF_BYTES, content_type="application/pdf", title=title)
    assert getattr(exc.value, "field", None) == "title"
    session.rollback()
    assert service.list_portfolio(user.id) == []


# ===========================================================================
# PortfolioService.delete (R11.5, R11.6, R11.7)
# ===========================================================================


def test_delete_removes_record_and_file(
    service: PortfolioService, storage: LocalFileStorage, session: Session, user: User
) -> None:
    """O'z yozuvini o'chirish DB qatorlari va fizik faylni olib tashlaydi (R11.5)."""
    item = service.upload(user.id, "a.pdf", PDF_BYTES, content_type="application/pdf")
    session.commit()
    key = item.storage_key
    assert storage.get(key) == PDF_BYTES

    service.delete(user.id, item.id)
    session.commit()

    # DB yozuvlari yo'q (portfolio + fayl).
    assert service.list_portfolio(user.id) == []
    assert session.get(Portfolio, item.id) is None
    file_id = session.query(File).count()
    assert file_id == 0
    # Fizik fayl o'chirildi.
    with pytest.raises(FileNotFoundError):
        storage.get(key)


def test_delete_others_record_is_forbidden(
    service: PortfolioService,
    storage: LocalFileStorage,
    session: Session,
    user: User,
    other_user: User,
) -> None:
    """Begona yozuvni o'chirishga urinish 403 va holat o'zgarmaydi (R11.6)."""
    item = service.upload(user.id, "a.pdf", PDF_BYTES, content_type="application/pdf")
    session.commit()
    key = item.storage_key

    with pytest.raises(PermissionDeniedError):
        service.delete(other_user.id, item.id)
    session.rollback()

    # Yozuv va fayl saqlanib qoladi.
    assert session.get(Portfolio, item.id) is not None
    assert storage.get(key) == PDF_BYTES


def test_delete_missing_record_raises_not_found(
    service: PortfolioService, user: User
) -> None:
    """Mavjud bo'lmagan yozuvni o'chirish 404 (R11.7)."""
    with pytest.raises(NotFoundError):
        service.delete(user.id, 999999)


def test_service_accepts_repository_directly(
    session: Session, storage: LocalFileStorage, user: User
) -> None:
    """PortfolioService tayyor PortfolioRepository bilan ham ishlaydi (framework-agnostik)."""
    svc = PortfolioService(PortfolioRepository(session), storage)
    item = svc.upload(user.id, "a.pdf", PDF_BYTES, content_type="application/pdf")
    session.commit()
    assert svc.list_portfolio(user.id)[0].id == item.id
