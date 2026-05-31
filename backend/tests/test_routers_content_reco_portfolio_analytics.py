"""Vazifa 17.3 integratsion testlari — kontent, tavsiya, portfolio, analitika
routerlari (R9, R10, R11, R14, R20.4).

Testlar bir martalik (throwaway) FastAPI ilovasi ustida ishlaydi:
- ``auth_router`` (login token olish uchun), ``questions_router``,
  ``recommendations_router``, ``portfolio_router`` va ``analytics_router``
  ulanadi;
- ``register_exception_handlers`` markazlashtirilgan xato formatini ta'minlaydi
  (R20.6);
- ``get_db`` bog'liqligi in-memory SQLite sessiyasi bilan override qilinadi
  (``Base.metadata.create_all`` + standart rollar seed qilinadi);
- ``get_file_storage`` portfolio uchun vaqtinchalik katalogli ``LocalFileStorage``
  bilan override qilinadi (haqiqiy disk yozuvi sandbox ichida).

Autentifikatsiya **haqiqiy** token oqimi orqali tekshiriladi (register + login),
shu sababli ``get_current_principal``/RBAC override qilinmaydi — bu routerlar
deps + RBAC bilan to'g'ri bog'langanini tasdiqlaydi.

Qoplangan oqimlar:
- recommendations: me (bo'sh va to'la) + by-result (egalik 404);
- portfolio: list / upload (multipart) / delete (+ begona 403, yo'q 404);
- analytics: me (bo'sh va natijali);
- questions: CRUD admin-guard (non-admin 403, admin to'liq CRUD).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

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
    analytics_router,
    auth_router,
    portfolio_router,
    questions_router,
    recommendations_router,
)
from app.api.routers.portfolio import get_file_storage
from app.models.base import Base
from app.models.content import Test
from app.models.reference import Competency
from app.models.recommendation import Recommendation
from app.models.result import CompetencyResult, TestResult
from app.models.session import TestSession
from app.models.user import User
from app.repositories import RoleRepository
from app.services.recommendation_service import RecommendationService
from app.storage.local import LocalFileStorage

# --- Doimiy test ma'lumotlari ---
LEADER_PHONE = "+998901234567"
OTHER_PHONE = "+998907654321"
ADMIN_PHONE = "+998901112233"
PASSWORD = "secret123"

# Minimal yaroqli fayl mazmunlari (magic-bytes bilan) — portfolio upload uchun.
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
PDF_BYTES = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n"


# ---------------------------------------------------------------------------
# Fixturalar — in-memory SQLite + throwaway app
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine():
    """Sxema yaratilgan in-memory SQLite engine (StaticPool — thread ulashish)."""
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
def storage(tmp_path: Path) -> LocalFileStorage:
    """Vaqtinchalik katalogdagi LocalFileStorage (portfolio uchun)."""
    return LocalFileStorage(tmp_path / "uploads")


@pytest.fixture()
def client(engine, seed_roles, storage) -> Iterator[TestClient]:
    """17.3 routerlari ulangan throwaway ilova mijozi."""
    application = FastAPI()
    register_exception_handlers(application)
    application.include_router(auth_router)
    application.include_router(questions_router)
    application.include_router(recommendations_router)
    application.include_router(portfolio_router)
    application.include_router(analytics_router)

    def _override_db() -> Iterator[Session]:
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    application.dependency_overrides[get_db] = _override_db
    application.dependency_overrides[get_file_storage] = lambda: storage
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Yordamchilar
# ---------------------------------------------------------------------------


def _register(client: TestClient, *, phone: str = LEADER_PHONE, role: str = "Rahbar"):
    payload = {
        "phone": phone,
        "password": PASSWORD,
        "full_name": "Ali Valiyev",
        "role": role,
        "position": "Direktor",
        "experience_years": 5,
    }
    return client.post("/auth/register", json=payload)


def _access_token(client: TestClient, *, phone: str = LEADER_PHONE) -> str:
    resp = client.post("/auth/login", json={"phone": phone, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_result_with_recs(
    engine,
    *,
    user_id: int,
    percentage: str = "30.00",
    competency_percentages: list[str] | None = None,
) -> int:
    """Yakunlangan natija + kompetensiya natijalari + tavsiyalarni seed qiladi.

    Returns: yaratilgan ``TestResult.id``.
    """
    competency_percentages = competency_percentages or [percentage]
    with Session(engine) as sess:
        test = Test(title="Diagnostika", category="kompetensiya", duration_minutes=30)
        sess.add(test)
        sess.flush()

        comps = [Competency(name=f"Komp-{i}") for i in range(len(competency_percentages))]
        sess.add_all(comps)
        sess.flush()

        # Har bir kompetensiya+daraja uchun aniq mos tavsiya (R10.1).
        for comp, pct in zip(comps, competency_percentages):
            level = _level_for(Decimal(pct))
            sess.add(
                Recommendation(
                    competency_id=comp.id, level=level, text=f"{comp.name}-{level}"
                )
            )
        sess.flush()

        now = datetime.now(timezone.utc)
        ts = TestSession(
            user_id=user_id,
            test_id=test.id,
            status="completed",
            started_at=now,
            expires_at=now + timedelta(minutes=30),
            completed_at=now,
        )
        sess.add(ts)
        sess.flush()

        result = TestResult(
            user_id=user_id,
            test_id=test.id,
            session_id=ts.id,
            total_score=Decimal("10.00"),
            max_score=Decimal("20.00"),
            percentage=Decimal(percentage),
            level=_level_for(Decimal(percentage)),
        )
        for comp, pct in zip(comps, competency_percentages):
            result.competency_results.append(
                CompetencyResult(
                    competency_id=comp.id,
                    score=Decimal("5.00"),
                    max_score=Decimal("10.00"),
                    percentage=Decimal(pct),
                )
            )
        sess.add(result)
        sess.flush()
        result_id = result.id

        # Tavsiyalarni natijaga bog'lash (servisning haqiqiy mantig'i bilan).
        RecommendationService(sess).assign_recommendations(result)
        sess.commit()
        return result_id


def _level_for(percentage: Decimal) -> str:
    """Foizdan daraja (scoring bilan izchil) — test seed uchun."""
    if percentage <= 40:
        return "Past"
    if percentage <= 60:
        return "O'rta"
    if percentage <= 80:
        return "Yaxshi"
    return "Yuqori"


# ===========================================================================
# /recommendations (R10)
# ===========================================================================


def test_recommendations_me_empty_when_no_result(client: TestClient) -> None:
    """Natija yo'q bo'lsa bo'sh ro'yxat (xato emas) (R10.5)."""
    _register(client)
    token = _access_token(client)
    resp = client.get("/recommendations/me", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


def test_recommendations_me_requires_auth(client: TestClient) -> None:
    """Tokensiz /recommendations/me 401 (R2.5)."""
    assert client.get("/recommendations/me").status_code == 401


def test_recommendations_me_returns_latest(client: TestClient, engine) -> None:
    """So'nggi natijaga bog'langan tavsiyalar qaytadi (R10.2)."""
    user_id = _register(client).json()["id"]
    token = _access_token(client)
    _seed_result_with_recs(engine, user_id=user_id, percentage="30.00")

    resp = client.get("/recommendations/me", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["level"] == "Past"
    assert body[0]["text"].endswith("Past")


def test_recommendations_by_result_owner(client: TestClient, engine) -> None:
    """Egasi aniq natija id bo'yicha tavsiyalarni oladi (R10.3)."""
    user_id = _register(client).json()["id"]
    token = _access_token(client)
    result_id = _seed_result_with_recs(engine, user_id=user_id, percentage="90.00")

    resp = client.get(f"/recommendations/by-result/{result_id}", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["level"] == "Yuqori"


def test_recommendations_by_result_foreign_returns_404(
    client: TestClient, engine
) -> None:
    """Begona foydalanuvchi natijasi -> 404 (egalik, R10.6)."""
    owner_id = _register(client).json()["id"]
    _register(client, phone=OTHER_PHONE)
    other_token = _access_token(client, phone=OTHER_PHONE)
    result_id = _seed_result_with_recs(engine, user_id=owner_id, percentage="30.00")

    resp = client.get(
        f"/recommendations/by-result/{result_id}", headers=_auth(other_token)
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_recommendations_by_result_missing_returns_404(client: TestClient) -> None:
    """Mavjud bo'lmagan natija -> 404 (R10.6)."""
    _register(client)
    token = _access_token(client)
    resp = client.get("/recommendations/by-result/999999", headers=_auth(token))
    assert resp.status_code == 404


# ===========================================================================
# /portfolio (R11)
# ===========================================================================


def test_portfolio_me_empty(client: TestClient) -> None:
    """Yozuv yo'q bo'lsa bo'sh ro'yxat (R11.1)."""
    _register(client)
    token = _access_token(client)
    resp = client.get("/portfolio/me", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


def test_portfolio_me_requires_auth(client: TestClient) -> None:
    """Tokensiz /portfolio/me 401."""
    assert client.get("/portfolio/me").status_code == 401


def test_portfolio_upload_then_list(client: TestClient) -> None:
    """Multipart yuklash yozuv yaratadi va ro'yxatda ko'rinadi (R11.2)."""
    _register(client)
    token = _access_token(client)

    resp = client.post(
        "/portfolio/upload",
        headers=_auth(token),
        files={"file": ("sertifikat.png", PNG_BYTES, "image/png")},
        data={"title": "Sertifikat"},
    )
    assert resp.status_code == 201, resp.text
    item = resp.json()
    assert item["title"] == "Sertifikat"
    assert item["file_type"] == "png"
    assert item["size_bytes"] == len(PNG_BYTES)

    listed = client.get("/portfolio/me", headers=_auth(token))
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == item["id"]


def test_portfolio_upload_rejects_unsupported_type(client: TestClient) -> None:
    """Ruxsat etilmagan tur 400 va hech narsa saqlanmaydi (R11.3)."""
    _register(client)
    token = _access_token(client)
    resp = client.post(
        "/portfolio/upload",
        headers=_auth(token),
        files={"file": ("skript.exe", b"MZ\x90\x00", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "validation_error"
    # Hech narsa saqlanmaganini tasdiqlash.
    assert client.get("/portfolio/me", headers=_auth(token)).json() == []


def test_portfolio_delete_own_record(client: TestClient) -> None:
    """O'z yozuvini o'chirish 204 va ro'yxatdan chiqadi (R11.5)."""
    _register(client)
    token = _access_token(client)
    item = client.post(
        "/portfolio/upload",
        headers=_auth(token),
        files={"file": ("a.pdf", PDF_BYTES, "application/pdf")},
    ).json()

    resp = client.delete(f"/portfolio/{item['id']}", headers=_auth(token))
    assert resp.status_code == 204
    assert client.get("/portfolio/me", headers=_auth(token)).json() == []


def test_portfolio_delete_others_record_forbidden(client: TestClient) -> None:
    """Begona yozuvni o'chirishga urinish 403; holat o'zgarmaydi (R11.6)."""
    _register(client)
    owner_token = _access_token(client)
    item = client.post(
        "/portfolio/upload",
        headers=_auth(owner_token),
        files={"file": ("a.pdf", PDF_BYTES, "application/pdf")},
    ).json()

    _register(client, phone=OTHER_PHONE)
    other_token = _access_token(client, phone=OTHER_PHONE)

    resp = client.delete(f"/portfolio/{item['id']}", headers=_auth(other_token))
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"
    # Yozuv egada saqlanib qoladi.
    assert len(client.get("/portfolio/me", headers=_auth(owner_token)).json()) == 1


def test_portfolio_delete_missing_returns_404(client: TestClient) -> None:
    """Mavjud bo'lmagan yozuvni o'chirish 404 (R11.7)."""
    _register(client)
    token = _access_token(client)
    resp = client.delete("/portfolio/999999", headers=_auth(token))
    assert resp.status_code == 404


# ===========================================================================
# /analytics (R9)
# ===========================================================================


def test_analytics_me_empty_state(client: TestClient) -> None:
    """Natija yo'q bo'lsa muvaffaqiyatli bo'sh holat (R9.7)."""
    _register(client)
    token = _access_token(client)
    resp = client.get("/analytics/me", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_results"] is False
    assert body["overall_score"] == "0.00"
    assert body["distribution"] == []
    assert body["growth_diff"] is None


def test_analytics_me_requires_auth(client: TestClient) -> None:
    """Tokensiz /analytics/me 401."""
    assert client.get("/analytics/me").status_code == 401


def test_analytics_me_with_results(client: TestClient, engine) -> None:
    """Natija bo'lsa umumiy ball va taqsimot qaytadi (R9.1, R9.2)."""
    user_id = _register(client).json()["id"]
    token = _access_token(client)
    _seed_result_with_recs(
        engine,
        user_id=user_id,
        percentage="75.00",
        competency_percentages=["90.00", "30.00"],
    )

    resp = client.get("/analytics/me", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_results"] is True
    assert body["result_count"] == 1
    assert len(body["distribution"]) == 2
    # Kuchli va rivojlantirilishi lozim kompetensiyalar aniqlanadi (R9.5).
    assert len(body["strongest"]) >= 1
    assert len(body["to_develop"]) >= 1


# ===========================================================================
# /questions — admin guard (R14.5, R20.4)
# ===========================================================================


def test_questions_list_forbidden_for_leader(client: TestClient) -> None:
    """Rahbar /questions ga kira olmaydi -> 403 (R14.5)."""
    _register(client)
    token = _access_token(client)
    resp = client.get("/questions", headers=_auth(token))
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


def test_questions_list_requires_auth(client: TestClient) -> None:
    """Tokensiz /questions 401."""
    assert client.get("/questions").status_code == 401


def test_questions_create_forbidden_for_leader(client: TestClient) -> None:
    """Rahbar savol yarata olmaydi -> 403 (R14.5)."""
    _register(client)
    token = _access_token(client)
    resp = client.post(
        "/questions",
        headers=_auth(token),
        json={
            "test_id": 1,
            "question_text": "Savol?",
            "score": 5,
            "competency_id": 1,
            "answers": [
                {"answer_text": "A"},
                {"answer_text": "B"},
            ],
        },
    )
    assert resp.status_code == 403


def _seed_test_and_competency(engine) -> tuple[int, int]:
    """Bitta test va kompetensiya yaratadi; (test_id, competency_id) qaytaradi."""
    with Session(engine) as sess:
        test = Test(title="Admin test", category="kompetensiya", duration_minutes=30)
        comp = Competency(name="Boshqaruv")
        sess.add_all([test, comp])
        sess.commit()
        return test.id, comp.id


def test_questions_admin_full_crud(client: TestClient, engine) -> None:
    """Administrator savol yaratadi, ko'radi, tahrirlaydi va o'chiradi (R14)."""
    test_id, competency_id = _seed_test_and_competency(engine)
    _register(client, phone=ADMIN_PHONE, role="Administrator")
    admin_token = _access_token(client, phone=ADMIN_PHONE)

    # CREATE
    create = client.post(
        "/questions",
        headers=_auth(admin_token),
        json={
            "test_id": test_id,
            "question_text": "Jamoani qanday boshqarasiz?",
            "score": 5,
            "competency_id": competency_id,
            "question_type": "likert",
            "answers": [
                {"answer_text": "Variant A", "is_correct": False},
                {"answer_text": "Variant B", "is_correct": True},
            ],
        },
    )
    assert create.status_code == 201, create.text
    question = create.json()
    assert question["question_text"] == "Jamoani qanday boshqarasiz?"
    assert len(question["answers"]) == 2
    qid = question["id"]

    # LIST (test bo'yicha filtr)
    listed = client.get(
        "/questions", headers=_auth(admin_token), params={"test_id": test_id}
    )
    assert listed.status_code == 200
    assert any(q["id"] == qid for q in listed.json())

    # PATCH
    patched = client.patch(
        f"/questions/{qid}",
        headers=_auth(admin_token),
        json={"question_text": "Yangilangan savol"},
    )
    assert patched.status_code == 200
    assert patched.json()["question_text"] == "Yangilangan savol"

    # DELETE
    deleted = client.delete(f"/questions/{qid}", headers=_auth(admin_token))
    assert deleted.status_code == 204
    after = client.get(
        "/questions", headers=_auth(admin_token), params={"test_id": test_id}
    )
    assert all(q["id"] != qid for q in after.json())


def test_questions_create_invalid_returns_400(client: TestClient, engine) -> None:
    """Admin yaroqsiz savol (1 ta variant) yaratsa 400 (R14.3, R14.6)."""
    test_id, competency_id = _seed_test_and_competency(engine)
    _register(client, phone=ADMIN_PHONE, role="Administrator")
    admin_token = _access_token(client, phone=ADMIN_PHONE)

    resp = client.post(
        "/questions",
        headers=_auth(admin_token),
        json={
            "test_id": test_id,
            "question_text": "Savol?",
            "score": 5,
            "competency_id": competency_id,
            "answers": [{"answer_text": "Faqat bitta"}],
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "validation_error"


def test_questions_create_missing_competency_returns_404(
    client: TestClient, engine
) -> None:
    """Mavjud bo'lmagan kompetensiyaga bog'lash 404 (R14.7)."""
    test_id, _ = _seed_test_and_competency(engine)
    _register(client, phone=ADMIN_PHONE, role="Administrator")
    admin_token = _access_token(client, phone=ADMIN_PHONE)

    resp = client.post(
        "/questions",
        headers=_auth(admin_token),
        json={
            "test_id": test_id,
            "question_text": "Savol?",
            "score": 5,
            "competency_id": 999999,
            "answers": [
                {"answer_text": "A"},
                {"answer_text": "B"},
            ],
        },
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"
