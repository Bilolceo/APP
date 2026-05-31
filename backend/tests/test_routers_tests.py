"""Vazifa 17.2 integratsion testlari — test/sessiya/natija routerlari (R6, R7, R8, R4).

Testlar bir martalik (throwaway) FastAPI ilovasi ustida ishlaydi:
- ``auth_router``, ``users_router`` va ``tests_router`` ulanadi;
- ``register_exception_handlers`` markazlashtirilgan xato formatini ta'minlaydi
  (R20.6);
- ``get_db`` bog'liqligi in-memory SQLite sessiyasi bilan override qilinadi
  (``Base.metadata.create_all`` + standart rollar, kompetensiya va namunaviy
  faol test seed qilinadi).

Qoplangan oqimlar (R6, R7, R8):
- ``GET /tests`` — faol testlar ro'yxati; autentifikatsiya talab qilinadi.
- ``GET /tests/{id}`` — tafsilot (savollar bilan); mavjud bo'lmasa 404.
- ``POST /tests/{id}/start`` — sessiya boshlash (201) va idempotentlik (R7.10).
- ``POST /tests/{id}/submit`` — topshirish (muvaffaqiyat + idempotent 409 +
  to'liqsiz 400 + begona sessiya 404).
- ``GET /tests/results/me`` — o'z natijalari.
- ``GET /tests/results/{id}`` — natija tafsiloti egalik/RBAC bilan.

Autentifikatsiya **haqiqiy** token oqimi orqali tekshiriladi (login'dan olingan
access token bilan).
"""

from __future__ import annotations

from collections.abc import Iterator
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
from app.api.routers import auth_router, tests_router, users_router
from app.models.base import Base
from app.models.content import Answer, Question, Test
from app.models.reference import Competency
from app.repositories import RoleRepository

VALID_PHONE = "+998901234567"
OTHER_PHONE = "+998907654321"
ADMIN_PHONE = "+998901112233"
VALID_PASSWORD = "secret123"


# ---------------------------------------------------------------------------
# Fixturalar — in-memory SQLite + throwaway app + seed
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine():
    """Sxema yaratilgan in-memory SQLite engine (StaticPool — bitta baza)."""
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
def sample_test(engine, seed_roles) -> dict:
    """Bitta faol test: 2 ta variant tanlash savoli, kompetensiya bilan.

    Qaytaradi: ``{"test_id", "q1_id", "q2_id", "q1_correct", "q1_wrong",
    "q2_correct", "q2_wrong", "competency_id"}`` — testlar oqimini topshirishda
    foydalanish uchun.
    """
    with Session(engine) as sess:
        comp = Competency(name="Boshqaruv")
        sess.add(comp)
        sess.flush()

        test = Test(
            title="Kognitiv diagnostika",
            description="Namunaviy test",
            category="kognitiv",
            duration_minutes=30,
            is_active=True,
        )
        sess.add(test)
        sess.flush()

        q1 = Question(
            test_id=test.id,
            competency_id=comp.id,
            question_text="1-savol",
            question_type="cognitive",
            score=Decimal("10.00"),
            order_index=1,
        )
        q2 = Question(
            test_id=test.id,
            competency_id=comp.id,
            question_text="2-savol",
            question_type="cognitive",
            score=Decimal("10.00"),
            order_index=2,
        )
        sess.add_all([q1, q2])
        sess.flush()

        q1_correct = Answer(question_id=q1.id, answer_text="to'g'ri", is_correct=True)
        q1_wrong = Answer(question_id=q1.id, answer_text="xato", is_correct=False)
        q2_correct = Answer(question_id=q2.id, answer_text="to'g'ri", is_correct=True)
        q2_wrong = Answer(question_id=q2.id, answer_text="xato", is_correct=False)
        sess.add_all([q1_correct, q1_wrong, q2_correct, q2_wrong])
        sess.flush()

        data = {
            "test_id": test.id,
            "q1_id": q1.id,
            "q2_id": q2.id,
            "q1_correct": q1_correct.id,
            "q1_wrong": q1_wrong.id,
            "q2_correct": q2_correct.id,
            "q2_wrong": q2_wrong.id,
            "competency_id": comp.id,
        }
        sess.commit()
        return data


@pytest.fixture()
def inactive_test(engine, seed_roles) -> int:
    """Faol bo'lmagan test ID (R6.4 / R6.5 holatlari uchun)."""
    with Session(engine) as sess:
        test = Test(
            title="Nofaol test",
            category="kognitiv",
            duration_minutes=30,
            is_active=False,
        )
        sess.add(test)
        sess.flush()
        test_id = test.id
        sess.commit()
        return test_id


@pytest.fixture()
def client(engine, seed_roles) -> Iterator[TestClient]:
    """Auth + users + tests routerlari ulangan throwaway ilova mijozi."""
    application = FastAPI()
    register_exception_handlers(application)
    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(tests_router)

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


def _leader_token(client: TestClient) -> str:
    """Rahbarni ro'yxatdan o'tkazib, access token qaytaradi."""
    _register(client)
    return _access_token(client)


def _start_session(client: TestClient, token: str, test_id: int):
    return client.post(f"/tests/{test_id}/start", headers=_auth_header(token))


def _submit(client: TestClient, token: str, test_id: int, body: dict):
    return client.post(
        f"/tests/{test_id}/submit", json=body, headers=_auth_header(token)
    )


# ---------------------------------------------------------------------------
# GET /tests (R6.1)
# ---------------------------------------------------------------------------


def test_list_tests_requires_auth(client: TestClient, sample_test: dict) -> None:
    """Tokensiz /tests 401 (R20.3)."""
    resp = client.get("/tests")
    assert resp.status_code == 401


def test_list_tests_returns_active_only(client: TestClient, sample_test: dict) -> None:
    """Faqat faol testlar qaytadi (R6.1)."""
    token = _leader_token(client)
    resp = client.get("/tests", headers=_auth_header(token))
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    ids = [t["id"] for t in body]
    assert sample_test["test_id"] in ids
    assert all(t["id"] for t in body)


def test_list_tests_excludes_inactive(client: TestClient, inactive_test: int) -> None:
    """Nofaol test ro'yxatda yo'q; faol test bo'lmasa bo'sh ro'yxat (R6.5)."""
    token = _leader_token(client)
    resp = client.get("/tests", headers=_auth_header(token))
    assert resp.status_code == 200
    assert inactive_test not in [t["id"] for t in resp.json()]


# ---------------------------------------------------------------------------
# GET /tests/{id} (R6.3, R6.4)
# ---------------------------------------------------------------------------


def test_get_test_detail_returns_questions_in_order(
    client: TestClient, sample_test: dict
) -> None:
    """Test tafsiloti savollarni belgilangan tartibda qaytaradi (R6.3)."""
    token = _leader_token(client)
    resp = client.get(f"/tests/{sample_test['test_id']}", headers=_auth_header(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == sample_test["test_id"]
    assert body["question_count"] == 2
    order = [q["id"] for q in body["questions"]]
    assert order == [sample_test["q1_id"], sample_test["q2_id"]]
    # Variantlar bor, ammo to'g'rilik/ball oshkor qilinmaydi.
    first_q = body["questions"][0]
    assert len(first_q["answers"]) == 2
    assert "is_correct" not in first_q["answers"][0]
    assert "score" not in first_q["answers"][0]


def test_get_test_detail_missing_returns_404(
    client: TestClient, sample_test: dict
) -> None:
    """Mavjud bo'lmagan test 404 (R6.4)."""
    token = _leader_token(client)
    resp = client.get("/tests/999999", headers=_auth_header(token))
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_get_test_detail_inactive_returns_404(
    client: TestClient, inactive_test: int
) -> None:
    """Faol bo'lmagan test tafsiloti 404 (R6.4)."""
    token = _leader_token(client)
    resp = client.get(f"/tests/{inactive_test}", headers=_auth_header(token))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /tests/{id}/start (R7.1, R7.10)
# ---------------------------------------------------------------------------


def test_start_session_returns_201(client: TestClient, sample_test: dict) -> None:
    """Sessiya boshlash 201 va in_progress sessiya qaytaradi (R7.1)."""
    token = _leader_token(client)
    resp = _start_session(client, token, sample_test["test_id"])
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "in_progress"
    assert body["test_id"] == sample_test["test_id"]
    assert body["started_at"]
    assert body["expires_at"]


def test_start_session_idempotent(client: TestClient, sample_test: dict) -> None:
    """Tugatilmagan sessiya mavjud bo'lsa, yangisi yaratilmaydi (R7.10)."""
    token = _leader_token(client)
    first = _start_session(client, token, sample_test["test_id"]).json()
    second = _start_session(client, token, sample_test["test_id"]).json()
    assert first["id"] == second["id"]


def test_start_session_missing_test_returns_404(
    client: TestClient, sample_test: dict
) -> None:
    """Mavjud bo'lmagan testni boshlash 404 (R6.4)."""
    token = _leader_token(client)
    resp = _start_session(client, token, 999999)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /tests/{id}/submit (R7.6–R7.9, R8.6)
# ---------------------------------------------------------------------------


def test_submit_session_scores_and_persists(
    client: TestClient, sample_test: dict
) -> None:
    """To'liq javob: natija hisoblanadi va saqlanadi (R7.6, R8.6)."""
    token = _leader_token(client)
    session_id = _start_session(client, token, sample_test["test_id"]).json()["id"]

    # q1 to'g'ri, q2 xato -> 10/20 = 50%.
    resp = _submit(
        client,
        token,
        sample_test["test_id"],
        {
            "session_id": session_id,
            "answers": [
                {"question_id": sample_test["q1_id"], "answer_id": sample_test["q1_correct"]},
                {"question_id": sample_test["q2_id"], "answer_id": sample_test["q2_wrong"]},
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["result_id"]
    assert Decimal(str(body["percentage"])) == Decimal("50.00")
    assert body["level"] == "O'rta"
    assert any(c["competency_id"] == sample_test["competency_id"] for c in body["competencies"])
    assert body["next_retake_date"]


def test_submit_session_idempotent_resubmit_returns_409(
    client: TestClient, sample_test: dict
) -> None:
    """Allaqachon topshirilgan sessiyaga qayta topshirish 409 (R7.7)."""
    token = _leader_token(client)
    session_id = _start_session(client, token, sample_test["test_id"]).json()["id"]
    body = {
        "session_id": session_id,
        "answers": [
            {"question_id": sample_test["q1_id"], "answer_id": sample_test["q1_correct"]},
            {"question_id": sample_test["q2_id"], "answer_id": sample_test["q2_correct"]},
        ],
    }
    first = _submit(client, token, sample_test["test_id"], body)
    assert first.status_code == 200

    second = _submit(client, token, sample_test["test_id"], body)
    assert second.status_code == 409
    assert "code" in second.json()["error"]


def test_submit_session_incomplete_returns_400(
    client: TestClient, sample_test: dict
) -> None:
    """Muddat tugamagan + javobsiz savol -> 400 (R7.8)."""
    token = _leader_token(client)
    session_id = _start_session(client, token, sample_test["test_id"]).json()["id"]

    resp = _submit(
        client,
        token,
        sample_test["test_id"],
        {
            "session_id": session_id,
            "answers": [
                {"question_id": sample_test["q1_id"], "answer_id": sample_test["q1_correct"]},
            ],
        },
    )
    assert resp.status_code == 400
    # ValidationError tip bo'yicha 400; kod ``incomplete_submission`` (R7.8).
    assert resp.json()["error"]["code"] == "incomplete_submission"


def test_submit_session_foreign_session_returns_404(
    client: TestClient, sample_test: dict
) -> None:
    """Boshqa foydalanuvchining sessiyasiga topshirish 404 (R7.9)."""
    # Rahbar (egasi) sessiyani boshlaydi.
    owner_token = _leader_token(client)
    session_id = _start_session(client, owner_token, sample_test["test_id"]).json()["id"]

    # Boshqa foydalanuvchi shu sessiyani topshirishga urinadi.
    _register(client, phone=OTHER_PHONE, full_name="Boshqa Rahbar")
    other_token = _access_token(client, phone=OTHER_PHONE)
    resp = _submit(
        client,
        other_token,
        sample_test["test_id"],
        {
            "session_id": session_id,
            "answers": [
                {"question_id": sample_test["q1_id"], "answer_id": sample_test["q1_correct"]},
                {"question_id": sample_test["q2_id"], "answer_id": sample_test["q2_correct"]},
            ],
        },
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /tests/results/me va /tests/results/{id} (R8, R8.7, R4.1)
# ---------------------------------------------------------------------------


def _submit_full(client: TestClient, token: str, sample_test: dict) -> dict:
    """Sessiyani boshlab to'liq topshiradi; topshirish javob tanasini qaytaradi."""
    session_id = _start_session(client, token, sample_test["test_id"]).json()["id"]
    resp = _submit(
        client,
        token,
        sample_test["test_id"],
        {
            "session_id": session_id,
            "answers": [
                {"question_id": sample_test["q1_id"], "answer_id": sample_test["q1_correct"]},
                {"question_id": sample_test["q2_id"], "answer_id": sample_test["q2_correct"]},
            ],
        },
    )
    assert resp.status_code == 200
    return resp.json()


def test_results_me_returns_own_results(
    client: TestClient, sample_test: dict
) -> None:
    """``/tests/results/me`` so'rovchining natijalarini qaytaradi (R8)."""
    token = _leader_token(client)
    result = _submit_full(client, token, sample_test)

    resp = client.get("/tests/results/me", headers=_auth_header(token))
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert any(r["id"] == result["result_id"] for r in body)


def test_results_me_empty_when_no_results(
    client: TestClient, sample_test: dict
) -> None:
    """Natija bo'lmasa bo'sh ro'yxat (xato emas)."""
    token = _leader_token(client)
    resp = client.get("/tests/results/me", headers=_auth_header(token))
    assert resp.status_code == 200
    assert resp.json() == []


def test_result_detail_owner_allowed(
    client: TestClient, sample_test: dict
) -> None:
    """Natija egasi tafsilotni kompetensiya ballari bilan oladi (R8.7)."""
    token = _leader_token(client)
    result = _submit_full(client, token, sample_test)

    resp = client.get(
        f"/tests/results/{result['result_id']}", headers=_auth_header(token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == result["result_id"]
    assert body["competency_results"]
    assert any(
        c["competency_id"] == sample_test["competency_id"]
        for c in body["competency_results"]
    )


def test_result_detail_missing_returns_404(
    client: TestClient, sample_test: dict
) -> None:
    """Mavjud bo'lmagan natija 404 (R8.7)."""
    token = _leader_token(client)
    resp = client.get("/tests/results/999999", headers=_auth_header(token))
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_result_detail_foreign_forbidden_for_leader(
    client: TestClient, sample_test: dict
) -> None:
    """Boshqa rahbarning natijasiga kirish 403 (R4.1, R4.5)."""
    owner_token = _leader_token(client)
    result = _submit_full(client, owner_token, sample_test)

    _register(client, phone=OTHER_PHONE, full_name="Boshqa Rahbar")
    other_token = _access_token(client, phone=OTHER_PHONE)
    resp = client.get(
        f"/tests/results/{result['result_id']}", headers=_auth_header(other_token)
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


def test_result_detail_admin_can_access(
    client: TestClient, sample_test: dict
) -> None:
    """Administrator istalgan natijaga kira oladi (R4.3)."""
    owner_token = _leader_token(client)
    result = _submit_full(client, owner_token, sample_test)

    _register(client, phone=ADMIN_PHONE, role="Administrator", full_name="Admin")
    admin_token = _access_token(client, phone=ADMIN_PHONE)
    resp = client.get(
        f"/tests/results/{result['result_id']}", headers=_auth_header(admin_token)
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == result["result_id"]


def test_results_me_requires_auth(client: TestClient, sample_test: dict) -> None:
    """Tokensiz /tests/results/me 401 (R20.3)."""
    resp = client.get("/tests/results/me")
    assert resp.status_code == 401
