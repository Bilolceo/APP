"""RecommendationService uchun unit testlar (task 12.2, R10.1–R10.6).

`app/services/recommendation_service.py` — Tavsiya_Moduli servisining biznes
mantig'ini in-memory SQLite engine ustida (mock'siz, real repositorylar va ORM
modellari bilan) tekshiradi.

Bog'liq talablar:
- R10.1: natija hisoblanganda har bir kompetensiya+daraja uchun tavsiya
  avtomatik tanlanadi va natijaga bog'lab saqlanadi.
- R10.2: foydalanuvchi tavsiyalarni so'raganda so'nggi natijaga bog'langan
  tavsiyalar kompetensiya nomi, darajasi va matni bilan qaytadi.
- R10.3: aniq natija id bo'yicha bog'langan tavsiyalar qaytadi.
- R10.4: aniq mos tavsiya bo'lmasa umumiy standart tavsiya tanlanadi.
- R10.5: yakunlangan natija yo'q bo'lsa bo'sh holat (xato emas).
- R10.6: natija mavjud emas yoki begona bo'lsa NotFoundError (404).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (modellarni metadata'ga ro'yxatdan o'tkazadi)
from app.core.db import create_db_engine
from app.models.base import Base
from app.models.content import Test
from app.models.recommendation import Recommendation
from app.models.reference import Competency, Role
from app.models.result import CompetencyResult, TestResult
from app.models.session import TestSession
from app.models.user import User
from app.services.errors import NotFoundError
from app.services.recommendation_service import (
    RecommendationService,
    RecommendationView,
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
    """Namunaviy foydalanuvchi (Rahbar)."""
    role = Role(name="Rahbar")
    session.add(role)
    session.flush()
    u = User(
        full_name="Ali Valiyev",
        phone="+998901112233",
        password_hash="hashed",
        role_id=role.id,
    )
    session.add(u)
    session.flush()
    return u


@pytest.fixture()
def other_user(session: Session) -> User:
    """Boshqa foydalanuvchi — egalik tekshiruvi uchun (R10.6)."""
    role = session.query(Role).first()
    u = User(
        full_name="Vali Aliyev",
        phone="+998901119988",
        password_hash="hashed",
        role_id=role.id,
    )
    session.add(u)
    session.flush()
    return u


@pytest.fixture()
def test_obj(session: Session) -> Test:
    """Namunaviy test."""
    t = Test(title="Diagnostika", category="kompetensiya", duration_minutes=30)
    session.add(t)
    session.flush()
    return t


@pytest.fixture()
def competencies(session: Session) -> list[Competency]:
    """Ikkita kompetensiya."""
    c1 = Competency(name="Boshqaruv")
    c2 = Competency(name="Pedagogik")
    session.add_all([c1, c2])
    session.flush()
    return [c1, c2]


def _make_session(session: Session, *, user_id: int, test_id: int) -> TestSession:
    now = datetime.now(timezone.utc)
    ts = TestSession(
        user_id=user_id,
        test_id=test_id,
        status="completed",
        started_at=now,
        expires_at=now + timedelta(minutes=30),
        completed_at=now,
    )
    session.add(ts)
    session.flush()
    return ts


def _make_result(
    session: Session,
    *,
    user_id: int,
    test_id: int,
    competency_rows: list[tuple[int, Decimal]],
    created_at: datetime | None = None,
) -> TestResult:
    """Natija + kompetensiya natijalarini yaratadi.

    ``competency_rows``: (competency_id, percentage) juftliklari.
    """
    ts = _make_session(session, user_id=user_id, test_id=test_id)
    result = TestResult(
        user_id=user_id,
        test_id=test_id,
        session_id=ts.id,
        total_score=Decimal("10.00"),
        max_score=Decimal("20.00"),
        percentage=Decimal("50.00"),
        level="O'rta",
    )
    if created_at is not None:
        result.created_at = created_at
    for competency_id, pct in competency_rows:
        result.competency_results.append(
            CompetencyResult(
                competency_id=competency_id,
                score=Decimal("5.00"),
                max_score=Decimal("10.00"),
                percentage=pct,
            )
        )
    session.add(result)
    session.flush()
    return result


# ---------------------------------------------------------------------------
# assign_recommendations (R10.1, R10.4)
# ---------------------------------------------------------------------------


def test_assign_recommendations_exact_match(
    session: Session, user: User, test_obj: Test, competencies: list[Competency]
) -> None:
    """Har bir kompetensiya+daraja uchun aniq mos tavsiya bog'lanadi (R10.1)."""
    c1, c2 = competencies
    # c1: 30% -> Past; c2: 90% -> Yuqori.
    session.add_all(
        [
            Recommendation(competency_id=c1.id, level="Past", text="c1-past"),
            Recommendation(competency_id=c2.id, level="Yuqori", text="c2-yuqori"),
        ]
    )
    result = _make_result(
        session,
        user_id=user.id,
        test_id=test_obj.id,
        competency_rows=[(c1.id, Decimal("30.00")), (c2.id, Decimal("90.00"))],
    )
    session.commit()

    views = RecommendationService(session).assign_recommendations(result)
    session.commit()

    by_comp = {v.competency_id: v for v in views}
    assert by_comp[c1.id].level == "Past"
    assert by_comp[c1.id].text == "c1-past"
    assert by_comp[c1.id].competency_name == "Boshqaruv"
    assert by_comp[c2.id].level == "Yuqori"
    assert by_comp[c2.id].text == "c2-yuqori"

    # Persist qilingani — qayta o'qishda ham mavjud (round-trip, R10.1).
    reread = RecommendationService(session).get_my_recommendations(user.id)
    assert {v.text for v in reread} == {"c1-past", "c2-yuqori"}


def test_assign_recommendations_general_fallback(
    session: Session, user: User, test_obj: Test, competencies: list[Competency]
) -> None:
    """Aniq mos bo'lmasa umumiy standart tavsiya tanlanadi (R10.4)."""
    c1, c2 = competencies
    # Faqat darajaga bog'langan umumiy standart tavsiyalar (competency_id NULL).
    session.add_all(
        [
            Recommendation(competency_id=None, level="Past", text="std-past"),
            Recommendation(competency_id=None, level="O'rta", text="std-orta"),
        ]
    )
    # c1: 20% -> Past; c2: 50% -> O'rta.
    result = _make_result(
        session,
        user_id=user.id,
        test_id=test_obj.id,
        competency_rows=[(c1.id, Decimal("20.00")), (c2.id, Decimal("50.00"))],
    )
    session.commit()

    views = RecommendationService(session).assign_recommendations(result)
    session.commit()

    by_comp = {v.competency_id: v for v in views}
    assert by_comp[c1.id].text == "std-past"
    assert by_comp[c2.id].text == "std-orta"


def test_assign_recommendations_levelless_general_fallback(
    session: Session, user: User, test_obj: Test, competencies: list[Competency]
) -> None:
    """Darajasiz umumiy standart tavsiya barcha darajalarga taalluqli (R10.4)."""
    c1, _ = competencies
    session.add(Recommendation(competency_id=None, level=None, text="umumiy"))
    # c1: 75% -> Yaxshi — aniq mos ham, darajaga mos standart ham yo'q.
    result = _make_result(
        session,
        user_id=user.id,
        test_id=test_obj.id,
        competency_rows=[(c1.id, Decimal("75.00"))],
    )
    session.commit()

    views = RecommendationService(session).assign_recommendations(result)
    session.commit()

    assert len(views) == 1
    assert views[0].text == "umumiy"
    assert views[0].level == "Yaxshi"


def test_assign_recommendations_no_competencies_returns_empty(
    session: Session, user: User, test_obj: Test
) -> None:
    """Kompetensiya natijasi bo'lmasa hech narsa bog'lanmaydi."""
    result = _make_result(
        session, user_id=user.id, test_id=test_obj.id, competency_rows=[]
    )
    session.commit()

    assert RecommendationService(session).assign_recommendations(result) == []


def test_assign_recommendations_no_fallback_keeps_only_exact(
    session: Session, user: User, test_obj: Test, competencies: list[Competency]
) -> None:
    """Umumiy standart seed qilinmagan bo'lsa, faqat aniq mos saqlanadi (graceful)."""
    c1, c2 = competencies
    # Faqat c1 uchun aniq tavsiya; c2 uchun na aniq, na umumiy standart.
    session.add(Recommendation(competency_id=c1.id, level="Past", text="c1-past"))
    result = _make_result(
        session,
        user_id=user.id,
        test_id=test_obj.id,
        competency_rows=[(c1.id, Decimal("30.00")), (c2.id, Decimal("90.00"))],
    )
    session.commit()

    views = RecommendationService(session).assign_recommendations(result)
    session.commit()

    assert [v.competency_id for v in views] == [c1.id]
    assert views[0].text == "c1-past"


# ---------------------------------------------------------------------------
# get_my_recommendations (R10.2, R10.5)
# ---------------------------------------------------------------------------


def test_get_my_recommendations_uses_latest_result(
    session: Session, user: User, test_obj: Test, competencies: list[Competency]
) -> None:
    """So'nggi yakunlangan natija tavsiyalari qaytadi (R10.2)."""
    c1, _ = competencies
    session.add(Recommendation(competency_id=c1.id, level="Past", text="eski"))
    session.add(Recommendation(competency_id=c1.id, level="Yuqori", text="yangi"))
    session.flush()

    old = datetime(2023, 1, 1, tzinfo=timezone.utc)
    new = datetime(2024, 1, 1, tzinfo=timezone.utc)
    old_result = _make_result(
        session,
        user_id=user.id,
        test_id=test_obj.id,
        competency_rows=[(c1.id, Decimal("30.00"))],
        created_at=old,
    )
    new_result = _make_result(
        session,
        user_id=user.id,
        test_id=test_obj.id,
        competency_rows=[(c1.id, Decimal("90.00"))],
        created_at=new,
    )
    session.commit()

    svc = RecommendationService(session)
    svc.assign_recommendations(old_result)
    svc.assign_recommendations(new_result)
    session.commit()

    views = svc.get_my_recommendations(user.id)
    # Faqat eng so'nggi natija (Yuqori) tavsiyalari.
    assert [v.text for v in views] == ["yangi"]
    assert views[0].competency_name == "Boshqaruv"


def test_get_my_recommendations_empty_when_no_result(
    session: Session, user: User
) -> None:
    """Yakunlangan natija yo'q bo'lsa bo'sh holat, xato emas (R10.5)."""
    result = RecommendationService(session).get_my_recommendations(user.id)
    assert result == []


# ---------------------------------------------------------------------------
# get_recommendations_by_result (R10.3, R10.6)
# ---------------------------------------------------------------------------


def test_get_recommendations_by_result_owner(
    session: Session, user: User, test_obj: Test, competencies: list[Competency]
) -> None:
    """Egasi aniq natija id bo'yicha tavsiyalarni oladi (R10.3)."""
    c1, _ = competencies
    session.add(Recommendation(competency_id=c1.id, level="Past", text="c1-past"))
    result = _make_result(
        session,
        user_id=user.id,
        test_id=test_obj.id,
        competency_rows=[(c1.id, Decimal("30.00"))],
    )
    session.commit()

    svc = RecommendationService(session)
    svc.assign_recommendations(result)
    session.commit()

    views = svc.get_recommendations_by_result(user.id, result.id)
    assert [v.text for v in views] == ["c1-past"]


def test_get_recommendations_by_result_missing_raises_not_found(
    session: Session, user: User
) -> None:
    """Mavjud bo'lmagan natija -> NotFoundError (R10.6)."""
    with pytest.raises(NotFoundError):
        RecommendationService(session).get_recommendations_by_result(
            user.id, 999999
        )


def test_get_recommendations_by_result_foreign_raises_not_found(
    session: Session,
    user: User,
    other_user: User,
    test_obj: Test,
    competencies: list[Competency],
) -> None:
    """Begona foydalanuvchi natijasi -> NotFoundError (egalik, R10.6)."""
    c1, _ = competencies
    result = _make_result(
        session,
        user_id=user.id,
        test_id=test_obj.id,
        competency_rows=[(c1.id, Decimal("30.00"))],
    )
    session.commit()

    # other_user boshqa odamning natijasini so'raydi -> 404.
    with pytest.raises(NotFoundError):
        RecommendationService(session).get_recommendations_by_result(
            other_user.id, result.id
        )


def test_views_are_recommendation_view_instances(
    session: Session, user: User, test_obj: Test, competencies: list[Competency]
) -> None:
    """assign natijasi RecommendationView tipida (DTO shartnomasi)."""
    c1, _ = competencies
    session.add(Recommendation(competency_id=c1.id, level="Past", text="c1-past"))
    result = _make_result(
        session,
        user_id=user.id,
        test_id=test_obj.id,
        competency_rows=[(c1.id, Decimal("30.00"))],
    )
    session.commit()

    views = RecommendationService(session).assign_recommendations(result)
    assert all(isinstance(v, RecommendationView) for v in views)
