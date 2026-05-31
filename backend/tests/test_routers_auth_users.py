"""Vazifa 17.1 integratsion testlari — auth va profil routerlari (R1–R5, R4, R20).

Testlar bir martalik (throwaway) FastAPI ilovasi ustida ishlaydi:
- ``auth_router`` va ``users_router`` ulanadi;
- ``register_exception_handlers`` markazlashtirilgan xato formatini ta'minlaydi
  (R20.6);
- ``get_db`` bog'liqligi in-memory SQLite sessiyasi bilan override qilinadi
  (``Base.metadata.create_all`` + standart rollar seed qilinadi).

Qoplangan oqimlar: register / login / refresh / logout / forgot-password /
reset-password hamda profil GET/PATCH va ``/users/{id}`` RBAC.

Autentifikatsiya **haqiqiy** token oqimi orqali tekshiriladi (login'dan olingan
access token bilan), shu sababli ``get_current_principal`` override qilinmaydi —
bu routerlar deps + RBAC bilan to'g'ri bog'langanini tasdiqlaydi.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (modellarni metadata'ga ro'yxatdan o'tkazadi)
from app.api.deps import get_db
from app.api.errors import register_exception_handlers
from app.api.routers import auth_router, users_router
from app.models.base import Base
from app.repositories import RoleRepository

VALID_PHONE = "+998901234567"
OTHER_PHONE = "+998907654321"
ADMIN_PHONE = "+998901112233"
VALID_PASSWORD = "secret123"


# ---------------------------------------------------------------------------
# Fixturalar — in-memory SQLite + throwaway app
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine():
    """Sxema yaratilgan in-memory SQLite engine.

    ``StaticPool`` + ``check_same_thread=False`` — bitta in-memory bazani
    TestClient so'rovlari (boshqa thread'da ham) bo'ylab ulashish uchun.
    """
    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        Base.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture()
def seed_roles(engine) -> None:
    """Standart rollarni seed qiladi (R1.7)."""
    with Session(engine) as sess:
        repo = RoleRepository(sess)
        for name in ("Rahbar", "Ekspert", "Administrator"):
            repo.create(name=name)
        sess.commit()


@pytest.fixture()
def client(engine, seed_roles) -> Iterator[TestClient]:
    """Auth + users routerlari ulangan throwaway ilova mijozi."""
    application = FastAPI()
    register_exception_handlers(application)
    application.include_router(auth_router)
    application.include_router(users_router)

    def _override_db() -> Iterator[Session]:
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    application.dependency_overrides[get_db] = _override_db
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Yordamchilar
# ---------------------------------------------------------------------------


def _register_payload(**overrides) -> dict:
    payload = {
        "phone": VALID_PHONE,
        "password": VALID_PASSWORD,
        "full_name": "Ali Valiyev",
        "role": "Rahbar",
        "position": "Direktor",
        "experience_years": 5,
    }
    payload.update(overrides)
    return payload


def _register(client: TestClient, **overrides):
    return client.post("/auth/register", json=_register_payload(**overrides))


def _login(client: TestClient, phone: str = VALID_PHONE, password: str = VALID_PASSWORD):
    return client.post("/auth/login", json={"phone": phone, "password": password})


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _access_token(client: TestClient, phone: str = VALID_PHONE) -> str:
    return _login(client, phone).json()["access_token"]


# ---------------------------------------------------------------------------
# register (R1)
# ---------------------------------------------------------------------------


def test_register_returns_201_and_profile(client: TestClient) -> None:
    """Yaroqli so'rov 201 va profil qaytaradi; parol oshkor qilinmaydi (R1.1, R20.2)."""
    resp = _register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["phone"] == VALID_PHONE
    assert body["full_name"] == "Ali Valiyev"
    assert body["id"] >= 1
    assert "password" not in body and "password_hash" not in body


def test_register_duplicate_phone_returns_409(client: TestClient) -> None:
    """Takroriy telefon 409 conflict beradi (R1.2)."""
    _register(client)
    resp = _register(client, full_name="Boshqa Ism")
    assert resp.status_code == 409
    # Tana yagona tuzilgan formatda; ``code`` aniq mashina-o'qiy servis kodi.
    assert "code" in resp.json()["error"]


def test_register_invalid_phone_returns_400(client: TestClient) -> None:
    """Telefon formati noto'g'ri bo'lsa 400 (R1.6)."""
    resp = _register(client, phone="998901234567")
    assert resp.status_code == 400
    body = resp.json()["error"]
    assert body["code"] == "validation_error"
    assert any(d["field"] == "phone" for d in body["details"])


def test_register_invalid_role_returns_400(client: TestClient) -> None:
    """Yaroqsiz rol 400 beradi (R1.7)."""
    resp = _register(client, role="SuperUser")
    assert resp.status_code == 400
    assert any(d["field"] == "role" for d in resp.json()["error"]["details"])


def test_register_missing_field_returns_422_or_400(client: TestClient) -> None:
    """Majburiy maydon umuman yo'q bo'lsa so'rov validatsiyasi xatosi (R20.6)."""
    payload = _register_payload()
    del payload["full_name"]
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# login (R2.1, R2.2)
# ---------------------------------------------------------------------------


def test_login_returns_token_pair(client: TestClient) -> None:
    """To'g'ri ma'lumot bilan access+refresh token (R2.1)."""
    _register(client)
    resp = _login(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 15 * 60


def test_login_wrong_password_returns_401_generic(client: TestClient) -> None:
    """Noto'g'ri parol 401; xabar qaysi maydon xato ekanini oshkor qilmaydi (R2.2)."""
    _register(client)
    resp = _login(client, password="wrong-password")
    assert resp.status_code == 401
    # Umumiy xabar: na "parol", na "telefon" maydoni alohida ko'rsatilmaydi (R2.2).
    message = resp.json()["error"]["message"].lower()
    assert "parol" not in message or "telefon" in message


def test_login_unknown_phone_returns_401(client: TestClient) -> None:
    """Mavjud bo'lmagan telefon ham bir xil 401 beradi (R2.2)."""
    _register(client)
    resp = _login(client, phone=OTHER_PHONE)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# refresh (R2.3, R2.6)
# ---------------------------------------------------------------------------


def test_refresh_returns_new_access_token(client: TestClient) -> None:
    """Yaroqli refresh token yangi access token beradi (R2.3)."""
    _register(client)
    tokens = _login(client).json()
    resp = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["expires_in"] == 15 * 60


def test_refresh_rejects_garbage_token(client: TestClient) -> None:
    """Buzilgan refresh token 401 beradi (R2.6)."""
    _register(client)
    resp = client.post("/auth/refresh", json={"refresh_token": "not-a-jwt"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# logout (R2.4)
# ---------------------------------------------------------------------------


def test_logout_revokes_tokens(client: TestClient) -> None:
    """Logout access jti'sini blacklistga qo'shadi va refreshni bekor qiladi (R2.4)."""
    _register(client)
    tokens = _login(client).json()

    resp = client.post(
        "/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=_auth_header(tokens["access_token"]),
    )
    assert resp.status_code == 200
    assert "message" in resp.json()

    # Bekor qilingan refresh token endi yangilanmaydi (R2.4, R2.6).
    refresh_resp = client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_resp.status_code == 401

    # Blacklistdagi access token bilan himoyalangan resurs 401 (R2.4, R2.5).
    me_resp = client.get("/users/me", headers=_auth_header(tokens["access_token"]))
    assert me_resp.status_code == 401


# ---------------------------------------------------------------------------
# forgot-password / reset-password (R3)
# ---------------------------------------------------------------------------


def test_forgot_password_generic_response_for_known_and_unknown(
    client: TestClient,
) -> None:
    """Mavjud va mavjud bo'lmagan telefon uchun bir xil umumiy javob (R3.2)."""
    _register(client)
    known = client.post("/auth/forgot-password", json={"phone": VALID_PHONE})
    unknown = client.post("/auth/forgot-password", json={"phone": OTHER_PHONE})
    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json() == unknown.json()


def test_reset_password_rejects_invalid_code(client: TestClient) -> None:
    """Faol kod bo'lsa ham noto'g'ri kod 400 beradi (R3.4)."""
    _register(client)
    client.post("/auth/forgot-password", json={"phone": VALID_PHONE})
    resp = client.post(
        "/auth/reset-password",
        json={"phone": VALID_PHONE, "code": "000000", "new_password": "new-secret-1"},
    )
    assert resp.status_code == 400
    assert "code" in resp.json()["error"]


def test_reset_password_rejects_short_password(client: TestClient) -> None:
    """8 belgidan kam yangi parol 400 beradi (R3.6)."""
    _register(client)
    client.post("/auth/forgot-password", json={"phone": VALID_PHONE})
    resp = client.post(
        "/auth/reset-password",
        json={"phone": VALID_PHONE, "code": "123456", "new_password": "short"},
    )
    assert resp.status_code == 400
    assert any(
        d["field"] == "new_password" for d in resp.json()["error"]["details"]
    )


# ---------------------------------------------------------------------------
# /users/me — GET / PATCH (R5)
# ---------------------------------------------------------------------------


def test_get_my_profile_requires_auth(client: TestClient) -> None:
    """Tokensiz /users/me 401 (R2.5)."""
    resp = client.get("/users/me")
    assert resp.status_code == 401


def test_get_my_profile_returns_full_profile(client: TestClient) -> None:
    """Joriy profil to'liq maydonlar bilan qaytadi (R5.1)."""
    _register(client)
    token = _access_token(client)
    resp = client.get("/users/me", headers=_auth_header(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["phone"] == VALID_PHONE
    assert body["position"] == "Direktor"
    assert body["experience_years"] == 5
    assert body["notifications_enabled"] is True


def test_patch_my_profile_updates_editable_fields(client: TestClient) -> None:
    """Tahrirlanadigan maydonlar yangilanadi va qaytariladi (R5.2)."""
    _register(client)
    token = _access_token(client)
    resp = client.patch(
        "/users/me",
        json={
            "position": "Bosh direktor",
            "experience_years": 8,
            "notifications_enabled": False,
        },
        headers=_auth_header(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["position"] == "Bosh direktor"
    assert body["experience_years"] == 8
    assert body["notifications_enabled"] is False
    # O'zgartirilmagan maydon o'z holicha qoladi.
    assert body["full_name"] == "Ali Valiyev"


def test_patch_my_profile_rejects_phone_change(client: TestClient) -> None:
    """Telefonni o'zgartirishga urinish 400 beradi (R5.4)."""
    _register(client)
    token = _access_token(client)
    resp = client.patch(
        "/users/me",
        json={"phone": "+998900000000"},
        headers=_auth_header(token),
    )
    assert resp.status_code == 400
    assert any(d["field"] == "phone" for d in resp.json()["error"]["details"])


def test_patch_my_profile_rejects_invalid_experience(client: TestClient) -> None:
    """Ish staji 0–60 dan tashqari bo'lsa 400 (R5.3)."""
    _register(client)
    token = _access_token(client)
    resp = client.patch(
        "/users/me",
        json={"experience_years": 99},
        headers=_auth_header(token),
    )
    assert resp.status_code == 400
    assert any(
        d["field"] == "experience_years" for d in resp.json()["error"]["details"]
    )


# ---------------------------------------------------------------------------
# /users/{id} — RBAC (R4)
# ---------------------------------------------------------------------------


def test_get_user_by_id_self_allowed(client: TestClient) -> None:
    """Foydalanuvchi o'z ID si bo'yicha profilga kira oladi (R4.1)."""
    me = _register(client).json()
    token = _access_token(client)
    resp = client.get(f"/users/{me['id']}", headers=_auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["id"] == me["id"]


def test_get_other_user_forbidden_for_leader(client: TestClient) -> None:
    """Rahbar boshqa foydalanuvchi profiliga kira olmaydi -> 403 (R4.1, R4.5)."""
    me = _register(client).json()
    token = _access_token(client)
    other_id = me["id"] + 999
    resp = client.get(f"/users/{other_id}", headers=_auth_header(token))
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


def test_admin_can_access_other_user_profile(client: TestClient) -> None:
    """Administrator istalgan foydalanuvchi profiliga kira oladi (R4.3)."""
    # Rahbar (target) va administrator (so'rovchi) yaratamiz.
    leader = _register(client).json()
    _register(client, phone=ADMIN_PHONE, role="Administrator", full_name="Admin")
    admin_token = _access_token(client, phone=ADMIN_PHONE)

    resp = client.get(f"/users/{leader['id']}", headers=_auth_header(admin_token))
    assert resp.status_code == 200
    assert resp.json()["id"] == leader["id"]


def test_admin_get_missing_user_returns_404(client: TestClient) -> None:
    """Administrator mavjud bo'lmagan foydalanuvchini so'rasa 404 (NotFoundError)."""
    _register(client, phone=ADMIN_PHONE, role="Administrator", full_name="Admin")
    admin_token = _access_token(client, phone=ADMIN_PHONE)
    resp = client.get("/users/999999", headers=_auth_header(admin_token))
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"
