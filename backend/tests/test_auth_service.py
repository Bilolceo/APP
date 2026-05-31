"""AuthService uchun unit testlar (task 9.3) — in-memory SQLite ustida.

Bu testlar ``app.services.auth_service.AuthService`` ning ro'yxatdan o'tish,
kirish (login), token yangilash, logout va parolni tiklash oqimlarini real
funksiya (mock'siz) bilan, in-memory SQLite engine ustida tekshiradi
(``Base.metadata.create_all``). Vaqt va kod generatori deterministik bo'lishi
uchun in'ektsiya qilinadi.

Bog'liq talablar: R1.1–R1.7, R2.1, R2.2, R2.6, R2.7, R3.1, R3.2, R3.3, R3.4,
R3.6, R3.7.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (modellarni metadata'ga ro'yxatdan o'tkazadi)
from app.core.db import create_db_engine
from app.core.tokens import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)
from app.models.base import Base
from app.repositories import RoleRepository, TokenRepository, UserRepository
from app.services.auth_service import AuthService
from app.services.errors import (
    AuthError,
    ConflictError,
    ValidationError,
)

VALID_PHONE = "+998901234567"
OTHER_PHONE = "+998907654321"
VALID_PASSWORD = "secret123"


# ---------------------------------------------------------------------------
# Fixturalar
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
    """Test uchun bitta sessiya (commit servis ichida bajariladi)."""
    with Session(engine) as sess:
        yield sess


@pytest.fixture()
def seeded_roles(session: Session) -> dict[str, int]:
    """Standart rollarni seed qiladi (R1.7)."""
    repo = RoleRepository(session)
    ids = {}
    for name in ("Rahbar", "Ekspert", "Administrator"):
        ids[name] = repo.create(name=name).id
    session.commit()
    return ids


@pytest.fixture()
def fixed_now():
    """Deterministik joriy vaqt (naive, real soatga yaqin UTC).

    Ikki test-muhit artefakti sababli **naive** va real soatga yaqin vaqt
    ishlatiladi (production'ga ta'sir qilmaydi):

    1. ``decode_token`` JWT ``exp`` ni **real** soatga nisbatan tekshiradi, shu
       sababli chiqarilgan token muddati real kelajakda bo'lishi kerak (uzoq
       o'tmishdagi qat'iy sana token muddatini o'tgan qiladi).
    2. SQLite ``DateTime`` ni timezone'siz (naive) saqlaydi; production
       PostgreSQL ``TIMESTAMPTZ`` esa tz-aware qaytaradi. Naive ``now`` SQLite'dan
       o'qilgan naive qiymatlar bilan izchil solishtiriladi.

    Nisbiy ofsetlar (masalan +16 daqiqa) saqlangani uchun testlar deterministik
    qoladi.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _make_service(session: Session, *, now: datetime, code: str = "123456") -> AuthService:
    return AuthService(
        session,
        now_provider=lambda: now,
        code_generator=lambda: code,
    )


def _valid_payload(**overrides) -> dict:
    payload = {
        "phone": VALID_PHONE,
        "password": VALID_PASSWORD,
        "full_name": "Ali Valiyev",
        "role": "Rahbar",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# register (R1)
# ---------------------------------------------------------------------------


def test_register_creates_user_with_hashed_password(
    session: Session, seeded_roles, fixed_now
) -> None:
    """Yaroqli kirish bilan hisob yaratiladi va parol xeshlanadi (R1.1, R1.4)."""
    service = _make_service(session, now=fixed_now)
    user = service.register(_valid_payload())

    assert user.id is not None
    assert user.phone == VALID_PHONE
    assert user.role_id == seeded_roles["Rahbar"]
    # R1.4 — parol ochiq matnda saqlanmaydi.
    assert user.password_hash != VALID_PASSWORD
    assert UserRepository(session).get_by_phone(VALID_PHONE) is not None


@pytest.mark.parametrize(
    "overrides, field",
    [
        ({"phone": "   "}, "phone"),
        ({"password": ""}, "password"),
        ({"full_name": "  "}, "full_name"),
        ({"role": None}, "role"),
    ],
)
def test_register_rejects_missing_required_fields(
    session: Session, seeded_roles, fixed_now, overrides, field
) -> None:
    """Majburiy maydon yo'q yoki bo'sh bo'lsa rad etiladi (R1.3)."""
    service = _make_service(session, now=fixed_now)
    with pytest.raises(ValidationError) as exc:
        service.register(_valid_payload(**overrides))
    assert exc.value.field == field


def test_register_rejects_bad_phone_format(
    session: Session, seeded_roles, fixed_now
) -> None:
    """Telefon formati noto'g'ri bo'lsa rad etiladi (R1.6)."""
    service = _make_service(session, now=fixed_now)
    with pytest.raises(ValidationError) as exc:
        service.register(_valid_payload(phone="998901234567"))  # +998 yo'q
    assert exc.value.field == "phone"


@pytest.mark.parametrize("password", ["short", "x" * 65])
def test_register_rejects_bad_password_length(
    session: Session, seeded_roles, fixed_now, password
) -> None:
    """Parol uzunligi 8–64 dan tashqari bo'lsa rad etiladi (R1.5)."""
    service = _make_service(session, now=fixed_now)
    with pytest.raises(ValidationError) as exc:
        service.register(_valid_payload(password=password))
    assert exc.value.field == "password"


def test_register_rejects_invalid_role(
    session: Session, seeded_roles, fixed_now
) -> None:
    """Rol whitelistda bo'lmasa rad etiladi (R1.7)."""
    service = _make_service(session, now=fixed_now)
    with pytest.raises(ValidationError) as exc:
        service.register(_valid_payload(role="SuperUser"))
    assert exc.value.field == "role"


def test_register_rejects_duplicate_phone(
    session: Session, seeded_roles, fixed_now
) -> None:
    """Takroriy telefon raqami ConflictError beradi va yangi hisob yaratmaydi (R1.2)."""
    service = _make_service(session, now=fixed_now)
    service.register(_valid_payload())
    with pytest.raises(ConflictError) as exc:
        service.register(_valid_payload(full_name="Boshqa Ism"))
    assert exc.value.field == "phone"


# ---------------------------------------------------------------------------
# login (R2.1, R2.2, R2.7)
# ---------------------------------------------------------------------------


def test_login_success_returns_token_pair(
    session: Session, seeded_roles, fixed_now
) -> None:
    """To'g'ri ma'lumot bilan access+refresh token qaytariladi (R2.1)."""
    service = _make_service(session, now=fixed_now)
    service.register(_valid_payload())

    tokens = service.login(VALID_PHONE, VALID_PASSWORD)
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] == 15 * 60
    assert tokens["access_token"] and tokens["refresh_token"]

    # Refresh token DB'da xeshlangan holda saqlangan (R2.1).
    stored = TokenRepository(session).get_refresh_by_hash(
        hash_token(tokens["refresh_token"])
    )
    assert stored is not None and stored.revoked is False


def test_login_wrong_password_uses_generic_error(
    session: Session, seeded_roles, fixed_now
) -> None:
    """Noto'g'ri parol qaysi maydon xato ekanini oshkor qilmaydi (R2.2)."""
    service = _make_service(session, now=fixed_now)
    service.register(_valid_payload())

    with pytest.raises(AuthError) as exc:
        service.login(VALID_PHONE, "wrong-password")
    msg = str(exc.value)
    assert "parol" not in msg.lower() or "telefon" in msg.lower()
    # Bir xil umumiy xabar mavjud bo'lmagan hisob uchun ham.
    with pytest.raises(AuthError) as exc2:
        service.login(OTHER_PHONE, "any-password")
    assert str(exc2.value) == str(exc.value)


def test_login_locks_account_after_five_failures(
    session: Session, seeded_roles, fixed_now
) -> None:
    """5 marta noto'g'ri urinishdan keyin hisob 15 daqiqaga bloklanadi (R2.7)."""
    service = _make_service(session, now=fixed_now)
    service.register(_valid_payload())

    for _ in range(5):
        with pytest.raises(AuthError):
            service.login(VALID_PHONE, "wrong-password")

    user = UserRepository(session).get_by_phone(VALID_PHONE)
    assert user.failed_login_count == 5
    assert user.locked_until == fixed_now + timedelta(minutes=15)

    # Bloklangan paytda to'g'ri parol ham rad etiladi (R2.7).
    with pytest.raises(AuthError) as exc:
        service.login(VALID_PHONE, VALID_PASSWORD)
    assert exc.value.code == "account_locked"


def test_login_success_resets_failed_count(
    session: Session, seeded_roles, fixed_now
) -> None:
    """Muvaffaqiyatli kirish bloklash hisoblagichini nolga tushiradi (R2.7)."""
    service = _make_service(session, now=fixed_now)
    service.register(_valid_payload())

    for _ in range(3):
        with pytest.raises(AuthError):
            service.login(VALID_PHONE, "wrong-password")

    service.login(VALID_PHONE, VALID_PASSWORD)
    user = UserRepository(session).get_by_phone(VALID_PHONE)
    assert user.failed_login_count == 0
    assert user.locked_until is None


def test_login_unlocks_after_lockout_window(
    session: Session, seeded_roles, fixed_now
) -> None:
    """Bloklash muddati tugagach kirish yana ishlaydi (R2.7)."""
    service = _make_service(session, now=fixed_now)
    service.register(_valid_payload())
    for _ in range(5):
        with pytest.raises(AuthError):
            service.login(VALID_PHONE, "wrong-password")

    # 16 daqiqadan keyin bloklash tugaydi.
    later = fixed_now + timedelta(minutes=16)
    later_service = _make_service(session, now=later)
    tokens = later_service.login(VALID_PHONE, VALID_PASSWORD)
    assert tokens["access_token"]


# ---------------------------------------------------------------------------
# refresh (R2.3, R2.6)
# ---------------------------------------------------------------------------


def test_refresh_returns_new_access_token(
    session: Session, seeded_roles, fixed_now
) -> None:
    """Yaroqli refresh token yangi access token beradi (R2.3)."""
    service = _make_service(session, now=fixed_now)
    service.register(_valid_payload())
    tokens = service.login(VALID_PHONE, VALID_PASSWORD)

    result = service.refresh(tokens["refresh_token"])
    assert result["token_type"] == "bearer"
    assert result["expires_in"] == 15 * 60
    claims = decode_token(result["access_token"])
    assert claims["type"] == "access"


def test_refresh_rejects_revoked_token(
    session: Session, seeded_roles, fixed_now
) -> None:
    """Bekor qilingan refresh token rad etiladi (R2.6)."""
    service = _make_service(session, now=fixed_now)
    service.register(_valid_payload())
    tokens = service.login(VALID_PHONE, VALID_PASSWORD)

    service.logout(tokens["access_token"], tokens["refresh_token"])
    with pytest.raises(AuthError) as exc:
        service.refresh(tokens["refresh_token"])
    assert exc.value.code == "invalid_refresh_token"


def test_refresh_rejects_garbage_and_wrong_type(
    session: Session, seeded_roles, fixed_now
) -> None:
    """Buzilgan yoki noto'g'ri turdagi token rad etiladi (R2.6)."""
    service = _make_service(session, now=fixed_now)
    with pytest.raises(AuthError):
        service.refresh("not-a-jwt")

    # Access token refresh sifatida ishlatilsa ham rad etiladi.
    access = create_access_token(user_id=1, role="Rahbar", now=fixed_now)
    with pytest.raises(AuthError):
        service.refresh(access.token)


# ---------------------------------------------------------------------------
# logout (R2.4)
# ---------------------------------------------------------------------------


def test_logout_blacklists_access_and_revokes_refresh(
    session: Session, seeded_roles, fixed_now
) -> None:
    """Logout access jti'sini blacklistga qo'shadi va refreshni bekor qiladi (R2.4)."""
    service = _make_service(session, now=fixed_now)
    service.register(_valid_payload())
    tokens = service.login(VALID_PHONE, VALID_PASSWORD)

    service.logout(tokens["access_token"], tokens["refresh_token"])

    repo = TokenRepository(session)
    access_claims = decode_token(tokens["access_token"])
    assert repo.is_jti_blacklisted(access_claims["jti"]) is True
    stored = repo.get_refresh_by_hash(hash_token(tokens["refresh_token"]))
    assert stored.revoked is True


def test_logout_is_resilient_to_bad_access_token(
    session: Session, seeded_roles, fixed_now
) -> None:
    """Yaroqsiz access token bo'lsa ham refresh token bekor qilinadi (R2.4)."""
    service = _make_service(session, now=fixed_now)
    service.register(_valid_payload())
    tokens = service.login(VALID_PHONE, VALID_PASSWORD)

    service.logout("garbage-access", tokens["refresh_token"])
    stored = TokenRepository(session).get_refresh_by_hash(
        hash_token(tokens["refresh_token"])
    )
    assert stored.revoked is True


# ---------------------------------------------------------------------------
# request_password_reset (R3.1, R3.2)
# ---------------------------------------------------------------------------


def test_request_password_reset_creates_hashed_code(
    session: Session, seeded_roles, fixed_now
) -> None:
    """Mavjud hisob uchun xeshlangan kod 15 daqiqalik muddat bilan yaratiladi (R3.1)."""
    service = _make_service(session, now=fixed_now, code="654321")
    service.register(_valid_payload())

    resp = service.request_password_reset(VALID_PHONE)
    assert "message" in resp
    # Javobda xom kod oshkor qilinmaydi (R3.2).
    assert "654321" not in resp["message"]

    user = UserRepository(session).get_by_phone(VALID_PHONE)
    active = TokenRepository(session).get_active_reset_code(user.id)
    assert active is not None
    assert active.code_hash == hash_token("654321")
    assert active.expires_at == fixed_now + timedelta(minutes=15)


def test_request_password_reset_generic_for_unknown_phone(
    session: Session, seeded_roles, fixed_now
) -> None:
    """Mavjud bo'lmagan raqam uchun ham bir xil javob; kod yaratilmaydi (R3.2)."""
    service = _make_service(session, now=fixed_now)
    service.register(_valid_payload())

    known = service.request_password_reset(VALID_PHONE)
    unknown = service.request_password_reset(OTHER_PHONE)
    assert known == unknown


# ---------------------------------------------------------------------------
# confirm_password_reset (R3.3–R3.7)
# ---------------------------------------------------------------------------


def test_confirm_password_reset_updates_password(
    session: Session, seeded_roles, fixed_now
) -> None:
    """To'g'ri kod va yangi parol bilan parol yangilanadi va kod bekor qilinadi (R3.3)."""
    service = _make_service(session, now=fixed_now, code="222333")
    service.register(_valid_payload())
    service.request_password_reset(VALID_PHONE)

    resp = service.confirm_password_reset(VALID_PHONE, "222333", "new-password-1")
    assert "message" in resp

    # Eski parol endi ishlamaydi, yangisi ishlaydi (R3.3).
    with pytest.raises(AuthError):
        service.login(VALID_PHONE, VALID_PASSWORD)
    assert service.login(VALID_PHONE, "new-password-1")["access_token"]

    # Kod bir martalik — qayta ishlatilmaydi (R3.3).
    user = UserRepository(session).get_by_phone(VALID_PHONE)
    assert TokenRepository(session).get_active_reset_code(user.id) is None


def test_confirm_password_reset_rejects_short_password(
    session: Session, seeded_roles, fixed_now
) -> None:
    """8 belgidan kam yangi parol rad etiladi (R3.6)."""
    service = _make_service(session, now=fixed_now, code="222333")
    service.register(_valid_payload())
    service.request_password_reset(VALID_PHONE)

    with pytest.raises(ValidationError) as exc:
        service.confirm_password_reset(VALID_PHONE, "222333", "short")
    assert exc.value.field == "new_password"


def test_confirm_password_reset_rejects_wrong_code(
    session: Session, seeded_roles, fixed_now
) -> None:
    """Noto'g'ri kod rad etiladi, parol o'zgarmaydi, urinish hisoblanadi (R3.4, R3.7)."""
    service = _make_service(session, now=fixed_now, code="222333")
    service.register(_valid_payload())
    service.request_password_reset(VALID_PHONE)

    with pytest.raises(ValidationError):
        service.confirm_password_reset(VALID_PHONE, "999999", "new-password-1")

    user = UserRepository(session).get_by_phone(VALID_PHONE)
    active = TokenRepository(session).get_active_reset_code(user.id)
    assert active is not None and active.attempts == 1
    # Eski parol hali ishlaydi (R3.4 — parol o'zgartirilmaydi).
    assert service.login(VALID_PHONE, VALID_PASSWORD)["access_token"]


def test_confirm_password_reset_rejects_expired_code(
    session: Session, seeded_roles, fixed_now
) -> None:
    """Muddati o'tgan kod rad etiladi (R3.4)."""
    service = _make_service(session, now=fixed_now, code="222333")
    service.register(_valid_payload())
    service.request_password_reset(VALID_PHONE)

    # 16 daqiqadan keyin kod muddati o'tadi.
    later = fixed_now + timedelta(minutes=16)
    later_service = _make_service(session, now=later)
    with pytest.raises(ValidationError):
        later_service.confirm_password_reset(VALID_PHONE, "222333", "new-password-1")


def test_confirm_password_reset_invalidates_after_too_many_attempts(
    session: Session, seeded_roles, fixed_now
) -> None:
    """6 noto'g'ri urinishdan keyin kod bekor qilinadi (R3.7)."""
    service = _make_service(session, now=fixed_now, code="222333")
    service.register(_valid_payload())
    service.request_password_reset(VALID_PHONE)

    # 6 marta noto'g'ri kod — attempts > 5 bo'lganda kod bekor qilinadi.
    for _ in range(6):
        with pytest.raises(ValidationError):
            service.confirm_password_reset(VALID_PHONE, "999999", "new-password-1")

    user = UserRepository(session).get_by_phone(VALID_PHONE)
    # Kod bekor qilingan — faol kod yo'q (R3.7).
    assert TokenRepository(session).get_active_reset_code(user.id) is None
    # Endi to'g'ri kod ham ishlamaydi (kod bekor qilingan).
    with pytest.raises(ValidationError):
        service.confirm_password_reset(VALID_PHONE, "222333", "new-password-1")
