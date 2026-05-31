"""21.2-vazifa: uchidan-uchiga API oqimi integratsion testi.

Oqim:
ro'yxatdan o'tish -> login -> testlar ro'yxati -> sessiya boshlash ->
topshirish -> natija -> analitika -> reyting.

Test throwaway FastAPI ilovasi (in-memory SQLite) ustida ishlaydi.
"""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.deps import get_db
from app.api.errors import register_exception_handlers
from app.api.routers import (
    analytics_router,
    auth_router,
    rating_router,
    recommendations_router,
    tests_router,
    users_router,
)
from app.models.base import Base
from app.models.content import Answer, Question, Test
from app.models.reference import Competency
from app.repositories import RoleRepository

PHONE = "+998901234567"
PASSWORD = "secret123"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register(client: TestClient) -> None:
    resp = client.post(
        "/auth/register",
        json={
            "phone": PHONE,
            "password": PASSWORD,
            "full_name": "Ali Valiyev",
            "role": "Rahbar",
            "position": "Direktor",
            "experience_years": 5,
        },
    )
    assert resp.status_code == 201, resp.text


def _login_access_token(client: TestClient) -> str:
    resp = client.post(
        "/auth/login",
        json={"phone": PHONE, "password": PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _seed_active_test(engine) -> dict[str, int]:
    with Session(engine) as sess:
        competency = Competency(name="Boshqaruv")
        sess.add(competency)
        sess.flush()

        test = Test(
            title="Kognitiv diagnostika",
            description="E2E sinov testi",
            category="kognitiv",
            duration_minutes=30,
            is_active=True,
        )
        sess.add(test)
        sess.flush()

        q1 = Question(
            test_id=test.id,
            competency_id=competency.id,
            question_text="1-savol",
            question_type="cognitive",
            score=Decimal("10.00"),
            order_index=1,
        )
        q2 = Question(
            test_id=test.id,
            competency_id=competency.id,
            question_text="2-savol",
            question_type="cognitive",
            score=Decimal("10.00"),
            order_index=2,
        )
        sess.add_all([q1, q2])
        sess.flush()

        q1_ok = Answer(question_id=q1.id, answer_text="to'g'ri", is_correct=True)
        q2_ok = Answer(question_id=q2.id, answer_text="to'g'ri", is_correct=True)
        sess.add_all([q1_ok, q2_ok])
        sess.flush()

        sess.commit()
        return {
            "test_id": test.id,
            "q1_id": q1.id,
            "q2_id": q2.id,
            "q1_ok": q1_ok.id,
            "q2_ok": q2_ok.id,
        }


def _build_app(engine) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(tests_router)
    app.include_router(recommendations_router)
    app.include_router(analytics_router)
    app.include_router(rating_router)

    def _override_db() -> Iterator[Session]:
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_db
    return app


def test_end_to_end_leader_flow() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as sess:
            repo = RoleRepository(sess)
            for name in ("Rahbar", "Ekspert", "Administrator"):
                repo.create(name=name)
            sess.commit()

        sample = _seed_active_test(engine)
        app = _build_app(engine)

        with TestClient(app, raise_server_exceptions=False) as client:
            _register(client)
            token = _login_access_token(client)

            tests_resp = client.get("/tests", headers=_auth(token))
            assert tests_resp.status_code == 200, tests_resp.text
            tests_body = tests_resp.json()
            assert any(t["id"] == sample["test_id"] for t in tests_body)

            start_resp = client.post(
                f"/tests/{sample['test_id']}/start",
                headers=_auth(token),
            )
            assert start_resp.status_code == 201, start_resp.text
            session_id = start_resp.json()["id"]

            submit_resp = client.post(
                f"/tests/{sample['test_id']}/submit",
                headers=_auth(token),
                json={
                    "session_id": session_id,
                    "answers": [
                        {"question_id": sample["q1_id"], "answer_id": sample["q1_ok"]},
                        {"question_id": sample["q2_id"], "answer_id": sample["q2_ok"]},
                    ],
                },
            )
            assert submit_resp.status_code == 200, submit_resp.text
            result_id = submit_resp.json()["result_id"]

            my_results_resp = client.get("/tests/results/me", headers=_auth(token))
            assert my_results_resp.status_code == 200, my_results_resp.text
            assert any(r["id"] == result_id for r in my_results_resp.json())

            result_detail_resp = client.get(
                f"/tests/results/{result_id}",
                headers=_auth(token),
            )
            assert result_detail_resp.status_code == 200, result_detail_resp.text

            reco_resp = client.get("/recommendations/me", headers=_auth(token))
            assert reco_resp.status_code == 200, reco_resp.text
            assert isinstance(reco_resp.json(), list)

            analytics_resp = client.get("/analytics/me", headers=_auth(token))
            assert analytics_resp.status_code == 200, analytics_resp.text
            analytics = analytics_resp.json()
            assert analytics["has_results"] is True
            assert analytics["result_count"] >= 1

            rating_resp = client.get("/rating?scope=overall", headers=_auth(token))
            assert rating_resp.status_code == 200, rating_resp.text
            rating = rating_resp.json()
            assert rating["scope"] == "overall"
            assert "ranked" in rating and "out_of_ranking" in rating
            assert any(entry.get("is_requester") for entry in rating["ranked"])
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
