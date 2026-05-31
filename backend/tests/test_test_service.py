"""TestService uchun unit testlari (task 10.3, R6.1–R6.5).

Diagnostika_Moduli (TestService) ning ``list_tests``, ``list_tests_by_category``
va ``get_test`` operatsiyalarini in-memory SQLite engine ustida tekshiradi
(`Base.metadata.create_all`). I/O'siz mock'siz: real repository va ORM modellari
ishlatiladi.

Bog'liq talablar:
- R6.1: ro'yxat faqat faol testlarni (id, nom, tavsif, toifa, davomiyligi) qaytaradi.
- R6.2: to'rt yo'nalish bo'yicha toifalash.
- R6.3: test tafsiloti + savollar ``order_index`` bo'yicha + javob variantlari.
- R6.4: mavjud yoki faol bo'lmagan test -> NotFoundError (404).
- R6.5: faol test yo'q bo'lsa bo'sh ro'yxat (xato emas).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (modellarni metadata'ga ro'yxatdan o'tkazadi)
from app.core.db import create_db_engine
from app.models.base import Base
from app.models.content import Answer, Question, Test
from app.services.test_service import (
    TEST_CATEGORIES,
    NotFoundError,
    TestService,
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
    """Test uchun bitta sessiya (tranzaksiya chegarasi test ichida)."""
    with Session(engine) as sess:
        yield sess


def _make_test(
    session: Session,
    *,
    title: str = "Test",
    category: str | None = "kognitiv",
    description: str | None = "desc",
    duration_minutes: int | None = 30,
    is_active: bool = True,
) -> Test:
    test = Test(
        title=title,
        category=category,
        description=description,
        duration_minutes=duration_minutes,
        is_active=is_active,
    )
    session.add(test)
    session.flush()
    return test


def _make_question(
    session: Session,
    *,
    test_id: int,
    text: str,
    order_index: int | None,
    competency_id: int | None = None,
    question_type: str | None = "cognitive",
) -> Question:
    q = Question(
        test_id=test_id,
        question_text=text,
        score=Decimal("1.00"),
        order_index=order_index,
        competency_id=competency_id,
        question_type=question_type,
    )
    session.add(q)
    session.flush()
    return q


# ---------------------------------------------------------------------------
# list_tests (R6.1, R6.5)
# ---------------------------------------------------------------------------


def test_list_tests_returns_only_active(session: Session) -> None:
    """Ro'yxat faqat faol testlarni qaytaradi; nofaol chetda (R6.1)."""
    active = _make_test(session, title="Faol", category="kognitiv")
    _make_test(session, title="Nofaol", category="reflexiv", is_active=False)
    session.commit()

    summaries = TestService(session).list_tests()

    assert [s.id for s in summaries] == [active.id]
    only = summaries[0]
    assert only.title == "Faol"
    assert only.description == "desc"
    assert only.category == "kognitiv"
    assert only.duration_minutes == 30


def test_list_tests_empty_when_no_active(session: Session) -> None:
    """Faol test bo'lmasa bo'sh ro'yxat qaytadi, xato emas (R6.5)."""
    _make_test(session, title="Nofaol", is_active=False)
    session.commit()

    assert TestService(session).list_tests() == []


def test_list_tests_empty_when_no_tests(session: Session) -> None:
    """Umuman test bo'lmasa ham bo'sh ro'yxat (R6.5)."""
    assert TestService(session).list_tests() == []


# ---------------------------------------------------------------------------
# list_tests_by_category (R6.2)
# ---------------------------------------------------------------------------


def test_list_tests_by_category_groups_four_directions(session: Session) -> None:
    """Faol testlar to'rt yo'nalish bo'yicha toifalanadi (R6.2)."""
    t_kog = _make_test(session, title="K", category="kognitiv")
    t_komp = _make_test(session, title="C", category="kompetensiya")
    t_ref = _make_test(session, title="R", category="reflexiv")
    t_sit = _make_test(session, title="S", category="situatsion")
    # Nofaol test toifalashga kirmaydi.
    _make_test(session, title="X", category="kognitiv", is_active=False)
    session.commit()

    grouped = TestService(session).list_tests_by_category()

    assert set(grouped.keys()) == set(TEST_CATEGORIES)
    assert [s.id for s in grouped["kognitiv"]] == [t_kog.id]
    assert [s.id for s in grouped["kompetensiya"]] == [t_komp.id]
    assert [s.id for s in grouped["reflexiv"]] == [t_ref.id]
    assert [s.id for s in grouped["situatsion"]] == [t_sit.id]


def test_list_tests_by_category_empty_groups_present(session: Session) -> None:
    """Mos test bo'lmasa yo'nalish bo'sh ro'yxat bilan qaytadi (R6.2, R6.5)."""
    grouped = TestService(session).list_tests_by_category()

    assert set(grouped.keys()) == set(TEST_CATEGORIES)
    assert all(grouped[c] == [] for c in TEST_CATEGORIES)


# ---------------------------------------------------------------------------
# get_test (R6.3, R6.4)
# ---------------------------------------------------------------------------


def test_get_test_returns_detail_with_ordered_questions(session: Session) -> None:
    """Tafsilot savollarni ``order_index`` bo'yicha tartibda qaytaradi (R6.3)."""
    test = _make_test(session, title="Detal", category="kompetensiya")
    # Ataylab tartibsiz qo'shamiz.
    q3 = _make_question(session, test_id=test.id, text="Q3", order_index=3)
    q1 = _make_question(session, test_id=test.id, text="Q1", order_index=1)
    q2 = _make_question(session, test_id=test.id, text="Q2", order_index=2)

    # q1 ga ikkita javob varianti.
    session.add_all(
        [
            Answer(question_id=q1.id, answer_text="A2"),
            Answer(question_id=q1.id, answer_text="A1"),
        ]
    )
    session.commit()

    detail = TestService(session).get_test(test.id)

    assert detail.id == test.id
    assert detail.title == "Detal"
    assert detail.category == "kompetensiya"
    assert detail.duration_minutes == 30
    assert detail.question_count == 3
    # order_index bo'yicha: q1, q2, q3.
    assert [q.question_text for q in detail.questions] == ["Q1", "Q2", "Q3"]
    assert [q.id for q in detail.questions] == [q1.id, q2.id, q3.id]
    # Javoblar id bo'yicha tartiblangan va faqat (id, matn) ochiladi.
    first_q_answers = detail.questions[0].answers
    assert [a.answer_text for a in first_q_answers] == ["A2", "A1"]
    assert all(hasattr(a, "answer_text") and hasattr(a, "id") for a in first_q_answers)


def test_get_test_questions_with_none_order_index_go_last(session: Session) -> None:
    """``order_index`` ``None`` bo'lgan savollar oxiriga joylashadi (R6.3)."""
    test = _make_test(session)
    q_none = _make_question(session, test_id=test.id, text="Oxirgi", order_index=None)
    q_first = _make_question(session, test_id=test.id, text="Birinchi", order_index=1)
    session.commit()

    detail = TestService(session).get_test(test.id)

    assert [q.id for q in detail.questions] == [q_first.id, q_none.id]


def test_get_test_no_questions_returns_empty(session: Session) -> None:
    """Savolsiz test tafsiloti bo'sh savollar ro'yxati bilan qaytadi (R6.3)."""
    test = _make_test(session)
    session.commit()

    detail = TestService(session).get_test(test.id)

    assert detail.question_count == 0
    assert detail.questions == []


def test_get_test_missing_raises_not_found(session: Session) -> None:
    """Mavjud bo'lmagan test -> NotFoundError (R6.4)."""
    with pytest.raises(NotFoundError):
        TestService(session).get_test(999999)


def test_get_test_inactive_raises_not_found(session: Session) -> None:
    """Faol bo'lmagan test -> NotFoundError (R6.4)."""
    test = _make_test(session, title="Nofaol", is_active=False)
    session.commit()

    with pytest.raises(NotFoundError):
        TestService(session).get_test(test.id)
