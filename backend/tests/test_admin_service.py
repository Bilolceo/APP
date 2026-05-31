"""AdminService uchun unit testlari (task 13.6, R14.1–R14.8).

Admin_Moduli (AdminService) ning test/savol/kompetensiya/tavsiya CRUD
operatsiyalarini va validatsiyasini in-memory SQLite engine ustida tekshiradi
(`Base.metadata.create_all`). I/O'siz, mock'siz: real repository va ORM
modellari ishlatiladi.

Bog'liq talablar:
- R14.1: kompetensiya/tavsiya CRUD.
- R14.2: test validatsiyasi (nom 1–200, toifa, davomiyligi 1–600 butun).
- R14.3: savol validatsiyasi (matn 1–1000, ≥2 variant, ball 0.01–1000, mavjud
  kompetensiya).
- R14.4: testni o'chirish/nofaol qilish faol ro'yxatdan chiqaradi.
- R14.6: yaroqsiz/to'liqsiz -> ValidationError, hech narsa saqlanmaydi.
- R14.7: mavjud bo'lmagan kompetensiya -> NotFoundError.
- R14.8: ishlatilayotgan kompetensiyani o'chirish -> ConflictError.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (modellarni metadata'ga ro'yxatdan o'tkazadi)
from app.core.db import create_db_engine
from app.models.base import Base
from app.models.content import Question, Test
from app.repositories.tests import (
    AnswerRepository,
    QuestionRepository,
    TestRepository,
)
from app.repositories.reference import CompetencyRepository
from app.services.admin_service import (
    MAX_QUESTION_SCORE,
    MAX_TITLE_LENGTH,
    MIN_QUESTION_SCORE,
    AdminService,
)
from app.services.errors import ConflictError, NotFoundError, ValidationError


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


@pytest.fixture()
def admin(session: Session) -> AdminService:
    return AdminService(session)


def _two_answers() -> list[dict[str, object]]:
    return [
        {"answer_text": "Variant A", "is_correct": True},
        {"answer_text": "Variant B", "is_correct": False},
    ]


def _make_competency(session: Session, name: str = "Boshqaruv") -> int:
    comp = CompetencyRepository(session).create(name=name)
    session.flush()
    return comp.id


# ---------------------------------------------------------------------------
# Test CRUD (R14.2, R14.4, R14.6)
# ---------------------------------------------------------------------------


def test_create_test_persists_valid_test(admin: AdminService, session: Session) -> None:
    """Yaroqli test saqlanadi va faol ro'yxatda mavjud bo'ladi (R14.2)."""
    test = admin.create_test(
        title="Kognitiv test",
        category="kognitiv",
        duration_minutes=30,
        description="tavsif",
    )
    session.commit()

    assert test.id is not None
    assert test.is_active is True
    assert [t.id for t in TestRepository(session).list_active()] == [test.id]


@pytest.mark.parametrize(
    "kwargs, field",
    [
        ({"title": "  ", "category": "kognitiv", "duration_minutes": 30}, "title"),
        ({"title": "x" * 201, "category": "kognitiv", "duration_minutes": 30}, "title"),
        ({"title": "Ok", "category": "boshqa", "duration_minutes": 30}, "category"),
        ({"title": "Ok", "category": "kognitiv", "duration_minutes": 0}, "duration_minutes"),
        ({"title": "Ok", "category": "kognitiv", "duration_minutes": 601}, "duration_minutes"),
        ({"title": "Ok", "category": "kognitiv", "duration_minutes": 1.5}, "duration_minutes"),
        ({"title": "Ok", "category": "kognitiv", "duration_minutes": True}, "duration_minutes"),
    ],
)
def test_create_test_invalid_rejected_and_persists_nothing(
    admin: AdminService, session: Session, kwargs: dict, field: str
) -> None:
    """Yaroqsiz test rad etiladi, hech narsa saqlanmaydi (R14.2, R14.6)."""
    with pytest.raises(ValidationError) as exc:
        admin.create_test(**kwargs)
    assert exc.value.field == field
    session.rollback()
    assert TestRepository(session).list_all() == []


def test_create_test_boundary_values_accepted(admin: AdminService, session: Session) -> None:
    """Chegaraviy qiymatlar (nom 200, davomiylik 1 va 600) qabul qilinadi (R14.2)."""
    t1 = admin.create_test(title="x" * MAX_TITLE_LENGTH, category="reflexiv", duration_minutes=1)
    t2 = admin.create_test(title="y", category="situatsion", duration_minutes=600)
    session.commit()
    assert t1.duration_minutes == 1
    assert t2.duration_minutes == 600


def test_update_test_partial_and_validation(admin: AdminService, session: Session) -> None:
    """Qisman yangilash ishlaydi; yaroqsiz qiymat eski holatni o'zgartirmaydi (R14.2, R14.6)."""
    test = admin.create_test(title="Asl", category="kognitiv", duration_minutes=10)
    session.commit()

    updated = admin.update_test(test.id, title="Yangi", duration_minutes=20)
    session.commit()
    assert updated.title == "Yangi"
    assert updated.duration_minutes == 20
    assert updated.category == "kognitiv"  # o'zgarmagan

    with pytest.raises(ValidationError):
        admin.update_test(test.id, category="notvalid")
    session.rollback()
    assert TestRepository(session).get_by_id(test.id).category == "kognitiv"


def test_update_test_missing_raises_not_found(admin: AdminService) -> None:
    with pytest.raises(NotFoundError):
        admin.update_test(999999, title="x")


def test_deactivate_test_removes_from_active_list(admin: AdminService, session: Session) -> None:
    """Testni nofaol qilish faol ro'yxatdan chiqaradi, lekin qatorni saqlaydi (R14.4)."""
    test = admin.create_test(title="T", category="kognitiv", duration_minutes=10)
    session.commit()

    result = admin.delete_or_deactivate_test(test.id)
    session.commit()

    assert result is not None and result.is_active is False
    assert TestRepository(session).list_active() == []
    # Qator hali mavjud (yumshoq o'chirish).
    assert TestRepository(session).get_by_id(test.id) is not None


def test_hard_delete_test_removes_row(admin: AdminService, session: Session) -> None:
    """Qattiq o'chirish test qatorini bazadan olib tashlaydi (R14.4)."""
    test = admin.create_test(title="T", category="kognitiv", duration_minutes=10)
    session.commit()

    assert admin.delete_or_deactivate_test(test.id, hard_delete=True) is None
    session.commit()
    assert TestRepository(session).get_by_id(test.id) is None


def test_delete_test_missing_raises_not_found(admin: AdminService) -> None:
    with pytest.raises(NotFoundError):
        admin.delete_or_deactivate_test(999999)


# ---------------------------------------------------------------------------
# Question CRUD (R14.3, R14.6, R14.7)
# ---------------------------------------------------------------------------


def test_create_question_persists_with_answers(admin: AdminService, session: Session) -> None:
    """Yaroqli savol ball, kompetensiya va variantlari bilan saqlanadi (R14.3)."""
    test = admin.create_test(title="T", category="kompetensiya", duration_minutes=15)
    comp_id = _make_competency(session)
    session.commit()

    question = admin.create_question(
        test_id=test.id,
        question_text="Savol matni?",
        score="2.50",
        competency_id=comp_id,
        answers=_two_answers(),
        order_index=1,
    )
    session.commit()

    loaded = QuestionRepository(session).get_by_id(question.id)
    assert loaded is not None
    assert loaded.score == Decimal("2.50")
    assert loaded.competency_id == comp_id
    answers = AnswerRepository(session).list_for_question(question.id)
    assert len(answers) == 2
    assert {a.answer_text for a in answers} == {"Variant A", "Variant B"}


@pytest.mark.parametrize(
    "overrides, field",
    [
        ({"question_text": "   "}, "question_text"),
        ({"question_text": "x" * 1001}, "question_text"),
        ({"score": "0"}, "score"),
        ({"score": "0.001"}, "score"),
        ({"score": "1000.01"}, "score"),
        ({"score": "abc"}, "score"),
        ({"score": True}, "score"),
        ({"answers": [{"answer_text": "Yagona"}]}, "answers"),
        ({"answers": []}, "answers"),
        ({"answers": "notalist"}, "answers"),
    ],
)
def test_create_question_invalid_rejected_persists_nothing(
    admin: AdminService, session: Session, overrides: dict, field: str
) -> None:
    """Yaroqsiz savol rad etiladi, savol ham javoblar ham saqlanmaydi (R14.3, R14.6)."""
    test = admin.create_test(title="T", category="kompetensiya", duration_minutes=15)
    comp_id = _make_competency(session)
    session.commit()

    payload = {
        "test_id": test.id,
        "question_text": "Savol?",
        "score": "1.00",
        "competency_id": comp_id,
        "answers": _two_answers(),
    }
    payload.update(overrides)

    with pytest.raises(ValidationError) as exc:
        admin.create_question(**payload)
    assert exc.value.field == field
    session.rollback()
    assert QuestionRepository(session).list_for_test(test.id) == []


def test_create_question_missing_competency_raises_not_found(
    admin: AdminService, session: Session
) -> None:
    """Mavjud bo'lmagan kompetensiyaga bog'lash -> NotFoundError, saqlanmaydi (R14.7)."""
    test = admin.create_test(title="T", category="kompetensiya", duration_minutes=15)
    session.commit()

    with pytest.raises(NotFoundError):
        admin.create_question(
            test_id=test.id,
            question_text="Savol?",
            score="1.00",
            competency_id=424242,
            answers=_two_answers(),
        )
    session.rollback()
    assert QuestionRepository(session).list_for_test(test.id) == []


def test_create_question_score_boundaries_accepted(
    admin: AdminService, session: Session
) -> None:
    """Ball chegaralari (0.01 va 1000) qabul qilinadi (R14.3)."""
    test = admin.create_test(title="T", category="kompetensiya", duration_minutes=15)
    comp_id = _make_competency(session)
    session.commit()

    q_min = admin.create_question(
        test_id=test.id, question_text="Q1?", score=MIN_QUESTION_SCORE,
        competency_id=comp_id, answers=_two_answers(),
    )
    q_max = admin.create_question(
        test_id=test.id, question_text="Q2?", score=MAX_QUESTION_SCORE,
        competency_id=comp_id, answers=_two_answers(),
    )
    session.commit()
    assert q_min.score == Decimal("0.01")
    assert q_max.score == Decimal("1000.00")


def test_update_question_replaces_answers(admin: AdminService, session: Session) -> None:
    """Savolni yangilashda variantlar to'liq almashtiriladi (R14.3)."""
    test = admin.create_test(title="T", category="kompetensiya", duration_minutes=15)
    comp_id = _make_competency(session)
    session.commit()
    question = admin.create_question(
        test_id=test.id, question_text="Savol?", score="1.00",
        competency_id=comp_id, answers=_two_answers(),
    )
    session.commit()

    admin.update_question(
        question.id,
        question_text="Yangilangan?",
        answers=[
            {"answer_text": "C"},
            {"answer_text": "D"},
            {"answer_text": "E"},
        ],
    )
    session.commit()

    loaded = QuestionRepository(session).get_by_id(question.id)
    assert loaded.question_text == "Yangilangan?"
    answers = AnswerRepository(session).list_for_question(question.id)
    assert {a.answer_text for a in answers} == {"C", "D", "E"}


def test_update_question_invalid_competency_not_found(
    admin: AdminService, session: Session
) -> None:
    """Yangilashda mavjud bo'lmagan kompetensiya -> NotFoundError (R14.7)."""
    test = admin.create_test(title="T", category="kompetensiya", duration_minutes=15)
    comp_id = _make_competency(session)
    session.commit()
    question = admin.create_question(
        test_id=test.id, question_text="Savol?", score="1.00",
        competency_id=comp_id, answers=_two_answers(),
    )
    session.commit()

    with pytest.raises(NotFoundError):
        admin.update_question(question.id, competency_id=999999)


def test_delete_question_removes_question_and_answers(
    admin: AdminService, session: Session
) -> None:
    """Savolni o'chirish uni va javoblarini olib tashlaydi (R14.1)."""
    test = admin.create_test(title="T", category="kompetensiya", duration_minutes=15)
    comp_id = _make_competency(session)
    session.commit()
    question = admin.create_question(
        test_id=test.id, question_text="Savol?", score="1.00",
        competency_id=comp_id, answers=_two_answers(),
    )
    session.commit()

    admin.delete_question(question.id)
    session.commit()

    assert QuestionRepository(session).get_by_id(question.id) is None
    assert AnswerRepository(session).list_for_question(question.id) == []


# ---------------------------------------------------------------------------
# Competency CRUD + referensial yaxlitlik (R14.1, R14.8)
# ---------------------------------------------------------------------------


def test_competency_crud_round_trip(admin: AdminService, session: Session) -> None:
    """Kompetensiya yaratiladi, yangilanadi va o'chiriladi (R14.1)."""
    comp = admin.create_competency(name="Pedagogik", description="d")
    session.commit()

    admin.update_competency(comp.id, name="Pedagogik (yangi)")
    session.commit()
    assert CompetencyRepository(session).get_by_id(comp.id).name == "Pedagogik (yangi)"

    admin.delete_competency(comp.id)
    session.commit()
    assert CompetencyRepository(session).get_by_id(comp.id) is None


def test_delete_used_competency_rejected(admin: AdminService, session: Session) -> None:
    """Ishlatilayotgan kompetensiyani o'chirish rad etiladi (R14.8)."""
    test = admin.create_test(title="T", category="kompetensiya", duration_minutes=15)
    comp = admin.create_competency(name="Innovatsiya")
    session.commit()
    admin.create_question(
        test_id=test.id, question_text="Savol?", score="1.00",
        competency_id=comp.id, answers=_two_answers(),
    )
    session.commit()

    with pytest.raises(ConflictError):
        admin.delete_competency(comp.id)
    session.rollback()
    # Kompetensiya hali mavjud (o'chirilmagan).
    assert CompetencyRepository(session).get_by_id(comp.id) is not None


def test_delete_competency_missing_raises_not_found(admin: AdminService) -> None:
    with pytest.raises(NotFoundError):
        admin.delete_competency(999999)


def test_create_competency_invalid_name_rejected(admin: AdminService, session: Session) -> None:
    with pytest.raises(ValidationError):
        admin.create_competency(name="   ")
    session.rollback()
    assert CompetencyRepository(session).list_all() == []


# ---------------------------------------------------------------------------
# Recommendation CRUD (R14.1)
# ---------------------------------------------------------------------------


def test_recommendation_crud_round_trip(admin: AdminService, session: Session) -> None:
    """Tavsiya yaratiladi (standart va aniq), yangilanadi va o'chiriladi (R14.1)."""
    comp = admin.create_competency(name="Strategik")
    session.commit()

    general = admin.create_recommendation(text="Umumiy tavsiya")
    specific = admin.create_recommendation(
        text="Aniq tavsiya", competency_id=comp.id, level="Past"
    )
    session.commit()
    assert general.competency_id is None
    assert specific.competency_id == comp.id and specific.level == "Past"

    admin.update_recommendation(specific.id, text="Yangilangan", level="O'rta")
    session.commit()
    from app.repositories.recommendations import RecommendationRepository

    repo = RecommendationRepository(session)
    assert repo.get_by_id(specific.id).text == "Yangilangan"
    assert repo.get_by_id(specific.id).level == "O'rta"

    admin.delete_recommendation(general.id)
    session.commit()
    assert repo.get_by_id(general.id) is None


def test_create_recommendation_missing_competency_not_found(
    admin: AdminService, session: Session
) -> None:
    """Mavjud bo'lmagan kompetensiyaga tavsiya -> NotFoundError (R14.7)."""
    with pytest.raises(NotFoundError):
        admin.create_recommendation(text="x", competency_id=999999)


def test_create_recommendation_empty_text_rejected(admin: AdminService) -> None:
    with pytest.raises(ValidationError):
        admin.create_recommendation(text="   ")
