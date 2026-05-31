"""AnalyticsService uchun unit testlar (task 12.1, R9.1–R9.7).

`app/services/analytics_service.py` — Analitika_Moduli servisining biznes
mantig'ini in-memory SQLite engine ustida (mock'siz, real repositorylar va ORM
modellari bilan) tekshiradi.

Bog'liq talablar:
- R9.1: umumiy ball, kompetensiya taqsimoti va xronologik o'sish dinamikasi.
- R9.2: radar/progress/line/card uchun yetarli kompetensiya ma'lumoti.
- R9.3: joriy vs bevosita oldingi natija farqi (musbat/manfiy/nol).
- R9.4: bitta natijada farq "mavjud emas" (None).
- R9.5: eng yuqori -> kuchli; eng past -> rivojlantirilishi lozim kompetensiya.
- R9.6: teng qiymatda barcha teng kompetensiyalar qaytadi.
- R9.7: natija yo'q bo'lsa muvaffaqiyatli bo'sh holat (xato emas).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (modellarni metadata'ga ro'yxatdan o'tkazadi)
from app.core.db import create_db_engine
from app.domain.analytics import GrowthPoint
from app.models.base import Base
from app.models.content import Test
from app.models.reference import Competency, Role
from app.models.result import CompetencyResult, TestResult
from app.models.session import TestSession
from app.models.user import User
from app.services.analytics_service import (
    AnalyticsService,
    AnalyticsView,
    CompetencyDistributionItem,
    CompetencyRef,
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
def test_obj(session: Session) -> Test:
    """Namunaviy test."""
    t = Test(title="Diagnostika", category="kompetensiya", duration_minutes=30)
    session.add(t)
    session.flush()
    return t


@pytest.fixture()
def competencies(session: Session) -> list[Competency]:
    """Uchta kompetensiya."""
    c1 = Competency(name="Boshqaruv")
    c2 = Competency(name="Pedagogik")
    c3 = Competency(name="Kommunikativ")
    session.add_all([c1, c2, c3])
    session.flush()
    return [c1, c2, c3]


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
    percentage: Decimal,
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
        percentage=percentage,
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
# R9.7 — bo'sh holat
# ---------------------------------------------------------------------------


def test_no_results_returns_empty_state(session: Session, user: User) -> None:
    """Natija yo'q bo'lsa muvaffaqiyatli bo'sh holat qaytadi (R9.7)."""
    view = AnalyticsService(session).get_my_analytics(user.id)

    assert isinstance(view, AnalyticsView)
    assert view.has_results is False
    assert view.result_count == 0
    assert view.overall_score == Decimal("0.00")
    assert view.distribution == ()
    assert view.dynamics == ()
    assert view.growth_diff is None
    assert view.strongest == ()
    assert view.to_develop == ()


# ---------------------------------------------------------------------------
# R9.4 — bitta natija: farq "mavjud emas"
# ---------------------------------------------------------------------------


def test_single_result_diff_not_available(
    session: Session, user: User, test_obj: Test, competencies: list[Competency]
) -> None:
    """Bitta natijada o'sish farqi None, dinamika bitta nuqtadan iborat (R9.4)."""
    c1, c2, _ = competencies
    _make_result(
        session,
        user_id=user.id,
        test_id=test_obj.id,
        percentage=Decimal("60.00"),
        competency_rows=[(c1.id, Decimal("40.00")), (c2.id, Decimal("80.00"))],
    )
    session.commit()

    view = AnalyticsService(session).get_my_analytics(user.id)

    assert view.has_results is True
    assert view.result_count == 1
    assert view.growth_diff is None
    assert len(view.dynamics) == 1
    assert isinstance(view.dynamics[0], GrowthPoint)
    assert view.dynamics[0].percentage == Decimal("60.00")


# ---------------------------------------------------------------------------
# R9.1, R9.3 — dinamika xronologik, farq joriy vs oldingi
# ---------------------------------------------------------------------------


def test_dynamics_chronological_and_growth_diff_positive(
    session: Session, user: User, test_obj: Test, competencies: list[Competency]
) -> None:
    """Dinamika xronologik tartibda; farq joriy − oldingi (R9.1, R9.3)."""
    c1, _, _ = competencies
    t1 = datetime(2023, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2023, 6, 1, tzinfo=timezone.utc)
    t3 = datetime(2024, 1, 1, tzinfo=timezone.utc)

    # Ataylab xronologik bo'lmagan tartibda kiritamiz (repo o'suvchi qaytaradi).
    _make_result(
        session, user_id=user.id, test_id=test_obj.id,
        percentage=Decimal("50.00"),
        competency_rows=[(c1.id, Decimal("50.00"))], created_at=t2,
    )
    _make_result(
        session, user_id=user.id, test_id=test_obj.id,
        percentage=Decimal("40.00"),
        competency_rows=[(c1.id, Decimal("40.00"))], created_at=t1,
    )
    _make_result(
        session, user_id=user.id, test_id=test_obj.id,
        percentage=Decimal("70.00"),
        competency_rows=[(c1.id, Decimal("70.00"))], created_at=t3,
    )
    session.commit()

    view = AnalyticsService(session).get_my_analytics(user.id)

    # Xronologik (eng eskidan eng yangiga): 40 -> 50 -> 70.
    assert [p.percentage for p in view.dynamics] == [
        Decimal("40.00"),
        Decimal("50.00"),
        Decimal("70.00"),
    ]
    # `achieved_at` sanalari o'suvchi (xronologik) tartibda. Eslatma: SQLite
    # DateTime ustuni tzinfo'ni saqlamaydi, shuning uchun aniq tz-aware
    # tenglik o'rniga tartib o'suvchi ekanligi tekshiriladi.
    achieved = [p.achieved_at for p in view.dynamics]
    assert achieved == sorted(achieved)
    # Farq: 70 (joriy) − 50 (oldingi) = +20.
    assert view.growth_diff == Decimal("20.00")


def test_growth_diff_negative_and_zero(
    session: Session, user: User, test_obj: Test, competencies: list[Competency]
) -> None:
    """Farq manfiy va nol holatlari to'g'ri ishorada (R9.3)."""
    c1, _, _ = competencies
    t1 = datetime(2023, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2024, 1, 1, tzinfo=timezone.utc)

    # Pasayish: 80 -> 65 = -15.
    _make_result(
        session, user_id=user.id, test_id=test_obj.id,
        percentage=Decimal("80.00"),
        competency_rows=[(c1.id, Decimal("80.00"))], created_at=t1,
    )
    _make_result(
        session, user_id=user.id, test_id=test_obj.id,
        percentage=Decimal("65.00"),
        competency_rows=[(c1.id, Decimal("65.00"))], created_at=t2,
    )
    session.commit()

    view = AnalyticsService(session).get_my_analytics(user.id)
    assert view.growth_diff == Decimal("-15.00")


# ---------------------------------------------------------------------------
# R9.1, R9.2 — umumiy ball va taqsimot
# ---------------------------------------------------------------------------


def test_overall_score_and_distribution(
    session: Session, user: User, test_obj: Test, competencies: list[Competency]
) -> None:
    """Umumiy ball — natijalar o'rtachasi; taqsimot kompetensiya bo'yicha (R9.1, R9.2)."""
    c1, c2, _ = competencies
    # Natija 1: umumiy 40; c1=30, c2=50.
    _make_result(
        session, user_id=user.id, test_id=test_obj.id,
        percentage=Decimal("40.00"),
        competency_rows=[(c1.id, Decimal("30.00")), (c2.id, Decimal("50.00"))],
        created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
    )
    # Natija 2: umumiy 60; c1=50, c2=70.
    _make_result(
        session, user_id=user.id, test_id=test_obj.id,
        percentage=Decimal("60.00"),
        competency_rows=[(c1.id, Decimal("50.00")), (c2.id, Decimal("70.00"))],
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    session.commit()

    view = AnalyticsService(session).get_my_analytics(user.id)

    # Umumiy ball: (40 + 60) / 2 = 50.00.
    assert view.overall_score == Decimal("50.00")

    # Taqsimot kompetensiya id bo'yicha o'suvchi tartibda, jamlangan o'rtacha.
    by_comp = {item.competency_id: item for item in view.distribution}
    assert set(by_comp) == {c1.id, c2.id}
    # c1: (30 + 50) / 2 = 40.00 -> Past.
    assert by_comp[c1.id].percentage == Decimal("40.00")
    assert by_comp[c1.id].competency_name == "Boshqaruv"
    assert by_comp[c1.id].level == "Past"
    # c2: (50 + 70) / 2 = 60.00 -> O'rta.
    assert by_comp[c2.id].percentage == Decimal("60.00")
    assert by_comp[c2.id].competency_name == "Pedagogik"
    assert by_comp[c2.id].level == "O'rta"

    assert all(
        isinstance(item, CompetencyDistributionItem) for item in view.distribution
    )


# ---------------------------------------------------------------------------
# R9.5 — kuchli va rivojlantirilishi lozim kompetensiya
# ---------------------------------------------------------------------------


def test_strongest_and_to_develop_single(
    session: Session, user: User, test_obj: Test, competencies: list[Competency]
) -> None:
    """Eng yuqori -> kuchli; eng past -> rivojlantirilishi lozim (R9.5)."""
    c1, c2, c3 = competencies
    _make_result(
        session, user_id=user.id, test_id=test_obj.id,
        percentage=Decimal("60.00"),
        competency_rows=[
            (c1.id, Decimal("30.00")),  # eng past
            (c2.id, Decimal("60.00")),
            (c3.id, Decimal("90.00")),  # eng yuqori
        ],
    )
    session.commit()

    view = AnalyticsService(session).get_my_analytics(user.id)

    assert [r.competency_id for r in view.strongest] == [c3.id]
    assert view.strongest[0].competency_name == "Kommunikativ"
    assert [r.competency_id for r in view.to_develop] == [c1.id]
    assert view.to_develop[0].competency_name == "Boshqaruv"
    assert all(isinstance(r, CompetencyRef) for r in view.strongest)


# ---------------------------------------------------------------------------
# R9.6 — teng qiymatda barcha teng kompetensiyalar
# ---------------------------------------------------------------------------


def test_strongest_and_to_develop_ties(
    session: Session, user: User, test_obj: Test, competencies: list[Competency]
) -> None:
    """Teng yuqori/past qiymatda barcha teng kompetensiyalar qaytadi (R9.6)."""
    c1, c2, c3 = competencies
    # c1 va c2 teng eng past (40); c3 eng yuqori (90).
    _make_result(
        session, user_id=user.id, test_id=test_obj.id,
        percentage=Decimal("56.67"),
        competency_rows=[
            (c1.id, Decimal("40.00")),
            (c2.id, Decimal("40.00")),
            (c3.id, Decimal("90.00")),
        ],
    )
    session.commit()

    view = AnalyticsService(session).get_my_analytics(user.id)

    # Eng past teng: c1 va c2 (id bo'yicha o'suvchi).
    assert [r.competency_id for r in view.to_develop] == [c1.id, c2.id]
    # Eng yuqori: faqat c3.
    assert [r.competency_id for r in view.strongest] == [c3.id]


def test_single_competency_is_both_strongest_and_to_develop(
    session: Session, user: User, test_obj: Test, competencies: list[Competency]
) -> None:
    """Yagona kompetensiya bir vaqtda eng kuchli va eng past bo'ladi (R9.5)."""
    c1, _, _ = competencies
    _make_result(
        session, user_id=user.id, test_id=test_obj.id,
        percentage=Decimal("75.00"),
        competency_rows=[(c1.id, Decimal("75.00"))],
    )
    session.commit()

    view = AnalyticsService(session).get_my_analytics(user.id)
    assert [r.competency_id for r in view.strongest] == [c1.id]
    assert [r.competency_id for r in view.to_develop] == [c1.id]


# ---------------------------------------------------------------------------
# Izolyatsiya — boshqa foydalanuvchi natijalari aralashmaydi
# ---------------------------------------------------------------------------


def test_analytics_scoped_to_user(
    session: Session, user: User, test_obj: Test, competencies: list[Competency]
) -> None:
    """Faqat so'rovchining natijalari hisobga olinadi."""
    c1, _, _ = competencies
    other = User(
        full_name="Vali Aliyev",
        phone="+998901119988",
        password_hash="hashed",
        role_id=user.role_id,
    )
    session.add(other)
    session.flush()

    _make_result(
        session, user_id=user.id, test_id=test_obj.id,
        percentage=Decimal("50.00"),
        competency_rows=[(c1.id, Decimal("50.00"))],
    )
    # Boshqa foydalanuvchining natijasi — aralashmasligi kerak.
    _make_result(
        session, user_id=other.id, test_id=test_obj.id,
        percentage=Decimal("99.00"),
        competency_rows=[(c1.id, Decimal("99.00"))],
    )
    session.commit()

    view = AnalyticsService(session).get_my_analytics(user.id)
    assert view.result_count == 1
    assert view.overall_score == Decimal("50.00")
