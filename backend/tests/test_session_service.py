"""SessionService uchun unit testlar (task 11.1 va 11.4, R7, R8.6).

Diagnostika_Moduli (SessionService) ning sessiya hayot siklini
(``start_session``, ``auto_finish``) va topshirish + baholash integratsiyasini
(``submit_session``) in-memory SQLite engine ustida tekshiradi
(`Base.metadata.create_all`). Mock'siz: real repository, ORM modellari va sof
domen scoring funksiyasi ishlatiladi.

Bog'liq talablar:
- R7.1, R7.10: sessiya boshlash idempotentligi (yangi yoki mavjudini davom ettirish).
- R7.5: muddat tugaganda avtomatik yakunlash, javobsizlarni belgilash.
- R7.6, R8.6: topshirish javoblarni saqlaydi, baholaydi va natijani saqlaydi.
- R7.7: takroriy topshirish rad etiladi (ConflictError).
- R7.8: muddat tugamagan + javobsiz savol -> ValidationError.
- R7.9: begona/yo'q sessiya -> NotFoundError.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (modellarni metadata'ga ro'yxatdan o'tkazadi)
from app.core.db import create_db_engine
from app.models.base import Base
from app.models.content import Answer, Question, Test
from app.models.reference import Competency
from app.repositories.results import ResultRepository
from app.repositories.sessions import SessionRepository
from app.services.errors import ConflictError, NotFoundError, ValidationError
from app.services.session_service import (
    DEFAULT_RETAKE_INTERVAL_DAYS,
    SessionService,
)

USER_ID = 1
OTHER_USER_ID = 2
NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


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


def _service(session: Session, **kwargs) -> SessionService:
    """Deterministik ``now`` bilan SessionService quradi."""
    kwargs.setdefault("now_provider", lambda: NOW)
    return SessionService(session, **kwargs)


def _make_test(
    session: Session,
    *,
    title: str = "Test",
    category: str | None = "kognitiv",
    duration_minutes: int | None = 30,
    is_active: bool = True,
) -> Test:
    test = Test(
        title=title,
        category=category,
        description="desc",
        duration_minutes=duration_minutes,
        is_active=is_active,
    )
    session.add(test)
    session.flush()
    return test


def _make_competency(session: Session, name: str) -> Competency:
    comp = Competency(name=name)
    session.add(comp)
    session.flush()
    return comp


def _make_question(
    session: Session,
    *,
    test_id: int,
    text: str,
    order_index: int,
    score: str = "10.00",
    competency_id: int | None = None,
    question_type: str = "cognitive",
) -> Question:
    q = Question(
        test_id=test_id,
        question_text=text,
        score=Decimal(score),
        order_index=order_index,
        competency_id=competency_id,
        question_type=question_type,
    )
    session.add(q)
    session.flush()
    return q


def _make_answer(
    session: Session,
    *,
    question_id: int,
    text: str,
    is_correct: bool = False,
    score: str | None = None,
) -> Answer:
    a = Answer(
        question_id=question_id,
        answer_text=text,
        is_correct=is_correct,
        score=Decimal(score) if score is not None else None,
    )
    session.add(a)
    session.flush()
    return a


# ---------------------------------------------------------------------------
# start_session (R7.1, R7.10)
# ---------------------------------------------------------------------------


def test_start_session_creates_new_with_started_and_expiry(session: Session) -> None:
    """Tugatilmagan sessiya yo'q bo'lsa, started_at va expires_at qayd etiladi (R7.1)."""
    test = _make_test(session, duration_minutes=30)
    session.commit()

    created = _service(session).start_session(USER_ID, test.id)

    assert created.id is not None
    assert created.status == "in_progress"
    assert created.user_id == USER_ID
    assert created.test_id == test.id
    # expires_at = started_at + duration.
    assert created.started_at is not None
    assert created.expires_at is not None
    delta = created.expires_at - created.started_at
    assert delta == timedelta(minutes=30)


def test_start_session_returns_existing_when_in_progress(session: Session) -> None:
    """Tugatilmagan sessiya mavjud bo'lsa, yangisi yaratilmaydi (R7.10)."""
    test = _make_test(session)
    session.commit()
    svc = _service(session)

    first = svc.start_session(USER_ID, test.id)
    second = svc.start_session(USER_ID, test.id)

    assert first.id == second.id
    # DB'da faqat bitta sessiya bo'lishi kerak.
    all_sessions = session.query(type(first)).all()
    assert len(all_sessions) == 1


def test_start_session_no_duration_has_no_expiry(session: Session) -> None:
    """Davomiyligi belgilanmagan testda expires_at None (R7.1)."""
    test = _make_test(session, duration_minutes=None)
    session.commit()

    created = _service(session).start_session(USER_ID, test.id)

    assert created.expires_at is None


def test_start_session_missing_test_raises_not_found(session: Session) -> None:
    """Mavjud bo'lmagan test -> NotFoundError (R6.4)."""
    with pytest.raises(NotFoundError):
        _service(session).start_session(USER_ID, 999999)


def test_start_session_inactive_test_raises_not_found(session: Session) -> None:
    """Faol bo'lmagan test -> NotFoundError (R6.4)."""
    test = _make_test(session, is_active=False)
    session.commit()

    with pytest.raises(NotFoundError):
        _service(session).start_session(USER_ID, test.id)


# ---------------------------------------------------------------------------
# auto_finish (R7.5)
# ---------------------------------------------------------------------------


def test_auto_finish_marks_completed_and_unanswered(session: Session) -> None:
    """Muddat tugaganda yakunlanadi va javobsizlar answered=false belgilanadi (R7.5)."""
    test = _make_test(session, duration_minutes=10)
    q1 = _make_question(session, test_id=test.id, text="Q1", order_index=1)
    q2 = _make_question(session, test_id=test.id, text="Q2", order_index=2)
    a1 = _make_answer(session, question_id=q1.id, text="A1", is_correct=True)
    session.commit()

    svc = _service(session)
    sess = svc.start_session(USER_ID, test.id)

    # q1 ga javob beramiz, q2 javobsiz qoladi.
    SessionRepository(session).upsert_answer(
        session_id=sess.id,
        question_id=q1.id,
        selected_answer_id=a1.id,
        answered=True,
    )
    session.commit()

    later = NOW + timedelta(minutes=20)
    svc.auto_finish(sess, now=later)

    assert sess.status == "completed"
    # SQLite ``DateTime(timezone=True)`` round-trip'da tzinfo tushib qolishi
    # mumkin; taqqoslashni naive UTC ustida bajaramiz.
    assert sess.completed_at is not None
    assert sess.completed_at.replace(tzinfo=None) == later.replace(tzinfo=None)
    answers = {a.question_id: a for a in SessionRepository(session).list_answers(sess.id)}
    assert answers[q1.id].answered is True
    assert answers[q2.id].answered is False


def test_auto_finish_idempotent_on_completed(session: Session) -> None:
    """Allaqachon yakunlangan sessiyada hech narsa o'zgartirmaydi (R7.5)."""
    test = _make_test(session, duration_minutes=10)
    _make_question(session, test_id=test.id, text="Q1", order_index=1)
    session.commit()

    svc = _service(session)
    sess = svc.start_session(USER_ID, test.id)
    later = NOW + timedelta(minutes=20)
    svc.auto_finish(sess, now=later)
    first_completed_at = sess.completed_at

    # Ikkinchi marta — completed_at o'zgarmaydi.
    even_later = NOW + timedelta(minutes=40)
    svc.auto_finish(sess, now=even_later)
    assert sess.completed_at == first_completed_at


# ---------------------------------------------------------------------------
# submit_session — muvaffaqiyatli baholash va saqlash (R7.6, R8.6)
# ---------------------------------------------------------------------------


def test_submit_session_scores_and_persists_result(session: Session) -> None:
    """To'liq javob: natija hisoblanadi va saqlanadi (R7.6, R8.6)."""
    test = _make_test(session, duration_minutes=30)
    comp = _make_competency(session, "Boshqaruv")
    q1 = _make_question(
        session, test_id=test.id, text="Q1", order_index=1,
        score="10.00", competency_id=comp.id,
    )
    q2 = _make_question(
        session, test_id=test.id, text="Q2", order_index=2,
        score="10.00", competency_id=comp.id,
    )
    correct1 = _make_answer(session, question_id=q1.id, text="to'g'ri", is_correct=True)
    _make_answer(session, question_id=q1.id, text="xato", is_correct=False)
    correct2 = _make_answer(session, question_id=q2.id, text="to'g'ri", is_correct=True)
    wrong2 = _make_answer(session, question_id=q2.id, text="xato", is_correct=False)
    session.commit()

    svc = _service(session)
    sess = svc.start_session(USER_ID, test.id)

    # q1 to'g'ri, q2 xato -> 10/20 = 50%.
    outcome = svc.submit_session(
        USER_ID,
        sess.id,
        [
            {"question_id": q1.id, "answer_id": correct1.id},
            {"question_id": q2.id, "answer_id": wrong2.id},
        ],
        now=NOW + timedelta(minutes=5),
    )

    assert outcome.result_id is not None
    assert outcome.score.total_score == Decimal("10")
    assert outcome.score.max_score == Decimal("20")
    assert outcome.score.percentage == Decimal("50.00")
    assert str(outcome.score.level) == "O'rta"

    # Sessiya yakunlangan.
    assert sess.status == "completed"

    # Round-trip: natija DB'da saqlangan (R8.6).
    stored = ResultRepository(session).get_by_id(outcome.result_id)
    assert stored is not None
    assert stored.user_id == USER_ID
    assert stored.test_id == test.id
    assert stored.percentage == Decimal("50.00")
    assert stored.level == "O'rta"
    # next_retake_date hisoblangan (R8.4).
    assert stored.next_retake_date == (NOW.date() + timedelta(days=DEFAULT_RETAKE_INTERVAL_DAYS))
    # Kompetensiya natijasi saqlangan (R8.3, R8.6).
    comp_results = {c.competency_id: c for c in stored.competency_results}
    assert comp.id in comp_results
    assert comp_results[comp.id].percentage == Decimal("50.00")
    # Foydalanuvchiga correct2 ko'rsatildimi - bu test logikasi uchun emas.
    assert correct2.id is not None


def test_submit_session_likert_scoring(session: Session) -> None:
    """Likert javob ``max*value/5`` formulasi bilan baholanadi (R7.3 mapping)."""
    test = _make_test(session, duration_minutes=30)
    comp = _make_competency(session, "Reflexiya")
    q = _make_question(
        session, test_id=test.id, text="L1", order_index=1,
        score="10.00", competency_id=comp.id, question_type="likert",
    )
    session.commit()

    svc = _service(session)
    sess = svc.start_session(USER_ID, test.id)

    # likert_value=4 -> 10 * 4/5 = 8.00 -> 80%.
    outcome = svc.submit_session(
        USER_ID,
        sess.id,
        [{"question_id": q.id, "likert_value": 4}],
        now=NOW + timedelta(minutes=1),
    )

    assert outcome.score.total_score == Decimal("8.00")
    assert outcome.score.percentage == Decimal("80.00")
    assert str(outcome.score.level) == "Yaxshi"


def test_submit_session_uses_answer_specific_score(session: Session) -> None:
    """Tanlangan variantda aniq ``score`` bo'lsa, o'sha ball ishlatiladi."""
    test = _make_test(session, duration_minutes=30)
    q = _make_question(
        session, test_id=test.id, text="Q", order_index=1, score="10.00",
    )
    partial = _make_answer(
        session, question_id=q.id, text="qisman", is_correct=False, score="6.00"
    )
    session.commit()

    svc = _service(session)
    sess = svc.start_session(USER_ID, test.id)

    outcome = svc.submit_session(
        USER_ID,
        sess.id,
        [{"question_id": q.id, "answer_id": partial.id}],
        now=NOW + timedelta(minutes=1),
    )

    # 6/10 = 60%.
    assert outcome.score.total_score == Decimal("6.00")
    assert outcome.score.percentage == Decimal("60.00")


# ---------------------------------------------------------------------------
# submit_session — idempotentlik (R7.7)
# ---------------------------------------------------------------------------


def test_submit_session_resubmission_rejected(session: Session) -> None:
    """Allaqachon topshirilgan sessiyaga qayta topshirish rad etiladi (R7.7)."""
    test = _make_test(session, duration_minutes=30)
    q = _make_question(session, test_id=test.id, text="Q", order_index=1, score="10.00")
    correct = _make_answer(session, question_id=q.id, text="t", is_correct=True)
    session.commit()

    svc = _service(session)
    sess = svc.start_session(USER_ID, test.id)
    first = svc.submit_session(
        USER_ID, sess.id, [{"question_id": q.id, "answer_id": correct.id}],
        now=NOW + timedelta(minutes=1),
    )

    with pytest.raises(ConflictError):
        svc.submit_session(
            USER_ID, sess.id, [{"question_id": q.id, "answer_id": correct.id}],
            now=NOW + timedelta(minutes=2),
        )

    # Faqat bitta natija saqlangan (dastlabki o'zgarmagan).
    assert ResultRepository(session).get_by_session(sess.id).id == first.result_id


# ---------------------------------------------------------------------------
# submit_session — to'liqsiz va begona sessiya (R7.8, R7.9)
# ---------------------------------------------------------------------------


def test_submit_session_incomplete_not_timed_out_rejected(session: Session) -> None:
    """Muddat tugamagan + javobsiz savol -> ValidationError, hech narsa saqlanmaydi (R7.8)."""
    test = _make_test(session, duration_minutes=30)
    q1 = _make_question(session, test_id=test.id, text="Q1", order_index=1, score="10.00")
    q2 = _make_question(session, test_id=test.id, text="Q2", order_index=2, score="10.00")
    a1 = _make_answer(session, question_id=q1.id, text="t", is_correct=True)
    session.commit()

    svc = _service(session)
    sess = svc.start_session(USER_ID, test.id)

    with pytest.raises(ValidationError) as exc:
        svc.submit_session(
            USER_ID, sess.id, [{"question_id": q1.id, "answer_id": a1.id}],
            now=NOW + timedelta(minutes=5),  # muddat tugamagan
        )
    assert getattr(exc.value, "field", None) == "answers"

    session.rollback()
    # Natija saqlanmagan.
    assert ResultRepository(session).get_by_session(sess.id) is None
    # Sessiya hali in_progress.
    refreshed = SessionRepository(session).get_by_id(sess.id)
    assert refreshed.status == "in_progress"
    assert q2.id is not None


def test_submit_session_timed_out_accepts_partial(session: Session) -> None:
    """Muddat tugagan bo'lsa qisman javoblar qabul qilinadi (R7.5, R7.8 istisno)."""
    test = _make_test(session, duration_minutes=10)
    q1 = _make_question(session, test_id=test.id, text="Q1", order_index=1, score="10.00")
    q2 = _make_question(session, test_id=test.id, text="Q2", order_index=2, score="10.00")
    a1 = _make_answer(session, question_id=q1.id, text="t", is_correct=True)
    session.commit()

    svc = _service(session)
    sess = svc.start_session(USER_ID, test.id)

    # Muddat tugagan (start + 10 min < now).
    outcome = svc.submit_session(
        USER_ID, sess.id, [{"question_id": q1.id, "answer_id": a1.id}],
        now=NOW + timedelta(minutes=15),
    )

    # q1 to'g'ri (10), q2 javobsiz (0) -> 10/20 = 50%.
    assert outcome.score.percentage == Decimal("50.00")
    # q2 javobsiz belgilangan.
    answers = {a.question_id: a for a in SessionRepository(session).list_answers(sess.id)}
    assert answers[q2.id].answered is False


def test_submit_session_unknown_session_raises_not_found(session: Session) -> None:
    """Mavjud bo'lmagan sessiya -> NotFoundError (R7.9)."""
    with pytest.raises(NotFoundError):
        _service(session).submit_session(USER_ID, 999999, [], now=NOW)


def test_submit_session_foreign_session_raises_not_found(session: Session) -> None:
    """Boshqa foydalanuvchining sessiyasiga topshirish -> NotFoundError (R7.9)."""
    test = _make_test(session, duration_minutes=30)
    _make_question(session, test_id=test.id, text="Q", order_index=1, score="10.00")
    session.commit()

    svc = _service(session)
    sess = svc.start_session(USER_ID, test.id)

    with pytest.raises(NotFoundError):
        svc.submit_session(OTHER_USER_ID, sess.id, [], now=NOW + timedelta(minutes=1))


# ---------------------------------------------------------------------------
# on_result_created seam (R10.1)
# ---------------------------------------------------------------------------


def test_submit_session_invokes_on_result_created_hook(session: Session) -> None:
    """``on_result_created`` callback natija bilan chaqiriladi (R10.1 seam)."""
    test = _make_test(session, duration_minutes=30)
    q = _make_question(session, test_id=test.id, text="Q", order_index=1, score="10.00")
    correct = _make_answer(session, question_id=q.id, text="t", is_correct=True)
    session.commit()

    captured = []
    svc = _service(session, on_result_created=captured.append)
    sess = svc.start_session(USER_ID, test.id)

    outcome = svc.submit_session(
        USER_ID, sess.id, [{"question_id": q.id, "answer_id": correct.id}],
        now=NOW + timedelta(minutes=1),
    )

    assert len(captured) == 1
    assert captured[0].id == outcome.result_id
