"""ORM modellari uchun unit testlari (task 2.1).

Bu testlar `design.md` — "Data Models" bo'limidagi barcha jadvallar ORM sifatida
e'lon qilinganini, ular umumiy `Base.metadata` ga ro'yxatdan o'tganini, sxema
yaratilishi (create_all) va asosiy munosabatlar (relationships) hamda
muhim ustun/cheklovlar mavjudligini tekshiradi.

Sinov uchun in-memory SQLite ishlatiladi (I/O'siz, tez). PostgreSQL-spetsifik
turlar (JSONB) `with_variant` orqali SQLite'ga moslashtirilgan.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (modellarni metadata'ga ro'yxatdan o'tkazadi)
from app.core.db import create_db_engine
from app.models import (
    Answer,
    Competency,
    CompetencyResult,
    DeviceToken,
    ExpertReview,
    Feedback,
    File,
    Organization,
    PasswordResetCode,
    Portfolio,
    Question,
    Recommendation,
    Region,
    RefreshToken,
    Role,
    Test,
    TestResult,
    TestSession,
    TokenBlacklist,
    User,
)
from app.models.base import Base

# design.md "Data Models" bo'limidagi barcha jadvallar.
EXPECTED_TABLES = {
    "users",
    "roles",
    "regions",
    "organizations",
    "competencies",
    "tests",
    "questions",
    "answers",
    "test_sessions",
    "session_answers",
    "test_results",
    "competency_results",
    "recommendations",
    "result_recommendations",
    "portfolios",
    "files",
    "expert_reviews",
    "refresh_tokens",
    "token_blacklist",
    "password_reset_codes",
    "device_tokens",
    "feedbacks",
}


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


def test_all_design_tables_registered() -> None:
    """Barcha kutilgan jadvallar `Base.metadata` da mavjud (R1.1, R18.1)."""
    assert EXPECTED_TABLES.issubset(set(Base.metadata.tables.keys()))


def test_schema_creates_all_tables(engine) -> None:
    """`create_all` barcha jadvallarni muvaffaqiyatli yaratadi."""
    inspector = inspect(engine)
    created = set(inspector.get_table_names())
    assert EXPECTED_TABLES.issubset(created)


def test_users_phone_is_unique_and_required() -> None:
    """`users.phone` UNIQUE va NOT NULL (R1.6, R5.4)."""
    phone_col = User.__table__.c.phone
    assert phone_col.unique is True
    assert phone_col.nullable is False
    assert phone_col.type.length == 13


def test_test_result_session_id_unique() -> None:
    """`test_results.session_id` UNIQUE — idempotentlik (R7.7)."""
    assert TestResult.__table__.c.session_id.unique is True


def test_active_session_partial_unique_index_declared() -> None:
    """`test_sessions` qisman noyob indeksi e'lon qilingan (R7.10)."""
    index_names = {ix.name for ix in TestSession.__table__.indexes}
    assert "uq_test_sessions_active_user_test" in index_names


def test_expert_review_has_six_criteria() -> None:
    """Ekspert sharhida 6 mezon ustuni mavjud (R13.1)."""
    cols = set(ExpertReview.__table__.c.keys())
    for criterion in (
        "management_culture",
        "teamwork",
        "pedagogical_process",
        "innovation",
        "documentation",
        "strategic_planning",
    ):
        assert criterion in cols


def test_question_competency_nullable() -> None:
    """`questions.competency_id` NULL bo'lishi mumkin — bog'lanmagan savol (R8.5)."""
    assert Question.__table__.c.competency_id.nullable is True


def test_basic_round_trip_insert(engine) -> None:
    """Asosiy yozuvlar yaratiladi va munosabatlar orqali o'qiladi."""
    with Session(engine) as session:
        role = Role(name="Rahbar")
        region = Region(name="Toshkent")
        org = Organization(name="MTT-1", region=region, org_type="davlat")
        user = User(
            full_name="Test Rahbar",
            phone="+998901234567",
            password_hash="hashed",
            role=role,
            organization=org,
            region=region,
            experience_years=5,
        )
        comp = Competency(name="Boshqaruv", description="Boshqaruv kompetensiyasi")
        test = Test(
            title="Kognitiv test",
            category="kognitiv",
            duration_minutes=30,
            is_active=True,
        )
        question = Question(
            test=test,
            competency=comp,
            question_text="Savol matni?",
            question_type="cognitive",
            score=Decimal("1.00"),
            order_index=1,
        )
        answer = Answer(
            question=question,
            answer_text="Variant A",
            is_correct=True,
            score=Decimal("1.00"),
        )
        session.add_all([role, region, org, user, comp, test, question, answer])
        session.commit()

        loaded = session.query(User).filter_by(phone="+998901234567").one()
        assert loaded.role.name == "Rahbar"
        assert loaded.organization.name == "MTT-1"
        assert loaded.region.name == "Toshkent"
        assert test.questions[0].answers[0].answer_text == "Variant A"


def test_result_and_recommendation_round_trip(engine) -> None:
    """Natija, kompetensiya natijasi va tavsiya bog'lanishi saqlanadi (R8.6, R10.1)."""
    with Session(engine) as session:
        role = Role(name="Rahbar")
        user = User(
            full_name="Rahbar 2",
            phone="+998901112233",
            password_hash="h",
            role=role,
        )
        test = Test(title="Test", category="kompetensiya", duration_minutes=10)
        comp = Competency(name="Innovatsiya")
        sess = TestSession(
            user=user,
            test=test,
            status="completed",
            started_at=datetime.now(timezone.utc),
        )
        result = TestResult(
            user=user,
            test=test,
            session=sess,
            total_score=Decimal("8.00"),
            max_score=Decimal("10.00"),
            percentage=Decimal("80.00"),
            level="Yuqori",
        )
        comp_result = CompetencyResult(
            result=result,
            competency=comp,
            score=Decimal("8.00"),
            max_score=Decimal("10.00"),
            percentage=Decimal("80.00"),
        )
        rec = Recommendation(competency=comp, level="Yuqori", text="Davom eting")
        session.add_all([role, user, test, comp, sess, result, comp_result, rec])
        session.commit()

        loaded = session.query(TestResult).one()
        assert loaded.session.status == "completed"
        assert loaded.competency_results[0].percentage == Decimal("80.00")


def test_auth_and_device_token_tables(engine) -> None:
    """Autentifikatsiya yordamchi va qurilma tokeni jadvallari ishlaydi."""
    with Session(engine) as session:
        role = Role(name="Rahbar")
        user = User(
            full_name="Auth User",
            phone="+998900000000",
            password_hash="h",
            role=role,
        )
        now = datetime.now(timezone.utc)
        refresh = RefreshToken(
            user=user, token_hash="t", expires_at=now, revoked=False
        )
        reset = PasswordResetCode(
            user=user, code_hash="c", expires_at=now, attempts=0, consumed=False
        )
        device = DeviceToken(
            user=user, token="dt", platform="android", is_valid=True
        )
        blacklist = TokenBlacklist(jti="jti-123", expires_at=now)
        session.add_all([role, user, refresh, reset, device, blacklist])
        session.commit()

        assert session.query(RefreshToken).count() == 1
        assert session.query(TokenBlacklist).filter_by(jti="jti-123").one()


def test_feedback_jsonb_payload_round_trip(engine) -> None:
    """`feedbacks.payload` JSON ma'lumotni saqlaydi (post-MVP, R18.1)."""
    with Session(engine) as session:
        role = Role(name="Rahbar")
        target = User(
            full_name="Target",
            phone="+998905556677",
            password_hash="h",
            role=role,
        )
        fb = Feedback(
            target_user=target,
            source_type="expert",
            payload={"score": 5, "comment": "ok"},
        )
        session.add_all([role, target, fb])
        session.commit()

        loaded = session.query(Feedback).one()
        assert loaded.payload == {"score": 5, "comment": "ok"}
        assert loaded.source_type == "expert"


def test_portfolio_file_relationship(engine) -> None:
    """Portfolio fayl bilan bog'lanadi (R11.1)."""
    with Session(engine) as session:
        role = Role(name="Rahbar")
        user = User(
            full_name="P User",
            phone="+998907778899",
            password_hash="h",
            role=role,
        )
        f = File(
            storage_key="key-1",
            file_url="http://x/key-1",
            file_type="pdf",
            size_bytes=1024,
        )
        p = Portfolio(user=user, title="Sertifikat", file=f)
        session.add_all([role, user, f, p])
        session.commit()

        loaded = session.query(Portfolio).one()
        assert loaded.file.storage_key == "key-1"
        assert loaded.user.full_name == "P User"
