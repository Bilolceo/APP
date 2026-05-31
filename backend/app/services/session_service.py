"""Diagnostika_Moduli — SessionService (R7, R8.6).

Test sessiyasi hayot siklini va baholash (Baholash_Moduli) integratsiyasini
biznes-mantiq darajasida birlashtiradi. Servis sof **framework'dan mustaqil**
(FastAPI/HTTP haqida hech narsa bilmaydi): konstruktorda SQLAlchemy ``Session``
oladi, ma'lumotlarga repository qatlami orqali kiradi va ball hisoblashni sof
domen funksiyasi (``app.domain.scoring.build_result``) orqali bajaradi.

Mas'uliyat (design.md — "Diagnostika_Moduli (TestService / SessionService)"):

- ``start_session(user_id, test_id)`` — tugatilmagan sessiya bo'lmasa yangi
  yaratadi (``started_at`` va ``expires_at = started_at + duration`` qayd
  etiladi); mavjud bo'lsa yangisini yaratmasdan mavjudini qaytaradi
  (R7.1, R7.10). Test mavjud/faol bo'lmasa ``NotFoundError`` (R6.4).
- ``auto_finish(session, now)`` — muddat tugaganda sessiyani yakunlaydi, mavjud
  javoblarni qabul qiladi va javob berilmagan savollarni ``answered=false``
  holatida belgilaydi (R7.5).
- ``submit_session(user_id, session_id, answers, now)`` — javoblarni saqlaydi,
  sessiyani yakunlaydi, domen scoring funksiyasini chaqiradi va natijani
  (`test_results` + `competency_results`) saqlaydi (R7.6, R8.6); takroriy
  topshirishni rad etadi (idempotent — R7.7); muddat tugamagan holda javobsiz
  savol bo'lsa rad etadi (R7.8); begona/yo'q sessiya ``NotFoundError`` (R7.9).

Tavsiyalarni ulash seami (R10.1 — parallel quriladigan RecommendationService):
SessionService ``RecommendationService`` ga **qattiq bog'lanmaydi**. Buning
o'rniga konstruktorda ixtiyoriy ``on_result_created`` callback qabul qilinadi.
Router/integratsiya qatlami uni ``RecommendationService.assign_recommendations``
ga ulashi mumkin. Callback natija saqlangach, ammo ``commit`` dan oldin
chaqiriladi — shu sababli tavsiyalar natija bilan bitta tranzaksiyada saqlanadi.

Awarded-score (yig'ilgan ball) mantig'i — quyidagi taxminlar ``design.md`` ning
"Scoring Algoritmi" bo'limiga muvofiq (har bir savol ``max_score = question.score``):

- **Variant tanlash (cognitive/situational):** tanlangan ``answers`` yozuvida
  aniq ``score`` bo'lsa — o'sha ball; aks holda ``is_correct`` bo'lsa to'liq
  savol balli, bo'lmasa 0 ("award score per correct option" — R8.1).
- **Likert (reflexiv):** ``awarded = question.score * likert_value / 5``
  (``likert_value`` ∈ 1..5; 5 -> to'liq ball), 2 kasr xonasigacha half-up.
- **Javobsiz savol** (``answered=false``): 0 ball, lekin maksimal ballga kiradi.

Har bir savol uchun yig'ilgan ball ``[0, max_score]`` oralig'iga qisiladi (clamp)
— bu umumiy foiz 0–100 oralig'ida qolishini kafolatlaydi (R8.1, DB CHECK).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.domain.scoring import build_result
from app.domain.types import AnsweredQuestion, ScoreResult
from app.models.content import Question
from app.models.result import TestResult
from app.models.session import SessionAnswer, TestSession
from app.repositories.results import ResultRepository
from app.repositories.sessions import SessionRepository
from app.repositories.tests import TestRepository
from app.services.errors import ConflictError, NotFoundError, ValidationError

#: Likert shkalasi maksimal qiymati (1..5; 5 -> to'liq ball) — R7.3.
LIKERT_MAX = Decimal(5)

#: 2 kasr xonasigacha yaxlitlash birligi (NUMERIC(_,2)) — R8.1.
_CENTS = Decimal("0.01")

_ZERO = Decimal("0")

#: Keyingi qayta topshirish sanasi uchun standart oraliq (kun) — R8.4.
#: ~3 oy. Konfiguratsiya qilinadi: konstruktordagi ``retake_interval_days``
#: orqali boshqa qiymat berilishi mumkin (masalan, sozlamalardan).
DEFAULT_RETAKE_INTERVAL_DAYS = 90


@dataclass(frozen=True)
class SubmissionOutcome:
    """``submit_session`` natijasi: saqlangan natija identifikatori + ball.

    Maydonlar:
    - ``result_id``: saqlangan ``test_results`` yozuvi identifikatori (R8.6).
    - ``score``: sof domen :class:`ScoreResult` (umumiy ball, foiz, daraja,
      kompetensiya ballari, kuchli/zaif tomonlar).
    """

    result_id: int
    score: ScoreResult


def _to_decimal(value: Decimal | int | float | str) -> Decimal:
    """Kirishni xavfsiz ``Decimal`` ga keltiradi (``float`` -> ``str`` orqali)."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def _to_naive_utc(value: datetime) -> datetime:
    """``datetime`` ni taqqoslash uchun UTC-naive ko'rinishga keltiradi.

    SQLite ``DateTime(timezone=True)`` ustunidan ba'zan tzinfo'siz (naive)
    qiymat qaytaradi, tarmoq/servis qatlamida esa tz-aware UTC ishlatiladi.
    Taqqoslashda ``TypeError`` (aware vs naive) bo'lmasligi uchun ikkala
    tomonni ham bir xil (UTC-naive) shaklga keltiramiz.
    """
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _question_sort_key(question: Question) -> tuple[bool, int, int]:
    """Savollarni ``order_index`` (None oxirida), so'ng ``id`` bo'yicha tartiblaydi."""
    order_index = question.order_index
    return (order_index is None, order_index or 0, question.id)


def _get(item: Mapping[str, Any] | Any, key: str) -> Any:
    """``item`` (Mapping yoki obyekt) dan ``key`` qiymatini oladi (yo'q -> None)."""
    if isinstance(item, Mapping):
        return item.get(key)
    return getattr(item, key, None)


class SessionService:
    """Test sessiyasi hayot sikli va baholash integratsiyasi (R7, R8.6).

    Args:
        session: faol SQLAlchemy ``Session``. Servis o'z yozuvlarini ushbu
            sessiyada ``commit`` qiladi (tranzaksiya chegarasi shu yerda).
        now_provider: joriy UTC vaqtni qaytaruvchi funksiya (deterministik
            testlar uchun in'ektsiya qilinadi). ``None`` bo'lsa
            ``datetime.now(timezone.utc)`` ishlatiladi.
        retake_interval_days: keyingi qayta topshirish sanasi uchun oraliq
            (kun). Standart :data:`DEFAULT_RETAKE_INTERVAL_DAYS` (R8.4).
        on_result_created: ixtiyoriy callback — natija saqlangach (``commit``
            dan oldin) chaqiriladi. Router uni
            ``RecommendationService.assign_recommendations`` ga ulashi mumkin
            (R10.1 seam). Imzo: ``(result: TestResult) -> Any``.
    """

    def __init__(
        self,
        session: Session,
        *,
        now_provider: Callable[[], datetime] | None = None,
        retake_interval_days: int = DEFAULT_RETAKE_INTERVAL_DAYS,
        on_result_created: Callable[[TestResult], Any] | None = None,
    ) -> None:
        self.session = session
        self.sessions = SessionRepository(session)
        self.tests = TestRepository(session)
        self.results = ResultRepository(session)
        self._now_provider = now_provider or self._default_now
        self._retake_interval_days = retake_interval_days
        self._on_result_created = on_result_created

    # ------------------------------------------------------------------
    # Yordamchilar
    # ------------------------------------------------------------------

    @staticmethod
    def _default_now() -> datetime:
        return datetime.now(timezone.utc)

    def _now(self) -> datetime:
        return self._now_provider()

    @staticmethod
    def is_expired(session_obj: TestSession, now: datetime) -> bool:
        """Sessiya muddati ``now`` ga kelib tugaganligini tekshiradi (R7.5).

        ``expires_at`` ``None`` (davomiyligi belgilanmagan test) bo'lsa sessiya
        hech qachon avtomatik tugamaydi -> ``False``.
        """
        if session_obj.expires_at is None:
            return False
        return _to_naive_utc(now) >= _to_naive_utc(session_obj.expires_at)

    # ------------------------------------------------------------------
    # R7.1, R7.10 — sessiyani boshlash / davom ettirish
    # ------------------------------------------------------------------

    def start_session(
        self, user_id: int, test_id: int, *, now: datetime | None = None
    ) -> TestSession:
        """Test sessiyasini boshlaydi yoki mavjud tugatilmaganini qaytaradi (R7.1, R7.10).

        - Tugatilmagan (``in_progress``) sessiya **mavjud bo'lmasa**: yangi
          sessiya yaratiladi; ``started_at = now`` va (test davomiyligi
          belgilangan bo'lsa) ``expires_at = started_at + duration_minutes``
          qayd etiladi (R7.1).
        - Tugatilmagan sessiya **mavjud bo'lsa**: yangi sessiya yaratilmaydi va
          mavjud sessiya qaytariladi (R7.10) — boshlashning idempotentligi.

        Args:
            user_id: sessiyani boshlayotgan foydalanuvchi.
            test_id: boshlanayotgan test.
            now: (ixtiyoriy) joriy vaqt; ``None`` bo'lsa ``now_provider``.

        Returns:
            Yangi yoki mavjud ``in_progress`` ``TestSession``.

        Raises:
            NotFoundError: test mavjud emas yoki faol emas (R6.4).
        """
        now = now or self._now()

        test = self.tests.get_by_id(test_id)
        if test is None or not test.is_active:
            raise NotFoundError("Test topilmadi")

        existing = self.sessions.get_active(user_id, test_id)
        if existing is not None:
            # R7.10 — mavjud tugatilmagan sessiyani davom ettirish.
            return existing

        expires_at: datetime | None = None
        if test.duration_minutes is not None:
            expires_at = now + timedelta(minutes=test.duration_minutes)

        created = self.sessions.create(
            user_id=user_id,
            test_id=test_id,
            started_at=now,
            expires_at=expires_at,
        )
        self.session.commit()
        return created

    # ------------------------------------------------------------------
    # R7.5 — muddat tugaganda avtomatik yakunlash
    # ------------------------------------------------------------------

    def auto_finish(
        self, session_obj: TestSession, *, now: datetime
    ) -> TestSession:
        """Muddati tugagan sessiyani avtomatik yakunlaydi (R7.5).

        Mavjud javoblar saqlanib qoladi ("topshirish uchun qabul qilinadi");
        savol-javob yozuvi bo'lmagan savollar ``answered=false`` holatida
        belgilanadi; sessiya ``completed`` holatiga o'tkaziladi.

        Amal idempotent: allaqachon ``completed`` bo'lgan sessiyada hech narsa
        o'zgartirmaydi. Ball hisoblash bu yerda bajarilmaydi — u
        :meth:`submit_session` zimmasida (auto-yakunlangan sessiya keyinchalik
        topshirilganda baholanadi; natija ``session_id`` UNIQUE bo'lgani uchun
        bir marta saqlanadi).

        Args:
            session_obj: yakunlanadigan sessiya.
            now: joriy vaqt (deterministik; ``completed_at`` shu qiymat bo'ladi).

        Returns:
            Yakunlangan ``TestSession``.
        """
        if session_obj.status == "completed":
            return session_obj

        self._ensure_unanswered_marked(session_obj)
        self.sessions.complete(session_obj, completed_at=now)
        self.session.commit()
        return session_obj

    # ------------------------------------------------------------------
    # R7.6, R7.7, R7.8, R7.9, R8.6 — topshirish va baholash
    # ------------------------------------------------------------------

    def submit_session(
        self,
        user_id: int,
        session_id: int,
        answers: Iterable[Mapping[str, Any] | Any],
        *,
        now: datetime,
    ) -> SubmissionOutcome:
        """Sessiyani topshiradi, baholaydi va natijani saqlaydi (R7.6–R7.9, R8.6).

        Oqim:

        1. Sessiya mavjud va so'rovchiga tegishli ekanini tekshiradi; aks holda
           ``NotFoundError`` (R7.9).
        2. Idempotentlik (R7.7): sessiya uchun natija allaqachon saqlangan
           bo'lsa, ``ConflictError`` (saqlangan javoblar/natija o'zgarmaydi).
        3. Muddat tugamagan bo'lsa-yu, javob berilmagan savollar mavjud bo'lsa,
           hech narsa saqlamasdan ``ValidationError`` (R7.8). Muddat tugagan
           bo'lsa (R7.5), qisman javoblar qabul qilinadi.
        4. Javoblarni saqlaydi (upsert), javobsizlarni ``answered=false`` qiladi,
           sessiyani ``completed`` holatiga o'tkazadi.
        5. Sof domen ``build_result`` ni chaqiradi va ``test_results`` +
           ``competency_results`` ni saqlaydi (R8.6); keyingi qayta topshirish
           sanasini hisoblaydi (R8.4).
        6. ``on_result_created`` callback (agar berilgan bo'lsa) chaqiriladi
           (R10.1 seam), so'ng ``commit``.

        Args:
            user_id: topshirayotgan foydalanuvchi.
            session_id: topshirilayotgan sessiya.
            answers: ``{question_id, answer_id|selected_answer_id?, likert_value?}``
                ko'rinishidagi javoblar (Mapping yoki obyekt).
            now: joriy vaqt (deterministik).

        Returns:
            :class:`SubmissionOutcome` — natija identifikatori va ball.

        Raises:
            NotFoundError: sessiya yo'q yoki so'rovchiga tegishli emas (R7.9).
            ConflictError: sessiya allaqachon topshirilgan (R7.7).
            ValidationError: muddat tugamagan, javobsiz savollar bor (R7.8).
        """
        session_obj = self.sessions.get_by_id(session_id)
        # R7.9 — mavjud emas yoki begona sessiya: bir xil "topilmadi" (egalikni
        # oshkor qilmaslik uchun ham 404).
        if session_obj is None or session_obj.user_id != user_id:
            raise NotFoundError("Sessiya topilmadi")

        # R7.7 — idempotentlik: natija allaqachon saqlangan bo'lsa, takroriy
        # topshirish rad etiladi (saqlangan javoblar va natija o'zgarmaydi).
        if self.results.get_by_session(session_id) is not None:
            raise ConflictError(
                "Sessiya allaqachon yakunlangan",
                code="already_submitted",
            )

        test = self.tests.get_with_questions(session_obj.test_id)
        if test is None:
            raise NotFoundError("Test topilmadi")

        questions = sorted(test.questions, key=_question_sort_key)
        valid_qids = {q.id for q in questions}
        provided = self._normalize_answers(answers, valid_qids)
        existing_answers = {
            a.question_id: a for a in self.sessions.list_answers(session_id)
        }

        timed_out = self.is_expired(session_obj, now)

        # R7.8 — muddat tugamagan + javobsiz savol bor -> hech narsa saqlamasdan
        # rad etish. (Muddat tugagan bo'lsa qisman javob qabul qilinadi — R7.5.)
        if not timed_out:
            unanswered = [
                q.id
                for q in questions
                if not self._is_answered(q.id, provided, existing_answers)
            ]
            if unanswered:
                raise ValidationError(
                    "Javob berilmagan savollar mavjud",
                    field="answers",
                    code="incomplete_submission",
                    details={"unanswered": unanswered},
                )

        # 4 — javoblarni saqlash (upsert) va javobsizlarni belgilash.
        for question in questions:
            if question.id in provided:
                selected_answer_id, likert_value = provided[question.id]
                self.sessions.upsert_answer(
                    session_id=session_id,
                    question_id=question.id,
                    selected_answer_id=selected_answer_id,
                    likert_value=likert_value,
                    answered=True,
                )
            elif question.id not in existing_answers:
                # Javobsiz savol (muddat tugagan yo'l yoki umuman javobsiz) — R7.5.
                self.sessions.upsert_answer(
                    session_id=session_id,
                    question_id=question.id,
                    selected_answer_id=None,
                    likert_value=None,
                    answered=False,
                )

        # 5 — yakuniy javob holatini o'qib, baholash uchun AnsweredQuestion qurish.
        final_answers = {
            a.question_id: a for a in self.sessions.list_answers(session_id)
        }
        answered_questions = [
            self._to_answered_question(q, final_answers.get(q.id))
            for q in questions
        ]
        score = build_result(answered_questions)

        # Sessiyani yakunlash (auto_finish allaqachon yakunlagan bo'lishi mumkin).
        if session_obj.status != "completed":
            self.sessions.complete(session_obj, completed_at=now)

        # 5 — natijani kompetensiya natijalari bilan saqlash (R8.6).
        competency_rows: list[dict[str, object]] = [
            {
                "competency_id": comp.competency_id,
                "score": comp.score if comp.score is not None else _ZERO,
                "max_score": comp.max_score if comp.max_score is not None else _ZERO,
                "percentage": comp.percentage,
            }
            for comp in score.competencies
        ]
        next_retake_date = self._compute_next_retake_date(now)

        result = self.results.create_with_competencies(
            user_id=user_id,
            test_id=session_obj.test_id,
            session_id=session_id,
            total_score=score.total_score,
            max_score=score.max_score,
            percentage=score.percentage,
            level=str(score.level),
            competency_rows=competency_rows,
            next_retake_date=next_retake_date,
        )

        # 6 — tavsiyalarni ulash seami (R10.1): natija saqlangach, commit'dan
        # oldin. Callback xato ko'tarsa, tashqi tranzaksiya rollback qiladi.
        if self._on_result_created is not None:
            self._on_result_created(result)

        self.session.commit()
        return SubmissionOutcome(result_id=result.id, score=score)

    # ------------------------------------------------------------------
    # Ichki yordamchilar
    # ------------------------------------------------------------------

    def _compute_next_retake_date(self, now: datetime) -> date:
        """Keyingi qayta topshirish sanasini hisoblaydi (R8.4)."""
        return _to_naive_utc(now).date() + timedelta(
            days=self._retake_interval_days
        )

    def _ensure_unanswered_marked(self, session_obj: TestSession) -> None:
        """Javob yozuvi bo'lmagan savollarni ``answered=false`` qiladi (R7.5)."""
        test = self.tests.get_with_questions(session_obj.test_id)
        if test is None:
            return
        existing = {
            a.question_id for a in self.sessions.list_answers(session_obj.id)
        }
        for question in test.questions:
            if question.id not in existing:
                self.sessions.upsert_answer(
                    session_id=session_obj.id,
                    question_id=question.id,
                    selected_answer_id=None,
                    likert_value=None,
                    answered=False,
                )

    @staticmethod
    def _normalize_answers(
        answers: Iterable[Mapping[str, Any] | Any],
        valid_qids: set[int],
    ) -> dict[int, tuple[int | None, int | None]]:
        """Kiruvchi javoblarni ``{question_id: (selected_answer_id, likert_value)}`` ga.

        - ``question_id`` testga tegishli bo'lmagan javoblar e'tiborga olinmaydi.
        - Tanlangan variant identifikatori ``answer_id`` yoki
          ``selected_answer_id`` kalitidan o'qiladi.
        - Faqat haqiqiy qiymat (variant id yoki likert) bo'lgan javoblar
          kiritiladi; ikkalasi ham yo'q bo'lsa javob hisoblanmaydi.
        """
        normalized: dict[int, tuple[int | None, int | None]] = {}
        for item in answers or []:
            qid = _get(item, "question_id")
            if qid is None or qid not in valid_qids:
                continue
            selected = _get(item, "answer_id")
            if selected is None:
                selected = _get(item, "selected_answer_id")
            likert = _get(item, "likert_value")
            if selected is None and likert is None:
                continue
            normalized[int(qid)] = (
                int(selected) if selected is not None else None,
                int(likert) if likert is not None else None,
            )
        return normalized

    @staticmethod
    def _is_answered(
        question_id: int,
        provided: dict[int, tuple[int | None, int | None]],
        existing_answers: dict[int, SessionAnswer],
    ) -> bool:
        """Savol shu topshirishda yoki avval saqlangan holda javoblanganmi (R7.8)."""
        if question_id in provided:
            return True
        existing = existing_answers.get(question_id)
        return existing is not None and existing.answered

    def _to_answered_question(
        self, question: Question, answer: SessionAnswer | None
    ) -> AnsweredQuestion:
        """ORM savol + javobni baholash uchun :class:`AnsweredQuestion` ga."""
        max_score = _to_decimal(question.score)
        awarded = self._awarded_score(question, answer, max_score)
        return AnsweredQuestion(
            question_id=question.id,
            awarded_score=awarded,
            max_score=max_score,
            competency_id=question.competency_id,
        )

    @staticmethod
    def _awarded_score(
        question: Question,
        answer: SessionAnswer | None,
        max_score: Decimal,
    ) -> Decimal:
        """Bitta savol uchun yig'ilgan ballni hisoblaydi (modul docstring'iga qarang).

        - Javobsiz/yo'q javob -> 0.
        - Likert -> ``max_score * likert_value / 5`` (2 kasr, half-up).
        - Variant tanlash -> tanlangan ``answers.score`` (aniq bo'lsa); aks holda
          ``is_correct`` -> to'liq ball, yo'q -> 0.

        Natija ``[0, max_score]`` oralig'iga qisiladi (foiz 0–100 da qoladi).
        """
        if answer is None or not answer.answered:
            return _ZERO

        if answer.likert_value is not None:
            raw = max_score * _to_decimal(answer.likert_value) / LIKERT_MAX
            awarded = raw.quantize(_CENTS, rounding=ROUND_HALF_UP)
        elif answer.selected_answer_id is not None:
            selected = next(
                (
                    a
                    for a in question.answers
                    if a.id == answer.selected_answer_id
                ),
                None,
            )
            if selected is None:
                awarded = _ZERO
            elif selected.score is not None:
                awarded = _to_decimal(selected.score)
            elif selected.is_correct:
                awarded = max_score
            else:
                awarded = _ZERO
        else:
            awarded = _ZERO

        # Clamp [0, max_score] — umumiy foiz 0–100 oralig'ida qoladi (R8.1).
        if awarded < _ZERO:
            return _ZERO
        if awarded > max_score:
            return max_score
        return awarded


__all__ = [
    "SessionService",
    "SubmissionOutcome",
    "LIKERT_MAX",
    "DEFAULT_RETAKE_INTERVAL_DAYS",
]
