"""Vazifa 17.4 integratsion testlari — admin/ekspert/hisobot/reyting/qurilma
routerlari (R12, R13, R14, R15, R16, R20.4).

Testlar bir martalik (throwaway) FastAPI ilovasi ustida ishlaydi:
- 17.4 routerlari (admin/expert/reports/rating/devices) hamda auth router
  (haqiqiy login tokeni olish uchun) ulanadi;
- ``register_exception_handlers`` markazlashtirilgan xato formatini ta'minlaydi
  (R20.6);
- ``get_db`` bog'liqligi in-memory SQLite sessiyasi bilan override qilinadi
  (``Base.metadata.create_all`` + standart rollar/hudud/tashkilot seed qilinadi).

Autentifikatsiya **haqiqiy** token oqimi orqali tekshiriladi (login'dan olingan
access token bilan), shu sababli ``get_current_principal`` override qilinmaydi —
bu routerlar deps + RBAC bilan to'g'ri bog'langanini tasdiqlaydi.

Qoplangan oqimlar:
- Admin CRUD: GET /admin/users, GET /admin/results, POST/PATCH/DELETE
  /admin/tests va admin-guard (non-admin 403).
- Ekspert: POST /expert/reviews (assigned 200 / unassigned 403 / invalid 400),
  GET /expert/leaders.
- Hisobot: /reports/admin, /reports/by-region, /reports/by-organization,
  /reports/dynamics/{leader_id}.
- Reyting: /rating?scope=... (overall/region/.../invalid).
- Qurilma tokeni: POST/DELETE /devices/token.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (modellarni metadata'ga ro'yxatdan o'tkazadi)
from app.api.deps import get_db
from app.api.errors import register_exception_handlers
from app.api.routers import (
    admin_router,
    auth_router,
    devices_router,
    expert_router,
    rating_router,
    reports_router,
)
from app.models.base import Base
from app.models.content import Test
from app.models.result import TestResult
from app.models.session import TestSession
from app.repositories import (
    OrganizationRepository,
    RegionRepository,
    RoleRepository,
)

# Telefon raqamlari (har biri +998, 13 belgi).
ADMIN_PHONE = "+998901112233"
EXPERT_PHONE = "+998902223344"
LEADER_PHONE = "+998903334455"
LEADER2_PHONE = "+998904445566"
PASSWORD = "secret123"


# ---------------------------------------------------------------------------
# Fixturalar — in-memory SQLite + throwaway app
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine():
    """Sxema yaratilgan in-memory SQLite engine (TestClient bo'ylab ulashiladi)."""
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
def seed_reference(engine):
    """Standart rollar, hudud va tashkilotlarni seed qiladi (R1.7).

    Returns:
        ``(region_id, org1_id, org2_id)`` — testlarda foydalanish uchun.
    """
    with Session(engine) as sess:
        roles = RoleRepository(sess)
        for name in ("Rahbar", "Ekspert", "Administrator"):
            roles.create(name=name)
        region = RegionRepository(sess).create(name="Toshkent")
        sess.flush()
        org1 = OrganizationRepository(sess).create(
            name="MTT-1", region_id=region.id, org_type="davlat"
        )
        org2 = OrganizationRepository(sess).create(
            name="MTT-2", region_id=region.id, org_type="xususiy"
        )
        sess.commit()
        return region.id, org1.id, org2.id


@pytest.fixture()
def client(engine, seed_reference) -> Iterator[TestClient]:
    """17.4 + auth routerlari ulangan throwaway ilova mijozi."""
    application = FastAPI()
    register_exception_handlers(application)
    application.include_router(auth_router)
    application.include_router(admin_router)
    application.include_router(expert_router)
    application.include_router(reports_router)
    application.include_router(rating_router)
    application.include_router(devices_router)

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


def _register(client: TestClient, phone: str, role: str, **overrides) -> dict:
    payload = {
        "phone": phone,
        "password": PASSWORD,
        "full_name": f"User {phone[-4:]}",
        "role": role,
        "position": "Direktor",
    }
    payload.update(overrides)
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _token(client: TestClient, phone: str) -> str:
    resp = client.post("/auth/login", json={"phone": phone, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_result(
    engine,
    *,
    user_id: int,
    percentage: str,
    created_at: datetime,
    test_id: int | None = None,
) -> int:
    """Yakunlangan test natijasini (sessiya bilan) bevosita seed qiladi.

    Reyting/hisobot/dinamika endpointlari uchun. Har bir natija o'z sessiyasiga
    ega (``session_id`` UNIQUE). Test berilmasa yangi test yaratiladi.

    Returns:
        Yaratilgan ``TestResult.id``.
    """
    with Session(engine) as sess:
        if test_id is None:
            test = Test(
                title="Reyting testi",
                category="kognitiv",
                duration_minutes=30,
                is_active=True,
            )
            sess.add(test)
            sess.flush()
            test_id = test.id
        session_row = TestSession(
            user_id=user_id,
            test_id=test_id,
            status="completed",
            started_at=created_at,
            completed_at=created_at,
        )
        sess.add(session_row)
        sess.flush()
        result = TestResult(
            user_id=user_id,
            test_id=test_id,
            session_id=session_row.id,
            total_score=Decimal(percentage),
            max_score=Decimal("100.00"),
            percentage=Decimal(percentage),
            level="Yuqori",
            created_at=created_at,
        )
        sess.add(result)
        sess.commit()
        return result.id


_BASE_TIME = datetime(2024, 1, 1, tzinfo=timezone.utc)


# ===========================================================================
# Admin CRUD (R14, R20.4)
# ===========================================================================


def test_admin_list_users_returns_all(client: TestClient) -> None:
    """Administrator barcha foydalanuvchilarni ko'ra oladi (R14.1, R4.3)."""
    _register(client, ADMIN_PHONE, "Administrator")
    _register(client, LEADER_PHONE, "Rahbar")
    token = _token(client, ADMIN_PHONE)

    resp = client.get("/admin/users", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    phones = {u["phone"] for u in body}
    assert ADMIN_PHONE in phones and LEADER_PHONE in phones
    # Rol nomi yoyilgan.
    assert any(u["role"] == "Administrator" for u in body)


def test_admin_endpoints_forbidden_for_non_admin(client: TestClient) -> None:
    """Admin bo'lmagan so'rovchi admin endpointiga 403 oladi (R14.5, R4.5)."""
    _register(client, LEADER_PHONE, "Rahbar")
    token = _token(client, LEADER_PHONE)
    resp = client.get("/admin/users", headers=_auth(token))
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


def test_admin_list_users_requires_auth(client: TestClient) -> None:
    """Tokensiz admin endpointi 401 (R2.5)."""
    resp = client.get("/admin/users")
    assert resp.status_code == 401


def test_admin_create_test_returns_201(client: TestClient) -> None:
    """Administrator yaroqli test yaratadi -> 201 (R14.2)."""
    _register(client, ADMIN_PHONE, "Administrator")
    token = _token(client, ADMIN_PHONE)
    resp = client.post(
        "/admin/tests",
        json={
            "title": "Kognitiv diagnostika",
            "category": "kognitiv",
            "duration_minutes": 30,
        },
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "Kognitiv diagnostika"
    assert body["is_active"] is True
    assert body["id"] >= 1


def test_admin_create_test_invalid_category_returns_400(client: TestClient) -> None:
    """Yaroqsiz toifa servisda 400 (R14.2, R14.6)."""
    _register(client, ADMIN_PHONE, "Administrator")
    token = _token(client, ADMIN_PHONE)
    resp = client.post(
        "/admin/tests",
        json={"title": "X", "category": "boshqa", "duration_minutes": 30},
        headers=_auth(token),
    )
    assert resp.status_code == 400
    assert any(d["field"] == "category" for d in resp.json()["error"]["details"])


def test_admin_create_test_forbidden_for_leader(client: TestClient) -> None:
    """Rahbar test yarata olmaydi -> 403 (R14.5)."""
    _register(client, LEADER_PHONE, "Rahbar")
    token = _token(client, LEADER_PHONE)
    resp = client.post(
        "/admin/tests",
        json={"title": "X", "category": "kognitiv", "duration_minutes": 30},
        headers=_auth(token),
    )
    assert resp.status_code == 403


def test_admin_update_test_patches_fields(client: TestClient) -> None:
    """PATCH /admin/tests/{id} yuborilgan maydonlarni yangilaydi (R14.2)."""
    _register(client, ADMIN_PHONE, "Administrator")
    token = _token(client, ADMIN_PHONE)
    created = client.post(
        "/admin/tests",
        json={"title": "Eski nom", "category": "kognitiv", "duration_minutes": 30},
        headers=_auth(token),
    ).json()
    resp = client.patch(
        f"/admin/tests/{created['id']}",
        json={"title": "Yangi nom", "is_active": False},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Yangi nom"
    assert body["is_active"] is False


def test_admin_update_missing_test_returns_404(client: TestClient) -> None:
    """Mavjud bo'lmagan testni yangilash 404 (R14.7 — topilmadi)."""
    _register(client, ADMIN_PHONE, "Administrator")
    token = _token(client, ADMIN_PHONE)
    resp = client.patch(
        "/admin/tests/999999", json={"title": "X"}, headers=_auth(token)
    )
    assert resp.status_code == 404


def test_admin_delete_test_deactivates(client: TestClient) -> None:
    """DELETE /admin/tests/{id} testni nofaol qiladi -> 204 (R14.4)."""
    _register(client, ADMIN_PHONE, "Administrator")
    token = _token(client, ADMIN_PHONE)
    created = client.post(
        "/admin/tests",
        json={"title": "Test", "category": "kognitiv", "duration_minutes": 30},
        headers=_auth(token),
    ).json()
    resp = client.delete(f"/admin/tests/{created['id']}", headers=_auth(token))
    assert resp.status_code == 204
    # Nofaol bo'lgani uchun PATCH bilan tekshirsak — hali ham mavjud (soft delete).
    patched = client.patch(
        f"/admin/tests/{created['id']}",
        json={"is_active": True},
        headers=_auth(token),
    )
    assert patched.status_code == 200


def test_admin_list_results(client: TestClient, engine) -> None:
    """GET /admin/results barcha natijalarni qaytaradi (R14.1)."""
    _register(client, ADMIN_PHONE, "Administrator")
    leader = _register(client, LEADER_PHONE, "Rahbar")
    _seed_result(engine, user_id=leader["id"], percentage="85.00", created_at=_BASE_TIME)
    token = _token(client, ADMIN_PHONE)

    resp = client.get("/admin/results", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["user_id"] == leader["id"]
    assert body[0]["percentage"] == "85.00"


# ===========================================================================
# Ekspert baholash (R13)
# ===========================================================================


def _review_payload(leader_id: int, **overrides) -> dict:
    payload = {
        "leader_id": leader_id,
        "management_culture": 4,
        "teamwork": 5,
        "pedagogical_process": 3,
        "innovation": 4,
        "documentation": 5,
        "strategic_planning": 4,
    }
    payload.update(overrides)
    return payload


def test_expert_review_assigned_returns_201(client: TestClient, seed_reference) -> None:
    """Biriktirilgan rahbarni baholash -> 201 va o'rtacha baho (R13.1, R13.2)."""
    _region, org1, _org2 = seed_reference
    _register(client, EXPERT_PHONE, "Ekspert", organization_id=org1)
    leader = _register(client, LEADER_PHONE, "Rahbar", organization_id=org1)
    token = _token(client, EXPERT_PHONE)

    resp = client.post(
        "/expert/reviews",
        json=_review_payload(leader["id"]),
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["review_id"] >= 1
    # (4+5+3+4+5+4)/6 = 4.1666... -> 4.17
    assert body["average_score"] == "4.17"


def test_expert_review_unassigned_returns_403(client: TestClient, seed_reference) -> None:
    """Biriktirilmagan rahbarni baholash -> 403 (R13.5)."""
    _region, org1, org2 = seed_reference
    _register(client, EXPERT_PHONE, "Ekspert", organization_id=org1)
    leader = _register(client, LEADER2_PHONE, "Rahbar", organization_id=org2)
    token = _token(client, EXPERT_PHONE)

    resp = client.post(
        "/expert/reviews",
        json=_review_payload(leader["id"]),
        headers=_auth(token),
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


def test_expert_review_invalid_score_returns_400(client: TestClient, seed_reference) -> None:
    """1–5 oralig'idan tashqari baho -> 400 (R13.3)."""
    _region, org1, _org2 = seed_reference
    _register(client, EXPERT_PHONE, "Ekspert", organization_id=org1)
    leader = _register(client, LEADER_PHONE, "Rahbar", organization_id=org1)
    token = _token(client, EXPERT_PHONE)

    resp = client.post(
        "/expert/reviews",
        json=_review_payload(leader["id"], management_culture=6),
        headers=_auth(token),
    )
    assert resp.status_code == 400
    # ExpertReviewService aniqroq kod beradi (``invalid_expert_scores``), ammo u
    # ``ValidationError`` tipi bo'lgani uchun HTTP 400 ga keltiriladi; maydon
    # ``scores`` deb belgilanadi (R13.3, R20.6).
    body = resp.json()["error"]
    assert body["code"] in ("validation_error", "invalid_expert_scores")
    assert any(d["field"] == "scores" for d in body["details"])


def test_expert_reviews_forbidden_for_leader(client: TestClient, seed_reference) -> None:
    """Rahbar ekspert baholash endpointiga 403 oladi (R4.2, R4.5)."""
    _region, org1, _org2 = seed_reference
    leader = _register(client, LEADER_PHONE, "Rahbar", organization_id=org1)
    token = _token(client, LEADER_PHONE)
    resp = client.post(
        "/expert/reviews",
        json=_review_payload(leader["id"]),
        headers=_auth(token),
    )
    assert resp.status_code == 403


def test_expert_leaders_lists_assigned(client: TestClient, seed_reference) -> None:
    """GET /expert/leaders bir tashkilotdagi rahbarlarni qaytaradi (R13.5 — MVP)."""
    _region, org1, org2 = seed_reference
    _register(client, EXPERT_PHONE, "Ekspert", organization_id=org1)
    assigned = _register(client, LEADER_PHONE, "Rahbar", organization_id=org1)
    _register(client, LEADER2_PHONE, "Rahbar", organization_id=org2)
    token = _token(client, EXPERT_PHONE)

    resp = client.get("/expert/leaders", headers=_auth(token))
    assert resp.status_code == 200
    ids = {leader["id"] for leader in resp.json()}
    assert assigned["id"] in ids
    # Boshqa tashkilotdagi rahbar ro'yxatda yo'q.
    assert len(ids) == 1


# ===========================================================================
# Hisobotlar (R15)
# ===========================================================================


def test_reports_admin_returns_counts(client: TestClient, engine, seed_reference) -> None:
    """/reports/admin rahbarlar/topshirganlar soni va o'rtacha ball (R15.1)."""
    _region, org1, _org2 = seed_reference
    _register(client, ADMIN_PHONE, "Administrator")
    leader = _register(client, LEADER_PHONE, "Rahbar", organization_id=org1)
    _seed_result(engine, user_id=leader["id"], percentage="80.00", created_at=_BASE_TIME)
    token = _token(client, ADMIN_PHONE)

    resp = client.get("/reports/admin", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["leaders_count"] == 1
    assert body["test_takers_count"] == 1
    assert body["average_score"] == "80.00"


def test_reports_admin_forbidden_for_leader(client: TestClient) -> None:
    """Rahbar hisobotga kira olmaydi -> 403 (R4.5)."""
    _register(client, LEADER_PHONE, "Rahbar")
    token = _token(client, LEADER_PHONE)
    resp = client.get("/reports/admin", headers=_auth(token))
    assert resp.status_code == 403


def test_reports_by_region_and_organization(
    client: TestClient, engine, seed_reference
) -> None:
    """/reports/by-region va /reports/by-organization kesim qatorlarini beradi (R15.3, R15.4)."""
    region_id, org1, _org2 = seed_reference
    _register(client, ADMIN_PHONE, "Administrator")
    leader = _register(
        client, LEADER_PHONE, "Rahbar", organization_id=org1, region_id=region_id
    )
    _seed_result(engine, user_id=leader["id"], percentage="70.00", created_at=_BASE_TIME)
    token = _token(client, ADMIN_PHONE)

    by_region = client.get("/reports/by-region", headers=_auth(token))
    assert by_region.status_code == 200
    region_rows = by_region.json()["rows"]
    assert any(r["section_id"] == region_id for r in region_rows)

    by_org = client.get("/reports/by-organization", headers=_auth(token))
    assert by_org.status_code == 200
    org_rows = by_org.json()["rows"]
    assert any(r["section_id"] == org1 for r in org_rows)


def test_reports_dynamics_chronological(client: TestClient, engine, seed_reference) -> None:
    """/reports/dynamics/{id} xronologik (o'suvchi) nuqtalarni beradi (R15.5)."""
    _region, org1, _org2 = seed_reference
    _register(client, ADMIN_PHONE, "Administrator")
    leader = _register(client, LEADER_PHONE, "Rahbar", organization_id=org1)
    _seed_result(
        engine, user_id=leader["id"], percentage="60.00", created_at=_BASE_TIME
    )
    _seed_result(
        engine,
        user_id=leader["id"],
        percentage="75.00",
        created_at=_BASE_TIME + timedelta(days=10),
    )
    token = _token(client, ADMIN_PHONE)

    resp = client.get(f"/reports/dynamics/{leader['id']}", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["leader_id"] == leader["id"]
    percentages = [p["percentage"] for p in body["points"]]
    assert percentages == ["60.00", "75.00"]


def test_reports_dynamics_expert_unassigned_forbidden(
    client: TestClient, engine, seed_reference
) -> None:
    """Ekspert biriktirilmagan rahbar dinamikasiga kira olmaydi -> 403 (R4.2, R15.6)."""
    _region, org1, org2 = seed_reference
    _register(client, EXPERT_PHONE, "Ekspert", organization_id=org1)
    leader = _register(client, LEADER2_PHONE, "Rahbar", organization_id=org2)
    _seed_result(engine, user_id=leader["id"], percentage="50.00", created_at=_BASE_TIME)
    token = _token(client, EXPERT_PHONE)

    resp = client.get(f"/reports/dynamics/{leader['id']}", headers=_auth(token))
    assert resp.status_code == 403


# ===========================================================================
# Reyting (R12)
# ===========================================================================


def test_rating_overall_ranks_and_excludes_unranked(
    client: TestClient, engine, seed_reference
) -> None:
    """/rating?scope=overall natijasi bor rahbarlarni reytinglaydi, natijasizni chiqaradi (R12.2, R12.5)."""
    _region, org1, _org2 = seed_reference
    high = _register(client, LEADER_PHONE, "Rahbar", organization_id=org1)
    _no_result = _register(client, LEADER2_PHONE, "Rahbar", organization_id=org1)
    _seed_result(engine, user_id=high["id"], percentage="90.00", created_at=_BASE_TIME)
    token = _token(client, LEADER_PHONE)

    resp = client.get("/rating", params={"scope": "overall"}, headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["scope"] == "overall"
    assert len(body["ranked"]) == 1
    assert body["ranked"][0]["rank"] == 1
    assert body["ranked"][0]["percentage"] == "90.00"
    # So'rovchi (natijasi bor rahbar) o'z yozuvi sifatida belgilangan (R12.4).
    assert body["ranked"][0]["is_requester"] is True
    # Anonimlik: ism/telefon maydonlari yo'q (R12.4).
    assert "full_name" not in body["ranked"][0]
    assert "phone" not in body["ranked"][0]
    # Natijasiz rahbar reytingdan tashqarida (R12.5).
    assert len(body["out_of_ranking"]) == 1


def test_rating_invalid_scope_returns_400(client: TestClient, seed_reference) -> None:
    """Yaroqsiz scope -> 400 (R12.1)."""
    _register(client, LEADER_PHONE, "Rahbar")
    token = _token(client, LEADER_PHONE)
    resp = client.get("/rating", params={"scope": "boshqa"}, headers=_auth(token))
    assert resp.status_code == 400
    assert any(d["field"] == "scope" for d in resp.json()["error"]["details"])


def test_rating_scopes_accepted(client: TestClient, engine, seed_reference) -> None:
    """region/organization/competency kesimlari ham 200 qaytaradi (R12.1)."""
    _region, org1, _org2 = seed_reference
    leader = _register(client, LEADER_PHONE, "Rahbar", organization_id=org1)
    _seed_result(engine, user_id=leader["id"], percentage="55.00", created_at=_BASE_TIME)
    token = _token(client, LEADER_PHONE)
    for scope in ("region", "organization", "competency"):
        resp = client.get("/rating", params={"scope": scope}, headers=_auth(token))
        assert resp.status_code == 200, scope
        assert resp.json()["scope"] == scope


def test_rating_requires_auth(client: TestClient) -> None:
    """Tokensiz /rating 401 (R2.5)."""
    resp = client.get("/rating")
    assert resp.status_code == 401


# ===========================================================================
# Qurilma tokeni (R16)
# ===========================================================================


def test_device_token_register_returns_201(client: TestClient) -> None:
    """POST /devices/token tokenni joriy foydalanuvchiga bog'lab ro'yxatga oladi (R16.1)."""
    me = _register(client, LEADER_PHONE, "Rahbar")
    token = _token(client, LEADER_PHONE)
    resp = client.post(
        "/devices/token",
        json={"token": "fcm-abc-123", "platform": "android"},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user_id"] == me["id"]
    assert body["is_valid"] is True
    assert body["platform"] == "android"


def test_device_token_register_requires_auth(client: TestClient) -> None:
    """Tokensiz qurilma ro'yxati 401 (R2.5)."""
    resp = client.post("/devices/token", json={"token": "x"})
    assert resp.status_code == 401


def test_device_token_invalidate(client: TestClient) -> None:
    """DELETE /devices/token tokenni yaroqsiz qiladi (R16.6)."""
    _register(client, LEADER_PHONE, "Rahbar")
    token = _token(client, LEADER_PHONE)
    client.post(
        "/devices/token",
        json={"token": "fcm-xyz-789", "platform": "android"},
        headers=_auth(token),
    )
    resp = client.request(
        "DELETE",
        "/devices/token",
        json={"token": "fcm-xyz-789"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_device_token_invalidate_unknown_is_ok(client: TestClient) -> None:
    """Mavjud bo'lmagan tokenni bekor qilish ham xato bermaydi (R16.6)."""
    _register(client, LEADER_PHONE, "Rahbar")
    token = _token(client, LEADER_PHONE)
    resp = client.request(
        "DELETE",
        "/devices/token",
        json={"token": "never-registered"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
