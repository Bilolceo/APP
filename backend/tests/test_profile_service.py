"""ProfileService uchun unit testlar (task 10.1).

`app/services/profile_service.py` — Profil_Moduli servisining biznes mantig'ini
in-memory SQLite engine ustida (mock'siz, real `UserRepository` bilan) tekshiradi.

Bog'liq talablar:
- R5.1: to'liq profil maydonlarini qaytarish.
- R5.2: tahrirlanadigan maydonlarni yaroqli qiymatlar bilan yangilash.
- R5.3: ish staji 0–60 butun son va matn ≤200 belgi validatsiyasi; yaroqsiz
  qiymatda saqlamaslik va qaysi maydon yaroqsizligini bildirish.
- R5.4: telefon raqamini (hisob identifikatori) o'zgartirishni rad etish.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (modellarni metadata'ga ro'yxatdan o'tkazadi)
from app.core.db import create_db_engine
from app.models.base import Base
from app.models.user import User
from app.repositories.reference import RoleRepository
from app.repositories.users import UserRepository
from app.services.profile_service import (
    MAX_EXPERIENCE_YEARS,
    MAX_TEXT_LENGTH,
    NotFoundError,
    ProfileService,
    ValidationError,
)


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
def user(session: Session) -> User:
    """Boshlang'ich profilga ega namunaviy foydalanuvchi yaratadi."""
    role = RoleRepository(session).create(name="Rahbar")
    u = User(
        full_name="Ali Valiyev",
        phone="+998901112233",
        password_hash="hashed",
        role_id=role.id,
        position="Direktor",
        experience_years=10,
        education_level="Oliy",
        org_type="davlat",
    )
    session.add(u)
    session.commit()
    return u


@pytest.fixture()
def service(session: Session) -> ProfileService:
    """Sessiya orqali qurilgan ProfileService."""
    return ProfileService(session)


# ---------------------------------------------------------------------------
# get_profile (R5.1)
# ---------------------------------------------------------------------------


def test_get_profile_returns_full_fields(service: ProfileService, user: User) -> None:
    """get_profile to'liq profil maydonlarini qaytaradi (R5.1)."""
    profile = service.get_profile(user.id)

    assert profile.id == user.id
    assert profile.full_name == "Ali Valiyev"
    assert profile.phone == "+998901112233"
    assert profile.position == "Direktor"
    assert profile.experience_years == 10
    assert profile.education_level == "Oliy"
    assert profile.org_type == "davlat"
    # Mavjud bo'lmagan ixtiyoriy maydonlar None.
    assert profile.qualification_courses is None
    assert profile.certificates is None
    assert profile.region_id is None
    assert profile.organization_id is None
    assert profile.notifications_enabled is True


def test_get_profile_missing_user_raises_not_found(service: ProfileService) -> None:
    """Mavjud bo'lmagan foydalanuvchi uchun NotFoundError (R5.1)."""
    with pytest.raises(NotFoundError):
        service.get_profile(999999)


def test_service_accepts_repository_directly(session: Session, user: User) -> None:
    """ProfileService tayyor UserRepository bilan ham ishlaydi (framework-agnostik)."""
    svc = ProfileService(UserRepository(session))
    assert svc.get_profile(user.id).full_name == "Ali Valiyev"


# ---------------------------------------------------------------------------
# update_profile — muvaffaqiyatli yangilash (R5.2)
# ---------------------------------------------------------------------------


def test_update_profile_updates_editable_fields(
    service: ProfileService, session: Session, user: User
) -> None:
    """Tahrirlanadigan maydonlar yangilanadi va round-trip o'qiladi (R5.2)."""
    updated = service.update_profile(
        user.id,
        {
            "full_name": "Vali Aliyev",
            "position": "Bosh metodist",
            "experience_years": 25,
            "education_level": "Magistr",
            "qualification_courses": "Kurs A; Kurs B",
            "certificates": "Sertifikat 1",
            "org_type": "xususiy",
            "notifications_enabled": False,
        },
    )
    session.commit()

    assert updated.full_name == "Vali Aliyev"
    assert updated.position == "Bosh metodist"
    assert updated.experience_years == 25

    # Round-trip: qayta o'qishda ham yangilangan qiymatlar.
    reread = service.get_profile(user.id)
    assert reread.full_name == "Vali Aliyev"
    assert reread.qualification_courses == "Kurs A; Kurs B"
    assert reread.certificates == "Sertifikat 1"
    assert reread.org_type == "xususiy"
    assert reread.notifications_enabled is False


def test_update_profile_updates_notifications_enabled_flag(
    service: ProfileService, session: Session, user: User
) -> None:
    """notifications_enabled true/false ga almashtiriladi (R16.5)."""
    updated = service.update_profile(user.id, {"notifications_enabled": False})
    session.commit()
    assert updated.notifications_enabled is False
    assert service.get_profile(user.id).notifications_enabled is False

    updated = service.update_profile(user.id, {"notifications_enabled": True})
    session.commit()
    assert updated.notifications_enabled is True
    assert service.get_profile(user.id).notifications_enabled is True


def test_update_profile_boundary_experience_values(
    service: ProfileService, session: Session, user: User
) -> None:
    """Ish staji chegara qiymatlari (0 va 60) qabul qilinadi (R5.3)."""
    service.update_profile(user.id, {"experience_years": 0})
    session.commit()
    assert service.get_profile(user.id).experience_years == 0

    service.update_profile(user.id, {"experience_years": MAX_EXPERIENCE_YEARS})
    session.commit()
    assert service.get_profile(user.id).experience_years == MAX_EXPERIENCE_YEARS


def test_update_profile_max_length_text_accepted(
    service: ProfileService, session: Session, user: User
) -> None:
    """Aynan 200 belgili matn qabul qilinadi (R5.3 chegarasi)."""
    text = "x" * MAX_TEXT_LENGTH
    service.update_profile(user.id, {"certificates": text})
    session.commit()
    assert service.get_profile(user.id).certificates == text


def test_update_profile_empty_patch_is_noop(
    service: ProfileService, session: Session, user: User
) -> None:
    """Bo'sh patch holatni o'zgartirmaydi va joriy profilni qaytaradi."""
    profile = service.update_profile(user.id, {})
    session.commit()
    assert profile.full_name == "Ali Valiyev"
    assert profile.experience_years == 10


# ---------------------------------------------------------------------------
# update_profile — telefon o'zgartirishni rad etish (R5.4)
# ---------------------------------------------------------------------------


def test_update_profile_rejects_phone_change(
    service: ProfileService, session: Session, user: User
) -> None:
    """Telefon raqamini o'zgartirish rad etiladi va ma'lumot o'zgarmaydi (R5.4)."""
    with pytest.raises(ValidationError) as exc:
        service.update_profile(user.id, {"phone": "+998900000000"})
    assert getattr(exc.value, "field", None) == "phone"

    # Holat o'zgarmagan.
    session.rollback()
    assert service.get_profile(user.id).phone == "+998901112233"


def test_update_profile_phone_change_does_not_persist_other_fields(
    service: ProfileService, session: Session, user: User
) -> None:
    """Telefon o'zgartirish patch'i ichidagi boshqa maydonlar ham saqlanmaydi (R5.4, R20.6)."""
    with pytest.raises(ValidationError):
        service.update_profile(
            user.id, {"position": "Yangi lavozim", "phone": "+998900000000"}
        )
    session.rollback()
    # Validatsiya muvaffaqiyatsiz -> hech narsa saqlanmaydi.
    assert service.get_profile(user.id).position == "Direktor"


# ---------------------------------------------------------------------------
# update_profile — yaroqsiz qiymatlar (R5.3): saqlamaslik + qaysi maydon
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [-1, 61, 100, 3.5, "10", True],
)
def test_update_profile_invalid_experience_rejected(
    service: ProfileService, session: Session, user: User, value: object
) -> None:
    """Yaroqsiz ish staji rad etiladi; maydon nomi bildiriladi (R5.3)."""
    with pytest.raises(ValidationError) as exc:
        service.update_profile(user.id, {"experience_years": value})
    assert getattr(exc.value, "field", None) == "experience_years"

    session.rollback()
    # Mavjud qiymat o'zgarmagan.
    assert service.get_profile(user.id).experience_years == 10


def test_update_profile_text_too_long_rejected(
    service: ProfileService, session: Session, user: User
) -> None:
    """200 belgidan uzun matn rad etiladi; maydon nomi bildiriladi (R5.3)."""
    too_long = "y" * (MAX_TEXT_LENGTH + 1)
    with pytest.raises(ValidationError) as exc:
        service.update_profile(user.id, {"position": too_long})
    assert getattr(exc.value, "field", None) == "position"

    session.rollback()
    assert service.get_profile(user.id).position == "Direktor"


def test_update_profile_blank_full_name_rejected(
    service: ProfileService, session: Session, user: User
) -> None:
    """Bo'sh/whitespace to'liq ism rad etiladi (R5.2 yaroqli qiymat)."""
    with pytest.raises(ValidationError) as exc:
        service.update_profile(user.id, {"full_name": "   "})
    assert getattr(exc.value, "field", None) == "full_name"

    session.rollback()
    assert service.get_profile(user.id).full_name == "Ali Valiyev"


def test_update_profile_unknown_field_rejected(
    service: ProfileService, session: Session, user: User
) -> None:
    """Tahrirlab bo'lmaydigan/noma'lum maydon rad etiladi (R5.2)."""
    with pytest.raises(ValidationError) as exc:
        service.update_profile(user.id, {"role_id": 2})
    assert getattr(exc.value, "field", None) == "role_id"


def test_update_profile_missing_user_raises_not_found(service: ProfileService) -> None:
    """Mavjud bo'lmagan foydalanuvchini yangilashda NotFoundError (R5.1)."""
    with pytest.raises(NotFoundError):
        service.update_profile(424242, {"position": "X"})


@pytest.mark.parametrize("value", [1, 0, "true", "false", None, []])
def test_update_profile_invalid_notifications_enabled_rejected(
    service: ProfileService, session: Session, user: User, value: object
) -> None:
    """notifications_enabled faqat bool qabul qiladi."""
    with pytest.raises(ValidationError) as exc:
        service.update_profile(user.id, {"notifications_enabled": value})
    assert getattr(exc.value, "field", None) == "notifications_enabled"

    session.rollback()
    assert service.get_profile(user.id).notifications_enabled is True
