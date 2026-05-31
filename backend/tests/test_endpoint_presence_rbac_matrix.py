"""Vazifa 17.6 — endpoint mavjudligi smoke + RBAC matritsa testlari.

Qamrov:
- `create_app()` dagi asosiy `/api/v1/*` prefikslar mavjudligi (route smoke);
- Rahbar/Ekspert/Administrator rollari uchun ruxsat/rad matritsasi:
  - `/users/me` (hamma autentifikatsiyalangan rollarga ruxsat),
  - `/users/{id}` (faqat o'zi yoki admin),
  - `/admin/users` (faqat admin),
  - `/expert/leaders` (ekspert yoki admin),
  - `/reports/admin` (ekspert yoki admin).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (modellarni metadata'ga ro'yxatdan o'tkazadi)
from app.api.deps import get_db
from app.main import create_app
from app.models.base import Base
from app.repositories import RoleRepository

PASSWORD = "secret123"
ADMIN_PHONE = "+998901001001"
EXPERT_PHONE = "+998901001002"
LEADER_A_PHONE = "+998901001003"
LEADER_B_PHONE = "+998901001004"


@pytest.fixture()
def engine():
    """Sxema yaratilgan in-memory SQLite engine."""
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
    """Standart rollar (R1.7) seed qilinadi."""
    with Session(engine) as sess:
        repo = RoleRepository(sess)
        for name in ("Rahbar", "Ekspert", "Administrator"):
            repo.create(name=name)
        sess.commit()


@pytest.fixture()
def client(engine, seed_roles) -> Iterator[TestClient]:
    """To'liq `create_app()` ilovasi, DB override bilan."""
    app = create_app()

    def _override_db() -> Iterator[Session]:
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _register(client: TestClient, *, phone: str, role: str) -> dict:
    payload = {
        "phone": phone,
        "password": PASSWORD,
        "full_name": f"User {phone[-3:]}",
        "role": role,
        "position": "Direktor",
        "experience_years": 5,
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _token(client: TestClient, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        json={"phone": phone, "password": PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_route_presence_smoke_for_all_core_prefixes(client: TestClient) -> None:
    """Asosiy router prefikslari `/api/v1` ostida mavjud bo'lishi kerak."""
    paths = {getattr(route, "path", None) for route in client.app.routes}
    expected_prefixes = (
        "/api/v1/auth",
        "/api/v1/users",
        "/api/v1/tests",
        "/api/v1/questions",
        "/api/v1/recommendations",
        "/api/v1/portfolio",
        "/api/v1/analytics",
        "/api/v1/admin",
        "/api/v1/expert",
        "/api/v1/reports",
        "/api/v1/rating",
        "/api/v1/devices",
    )
    for prefix in expected_prefixes:
        assert any(p is not None and p.startswith(prefix) for p in paths), prefix


@pytest.fixture()
def rbac_context(client: TestClient) -> dict[str, object]:
    """RBAC matritsa tekshiruvi uchun foydalanuvchilar va tokenlar."""
    admin = _register(client, phone=ADMIN_PHONE, role="Administrator")
    expert = _register(client, phone=EXPERT_PHONE, role="Ekspert")
    leader_a = _register(client, phone=LEADER_A_PHONE, role="Rahbar")
    leader_b = _register(client, phone=LEADER_B_PHONE, role="Rahbar")
    return {
        "admin_id": admin["id"],
        "expert_id": expert["id"],
        "leader_a_id": leader_a["id"],
        "leader_b_id": leader_b["id"],
        "admin_token": _token(client, ADMIN_PHONE),
        "expert_token": _token(client, EXPERT_PHONE),
        "leader_b_token": _token(client, LEADER_B_PHONE),
    }


def test_rbac_matrix_me_endpoint(client: TestClient, rbac_context: dict[str, object]) -> None:
    """`/users/me` barcha autentifikatsiyalangan rollarga ochiq (R4.1, R4.2, R4.3)."""
    for token_key in ("admin_token", "expert_token", "leader_b_token"):
        resp = client.get("/api/v1/users/me", headers=_auth(rbac_context[token_key]))  # type: ignore[arg-type]
        assert resp.status_code == 200


def test_rbac_matrix_user_by_id(client: TestClient, rbac_context: dict[str, object]) -> None:
    """`/users/{id}`: admin ruxsat, begona ekspert/rahbar rad (R4.1, R4.3, R4.5)."""
    target = int(rbac_context["leader_a_id"])
    checks = (
        ("admin_token", 200),
        ("expert_token", 403),
        ("leader_b_token", 403),
    )
    for token_key, expected_status in checks:
        resp = client.get(
            f"/api/v1/users/{target}",
            headers=_auth(rbac_context[token_key]),  # type: ignore[arg-type]
        )
        assert resp.status_code == expected_status


def test_rbac_matrix_admin_endpoint(
    client: TestClient, rbac_context: dict[str, object]
) -> None:
    """`/admin/users`: faqat administratorga ruxsat (R14.5, R4.5)."""
    checks = (
        ("admin_token", 200),
        ("expert_token", 403),
        ("leader_b_token", 403),
    )
    for token_key, expected_status in checks:
        resp = client.get(
            "/api/v1/admin/users",
            headers=_auth(rbac_context[token_key]),  # type: ignore[arg-type]
        )
        assert resp.status_code == expected_status


def test_rbac_matrix_expert_endpoint(
    client: TestClient, rbac_context: dict[str, object]
) -> None:
    """`/expert/leaders`: ekspert/admin ruxsat, rahbar rad (R4.2, R4.3, R4.5)."""
    checks = (
        ("admin_token", 200),
        ("expert_token", 200),
        ("leader_b_token", 403),
    )
    for token_key, expected_status in checks:
        resp = client.get(
            "/api/v1/expert/leaders",
            headers=_auth(rbac_context[token_key]),  # type: ignore[arg-type]
        )
        assert resp.status_code == expected_status


def test_rbac_matrix_reports_endpoint(
    client: TestClient, rbac_context: dict[str, object]
) -> None:
    """`/reports/admin`: ekspert/admin ruxsat, rahbar rad (R15.6, R4.5)."""
    checks = (
        ("admin_token", 200),
        ("expert_token", 200),
        ("leader_b_token", 403),
    )
    for token_key, expected_status in checks:
        resp = client.get(
            "/api/v1/reports/admin",
            headers=_auth(rbac_context[token_key]),  # type: ignore[arg-type]
        )
        assert resp.status_code == expected_status
