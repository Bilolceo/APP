"""Admin_Moduli — AdminService (R14).

Administrator uchun kontent boshqaruvi (CRUD): testlar, savollar, javob
variantlari, kompetensiyalar va tavsiyalar. Servis framework'dan mustaqil
(FastAPI'siz): konstruktorga SQLAlchemy `Session` (yoki tayyor repositorylar)
beriladi va biznes qoidalari hamda validatsiya shu yerda hal qilinadi.
Repository qatlami yupqa (thin) bo'lib qoladi.

Mas'uliyat (design.md — "Admin_Moduli (AdminService)"):
- Test/savol/kompetensiya/tavsiya CRUD (R14.1).
- Test validatsiyasi: nom 1–200 belgi, toifa yaroqli ({kognitiv, kompetensiya,
  reflexiv, situatsion}), davomiyligi 1–600 oralig'idagi butun son (R14.2).
- Savol validatsiyasi: matn 1–1000 belgi, kamida 2 ta javob varianti, ball
  0.01–1000 oralig'idagi musbat son, mavjud kompetensiyaga bog'lash (R14.3).
- Testni o'chirish yoki nofaol qilish — uni faol ro'yxatdan chiqaradi (R14.4).
- Yaroqsiz/to'liqsiz yaratish yoki tahrirlash -> `ValidationError`, hech narsa
  saqlanmaydi (R14.6).
- Savol mavjud bo'lmagan kompetensiyaga bog'lansa -> `NotFoundError` (R14.7).
- Ishlatilayotgan (bog'langan) kompetensiyani o'chirish -> `ConflictError`
  (referensial yaxlitlik, R14.8).

Eslatma (xavfsizlik / RBAC): admin-only ruxsat tekshiruvi (R14.5) router/RBAC
qatlamida (task 16.5/17.4) amalga oshiriladi. Ushbu servis chaqiruvchi
avtorizatsiyalangan deb qabul qiladi va o'zi rol tekshirmaydi (framework'dan
mustaqil qolish uchun).

MUHIM tamoyil: har bir operatsiyada **avval to'liq validatsiya**, keyin
persistensiya. Yaroqsiz so'rov hech qanday holatni o'zgartirmasligi kerak (R14.6).
Repositorylar `flush` qiladi, `commit` qilmaydi — tranzaksiya chegarasi
chaqiruvchida boshqariladi.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.models.content import Question, Test
from app.models.recommendation import Recommendation
from app.models.reference import Competency
from app.repositories.recommendations import RecommendationRepository
from app.repositories.reference import CompetencyRepository
from app.repositories.tests import (
    AnswerRepository,
    QuestionRepository,
    TestRepository,
)
from app.services.errors import ConflictError, NotFoundError, ValidationError

# ---------------------------------------------------------------------------
# Validatsiya cheklovlari (R14.2, R14.3)
# ---------------------------------------------------------------------------

#: Yaroqli test toifalari (R14.2, R6.2). Tartib referens uchun.
VALID_TEST_CATEGORIES: tuple[str, ...] = (
    "kognitiv",
    "kompetensiya",
    "reflexiv",
    "situatsion",
)

#: Test nomi uzunligi oralig'i (R14.2).
MIN_TITLE_LENGTH = 1
MAX_TITLE_LENGTH = 200

#: Test davomiyligi (daqiqa) oralig'i (R14.2).
MIN_DURATION_MINUTES = 1
MAX_DURATION_MINUTES = 600

#: Savol matni uzunligi oralig'i (R14.3).
MIN_QUESTION_TEXT_LENGTH = 1
MAX_QUESTION_TEXT_LENGTH = 1000

#: Savol balli oralig'i (R14.3) — musbat son.
MIN_QUESTION_SCORE = Decimal("0.01")
MAX_QUESTION_SCORE = Decimal("1000")

#: Savol balli saqlanadigan aniqlik (Numeric(7,2)).
_SCORE_QUANTUM = Decimal("0.01")

#: Savol uchun kamida nechta javob varianti talab qilinadi (R14.3).
MIN_ANSWER_OPTIONS = 2

#: "Berilmagan" (not provided) ni "None ga o'rnatilgan" dan ajratish uchun
#: sentinel — qisman (partial) yangilashlar uchun.
_UNSET: Any = object()


def _validation_error(message: str, field: str | None) -> ValidationError:
    """Qaysi maydon yaroqsizligini ko'rsatuvchi `ValidationError` yaratadi (R14.6, R20.6)."""
    return ValidationError(message, field=field)


# ---------------------------------------------------------------------------
# Maydon validatorlari (sof — hech narsa saqlamaydi)
# ---------------------------------------------------------------------------


def _validate_title(value: Any) -> str:
    """Test nomi 1–200 belgi va bo'sh/whitespace bo'lmasligini tekshiradi (R14.2, R14.6)."""
    if not isinstance(value, str):
        raise _validation_error("Test nomi matn bo'lishi kerak", "title")
    if not value.strip():
        raise _validation_error(
            "Test nomi bo'sh yoki faqat bo'sh joydan iborat bo'lishi mumkin emas",
            "title",
        )
    if len(value) > MAX_TITLE_LENGTH:
        raise _validation_error(
            f"Test nomi {MAX_TITLE_LENGTH} belgidan oshmasligi kerak",
            "title",
        )
    return value


def _validate_category(value: Any) -> str:
    """Toifa yaroqli to'plamdan ekanini tekshiradi (R14.2, R14.6)."""
    if not isinstance(value, str) or value not in VALID_TEST_CATEGORIES:
        allowed = ", ".join(VALID_TEST_CATEGORIES)
        raise _validation_error(
            f"Test toifasi quyidagilardan biri bo'lishi kerak: {allowed}",
            "category",
        )
    return value


def _validate_duration_minutes(value: Any) -> int:
    """Davomiylik 1–600 oralig'idagi butun son ekanini tekshiradi (R14.2, R14.6)."""
    # ``bool`` — ``int`` ning quyi klassi; uni alohida rad etamiz.
    if isinstance(value, bool) or not isinstance(value, int):
        raise _validation_error(
            "Test davomiyligi butun son (daqiqalarda) bo'lishi kerak",
            "duration_minutes",
        )
    if value < MIN_DURATION_MINUTES or value > MAX_DURATION_MINUTES:
        raise _validation_error(
            f"Test davomiyligi {MIN_DURATION_MINUTES}–{MAX_DURATION_MINUTES} "
            "daqiqa oralig'ida bo'lishi kerak",
            "duration_minutes",
        )
    return value


def _validate_description(value: Any) -> str | None:
    """Tavsif (ixtiyoriy) matn yoki ``None`` ekanini tekshiradi."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise _validation_error("Tavsif matn bo'lishi kerak", "description")
    return value


def _validate_question_text(value: Any) -> str:
    """Savol matni 1–1000 belgi va bo'sh bo'lmasligini tekshiradi (R14.3, R14.6)."""
    if not isinstance(value, str):
        raise _validation_error(
            "Savol matni matn bo'lishi kerak", "question_text"
        )
    if not value.strip():
        raise _validation_error(
            "Savol matni bo'sh yoki faqat bo'sh joydan iborat bo'lishi mumkin emas",
            "question_text",
        )
    if len(value) > MAX_QUESTION_TEXT_LENGTH:
        raise _validation_error(
            f"Savol matni {MAX_QUESTION_TEXT_LENGTH} belgidan oshmasligi kerak",
            "question_text",
        )
    return value


def _normalize_score(value: Any) -> Decimal:
    """Savol ballini `Decimal` ga keltiradi va 0.01–1000 oralig'ini tekshiradi (R14.3, R14.6).

    ``int``, ``float``, ``Decimal`` yoki son ko'rinishidagi ``str`` qabul
    qilinadi; ``bool`` va boshqa tiplar rad etiladi. Qiymat 2 kasr xonasiga
    (Numeric(7,2)) yaxlitlanadi va oralig'i shu yaxlitlangan qiymatda
    tekshiriladi.
    """
    if isinstance(value, bool):
        raise _validation_error("Savol balli son bo'lishi kerak", "score")
    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, int):
        decimal_value = Decimal(value)
    elif isinstance(value, float):
        # ``float`` aniqsizligidan qochish uchun avval ``str`` orqali o'tamiz.
        decimal_value = Decimal(str(value))
    elif isinstance(value, str):
        try:
            decimal_value = Decimal(value.strip())
        except (InvalidOperation, ValueError):
            raise _validation_error(
                "Savol balli yaroqli son bo'lishi kerak", "score"
            ) from None
    else:
        raise _validation_error("Savol balli son bo'lishi kerak", "score")

    if not decimal_value.is_finite():
        raise _validation_error(
            "Savol balli chekli (finite) son bo'lishi kerak", "score"
        )

    quantized = decimal_value.quantize(_SCORE_QUANTUM)
    if quantized < MIN_QUESTION_SCORE or quantized > MAX_QUESTION_SCORE:
        raise _validation_error(
            f"Savol balli {MIN_QUESTION_SCORE}–{MAX_QUESTION_SCORE} oralig'idagi "
            "musbat son bo'lishi kerak",
            "score",
        )
    return quantized


def _validate_competency_id(value: Any) -> int:
    """Kompetensiya identifikatori musbat butun son ekanini tekshiradi (R14.3, R14.6).

    Mavjudligi (R14.7) alohida `NotFoundError` bilan tekshiriladi — bu funksiya
    faqat formatni tekshiradi.
    """
    if value is None:
        raise _validation_error(
            "Savol mavjud kompetensiyaga bog'lanishi shart", "competency_id"
        )
    if isinstance(value, bool) or not isinstance(value, int):
        raise _validation_error(
            "Kompetensiya identifikatori butun son bo'lishi kerak",
            "competency_id",
        )
    if value <= 0:
        raise _validation_error(
            "Kompetensiya identifikatori musbat bo'lishi kerak", "competency_id"
        )
    return value


def _normalize_answers(answers: Any) -> list[dict[str, Any]]:
    """Javob variantlarini tekshiradi va normallashtiradi (R14.3, R14.6).

    Kamida 2 ta variant talab qilinadi. Har bir element ``str`` (faqat matn)
    yoki ``Mapping`` (``answer_text`` majburiy; ``is_correct``, ``score``
    ixtiyoriy) bo'lishi mumkin.
    """
    if answers is None or isinstance(answers, (str, bytes, Mapping)):
        # Yagona qiymat yoki mapping — ro'yxat emas; rad etamiz.
        raise _validation_error(
            f"Savol uchun kamida {MIN_ANSWER_OPTIONS} ta javob varianti kerak",
            "answers",
        )
    if not isinstance(answers, (list, tuple)):
        raise _validation_error(
            "Javob variantlari ro'yxat bo'lishi kerak", "answers"
        )

    items = list(answers)
    if len(items) < MIN_ANSWER_OPTIONS:
        raise _validation_error(
            f"Savol uchun kamida {MIN_ANSWER_OPTIONS} ta javob varianti kerak",
            "answers",
        )

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if isinstance(item, str):
            text: Any = item
            is_correct: Any = False
            score: Any = None
        elif isinstance(item, Mapping):
            text = item.get("answer_text")
            is_correct = item.get("is_correct", False)
            score = item.get("score")
        else:
            raise _validation_error(
                f"Javob varianti #{index + 1} matn yoki obyekt bo'lishi kerak",
                "answers",
            )

        if not isinstance(text, str) or not text.strip():
            raise _validation_error(
                f"Javob varianti #{index + 1} matni bo'sh bo'lishi mumkin emas",
                "answers",
            )
        if not isinstance(is_correct, bool):
            raise _validation_error(
                f"Javob varianti #{index + 1} 'is_correct' qiymati mantiqiy "
                "(bool) bo'lishi kerak",
                "answers",
            )
        normalized.append(
            {
                "answer_text": text,
                "is_correct": is_correct,
                "score": (
                    None if score is None else _normalize_score(score)
                ),
            }
        )
    return normalized


class AdminService:
    """Administrator kontent boshqaruvi (CRUD) servisi (R14).

    Args:
        session: faol SQLAlchemy `Session`. Repositorylar berilmagan bo'lsa,
            ulardan shu sessiya orqali quriladi.
        tests: ixtiyoriy `TestRepository` (test/inject uchun).
        questions: ixtiyoriy `QuestionRepository`.
        answers: ixtiyoriy `AnswerRepository`.
        competencies: ixtiyoriy `CompetencyRepository`.
        recommendations: ixtiyoriy `RecommendationRepository`.

    `session` ham, repositorylar ham berilmasa `ValueError` ko'tariladi.
    """

    def __init__(
        self,
        session: Session | None = None,
        *,
        tests: TestRepository | None = None,
        questions: QuestionRepository | None = None,
        answers: AnswerRepository | None = None,
        competencies: CompetencyRepository | None = None,
        recommendations: RecommendationRepository | None = None,
    ) -> None:
        if session is None and tests is None:
            raise ValueError(
                "AdminService uchun `session` yoki repositorylar zarur"
            )
        self._tests = tests or TestRepository(session)  # type: ignore[arg-type]
        self._questions = questions or QuestionRepository(session)  # type: ignore[arg-type]
        self._answers = answers or AnswerRepository(session)  # type: ignore[arg-type]
        self._competencies = competencies or CompetencyRepository(session)  # type: ignore[arg-type]
        self._recommendations = recommendations or RecommendationRepository(
            session  # type: ignore[arg-type]
        )

    # -- Test CRUD (R14.2, R14.4, R14.6) ------------------------------------

    def create_test(
        self,
        *,
        title: str,
        category: str,
        duration_minutes: int,
        description: str | None = None,
        is_active: bool = True,
    ) -> Test:
        """Yangi test yaratadi (R14.2).

        Validatsiya: nom 1–200 belgi, toifa yaroqli, davomiyligi 1–600 butun.
        Yaroqsiz qiymat -> `ValidationError`, hech narsa saqlanmaydi (R14.6).
        """
        validated_title = _validate_title(title)
        validated_category = _validate_category(category)
        validated_duration = _validate_duration_minutes(duration_minutes)
        validated_description = _validate_description(description)
        if not isinstance(is_active, bool):
            raise _validation_error(
                "'is_active' qiymati mantiqiy (bool) bo'lishi kerak", "is_active"
            )

        return self._tests.create(
            title=validated_title,
            category=validated_category,
            duration_minutes=validated_duration,
            description=validated_description,
            is_active=is_active,
        )

    def update_test(
        self,
        test_id: int,
        *,
        title: Any = _UNSET,
        category: Any = _UNSET,
        duration_minutes: Any = _UNSET,
        description: Any = _UNSET,
        is_active: Any = _UNSET,
    ) -> Test:
        """Mavjud testni qisman yangilaydi (R14.2, R14.6).

        Faqat berilgan maydonlar yangilanadi. Validatsiya muvaffaqiyatsiz
        bo'lsa hech narsa o'zgartirilmaydi (R14.6). Test topilmasa
        `NotFoundError` (R14.7 — topilmadi semantikasi).
        """
        test = self._tests.get_by_id(test_id)
        if test is None:
            raise NotFoundError(f"Test topilmadi (id={test_id})")

        # Avval barcha berilgan maydonlarni validatsiya qilamiz (persistensiyadan
        # oldin) — yaroqsiz so'rov holatni o'zgartirmasligi kerak (R14.6).
        updates: dict[str, Any] = {}
        if title is not _UNSET:
            updates["title"] = _validate_title(title)
        if category is not _UNSET:
            updates["category"] = _validate_category(category)
        if duration_minutes is not _UNSET:
            updates["duration_minutes"] = _validate_duration_minutes(
                duration_minutes
            )
        if description is not _UNSET:
            updates["description"] = _validate_description(description)
        if is_active is not _UNSET:
            if not isinstance(is_active, bool):
                raise _validation_error(
                    "'is_active' qiymati mantiqiy (bool) bo'lishi kerak",
                    "is_active",
                )
            updates["is_active"] = is_active

        for key, value in updates.items():
            setattr(test, key, value)
        self._tests.session.flush()
        return test

    def delete_or_deactivate_test(
        self, test_id: int, *, hard_delete: bool = False
    ) -> Test | None:
        """Testni o'chiradi yoki nofaol qiladi — uni faol ro'yxatdan chiqaradi (R14.4).

        Standart holatda (``hard_delete=False``) test ``is_active=False`` ga
        o'tkaziladi (yumshoq o'chirish) — bu uni `list_active` natijasidan
        chiqaradi va bog'liq yozuvlarni (savollar, natijalar) saqlab qoladi.
        ``hard_delete=True`` bo'lsa test qatori bazadan o'chiriladi.

        Test topilmasa `NotFoundError`.

        Returns:
            Nofaol qilingan `Test` (soft), yoki ``None`` (hard delete).
        """
        test = self._tests.get_by_id(test_id)
        if test is None:
            raise NotFoundError(f"Test topilmadi (id={test_id})")

        if hard_delete:
            self._tests.delete(test)
            return None

        return self._tests.set_active(test, is_active=False)

    # -- Question CRUD (R14.3, R14.6, R14.7) --------------------------------

    def create_question(
        self,
        *,
        test_id: int,
        question_text: str,
        score: Any,
        competency_id: int,
        answers: Sequence[Any],
        question_type: str | None = None,
        order_index: int | None = None,
    ) -> Question:
        """Yangi savol va uning javob variantlarini yaratadi (R14.3).

        Validatsiya: matn 1–1000 belgi, ball 0.01–1000 musbat son, kamida 2 ta
        javob varianti, mavjud kompetensiyaga bog'lash. Yaroqsiz/to'liqsiz
        qiymat -> `ValidationError`, hech narsa saqlanmaydi (R14.6). Mavjud
        bo'lmagan kompetensiya -> `NotFoundError` (R14.7).
        """
        test = self._tests.get_by_id(test_id)
        if test is None:
            raise NotFoundError(f"Test topilmadi (id={test_id})")

        # To'liq validatsiya (persistensiyadan oldin) — R14.6.
        validated_text = _validate_question_text(question_text)
        validated_score = _normalize_score(score)
        validated_competency_id = _validate_competency_id(competency_id)
        normalized_answers = _normalize_answers(answers)
        validated_type = self._validate_question_type(question_type)
        validated_order = self._validate_order_index(order_index)

        # Kompetensiya mavjudligini tekshirish (R14.7).
        self._require_competency(validated_competency_id)

        # Validatsiya tugadi — endi persist qilamiz.
        question = self._questions.create(
            test_id=test_id,
            question_text=validated_text,
            score=validated_score,
            competency_id=validated_competency_id,
            question_type=validated_type,
            order_index=validated_order,
        )
        for answer in normalized_answers:
            self._answers.create(
                question_id=question.id,
                answer_text=answer["answer_text"],
                is_correct=answer["is_correct"],
                score=answer["score"],
            )
        return question

    def update_question(
        self,
        question_id: int,
        *,
        question_text: Any = _UNSET,
        score: Any = _UNSET,
        competency_id: Any = _UNSET,
        answers: Any = _UNSET,
        question_type: Any = _UNSET,
        order_index: Any = _UNSET,
    ) -> Question:
        """Mavjud savolni qisman yangilaydi (R14.3, R14.6, R14.7).

        Faqat berilgan maydonlar yangilanadi. ``answers`` berilsa, mavjud
        variantlar yangilari bilan to'liq almashtiriladi (kamida 2 ta).
        Yaroqsiz qiymat -> `ValidationError`, mavjud bo'lmagan kompetensiya ->
        `NotFoundError`; ikkala holatda ham hech narsa saqlanmaydi (R14.6).
        """
        question = self._questions.get_by_id(question_id)
        if question is None:
            raise NotFoundError(f"Savol topilmadi (id={question_id})")

        # 1) Barcha berilgan maydonlarni validatsiya qilamiz (persistensiyadan oldin).
        updates: dict[str, Any] = {}
        if question_text is not _UNSET:
            updates["question_text"] = _validate_question_text(question_text)
        if score is not _UNSET:
            updates["score"] = _normalize_score(score)
        if competency_id is not _UNSET:
            validated_competency_id = _validate_competency_id(competency_id)
            self._require_competency(validated_competency_id)
            updates["competency_id"] = validated_competency_id
        if question_type is not _UNSET:
            updates["question_type"] = self._validate_question_type(question_type)
        if order_index is not _UNSET:
            updates["order_index"] = self._validate_order_index(order_index)

        normalized_answers: list[dict[str, Any]] | None = None
        if answers is not _UNSET:
            normalized_answers = _normalize_answers(answers)

        # 2) Validatsiya tugadi — endi persist qilamiz.
        for key, value in updates.items():
            setattr(question, key, value)

        if normalized_answers is not None:
            # Mavjud variantlarni o'chirib, yangilari bilan almashtiramiz.
            for existing in self._answers.list_for_question(question.id):
                self._answers.delete(existing)
            for answer in normalized_answers:
                self._answers.create(
                    question_id=question.id,
                    answer_text=answer["answer_text"],
                    is_correct=answer["is_correct"],
                    score=answer["score"],
                )

        self._questions.session.flush()
        return question

    def delete_question(self, question_id: int) -> None:
        """Savolni va uning javob variantlarini o'chiradi (R14.1).

        Savol topilmasa `NotFoundError`.
        """
        question = self._questions.get_by_id(question_id)
        if question is None:
            raise NotFoundError(f"Savol topilmadi (id={question_id})")

        for answer in self._answers.list_for_question(question.id):
            self._answers.delete(answer)
        self._questions.delete(question)

    # -- Competency CRUD (R14.1, R14.8) -------------------------------------

    def create_competency(
        self, *, name: str, description: str | None = None
    ) -> Competency:
        """Yangi kompetensiya yaratadi (R14.1).

        Validatsiya: nom 1–200 belgi va bo'sh bo'lmasligi. Yaroqsiz -> `ValidationError`.
        """
        validated_name = self._validate_name(name, "competency name")
        validated_description = _validate_description(description)
        return self._competencies.create(
            name=validated_name, description=validated_description
        )

    def update_competency(
        self,
        competency_id: int,
        *,
        name: Any = _UNSET,
        description: Any = _UNSET,
    ) -> Competency:
        """Mavjud kompetensiyani qisman yangilaydi (R14.1, R14.6).

        Kompetensiya topilmasa `NotFoundError`.
        """
        competency = self._competencies.get_by_id(competency_id)
        if competency is None:
            raise NotFoundError(f"Kompetensiya topilmadi (id={competency_id})")

        if name is not _UNSET:
            competency.name = self._validate_name(name, "competency name")
        if description is not _UNSET:
            competency.description = _validate_description(description)
        self._competencies.session.flush()
        return competency

    def delete_competency(self, competency_id: int) -> None:
        """Kompetensiyani o'chiradi, agar u biror savolda ishlatilmagan bo'lsa (R14.8).

        Ishlatilayotgan (bog'langan) kompetensiyani o'chirish rad etiladi:
        `ConflictError` (referensial yaxlitlik). Kompetensiya topilmasa
        `NotFoundError`.
        """
        competency = self._competencies.get_by_id(competency_id)
        if competency is None:
            raise NotFoundError(f"Kompetensiya topilmadi (id={competency_id})")

        # Referensial yaxlitlik: ishlatilayotgan bo'lsa o'chirmaymiz (R14.8).
        if self._questions.is_competency_used(competency_id):
            raise ConflictError(
                "Kompetensiya bir yoki bir nechta savol tomonidan "
                "ishlatilmoqda va o'chirib bo'lmaydi",
                field="competency_id",
            )
        self._competencies.delete(competency)

    # -- Recommendation CRUD (R14.1) ----------------------------------------

    def create_recommendation(
        self,
        *,
        text: str,
        competency_id: int | None = None,
        level: str | None = None,
    ) -> Recommendation:
        """Yangi tavsiya yaratadi (R14.1).

        ``competency_id`` va ``level`` ixtiyoriy: ikkalasi ham bo'sh bo'lsa,
        tavsiya umumiy standart (default) tavsiya hisoblanadi (R10.4). Agar
        ``competency_id`` berilsa, u mavjud bo'lishi shart -> aks holda
        `NotFoundError`.
        """
        validated_text = self._validate_recommendation_text(text)
        validated_level = self._validate_level(level)
        validated_competency_id: int | None = None
        if competency_id is not None:
            validated_competency_id = _validate_competency_id(competency_id)
            self._require_competency(validated_competency_id)

        recommendation = Recommendation(
            competency_id=validated_competency_id,
            level=validated_level,
            text=validated_text,
        )
        return self._recommendations.add(recommendation)

    def update_recommendation(
        self,
        recommendation_id: int,
        *,
        text: Any = _UNSET,
        competency_id: Any = _UNSET,
        level: Any = _UNSET,
    ) -> Recommendation:
        """Mavjud tavsiyani qisman yangilaydi (R14.1, R14.6).

        Tavsiya topilmasa `NotFoundError`; berilgan mavjud bo'lmagan
        kompetensiya -> `NotFoundError`.
        """
        recommendation = self._recommendations.get_by_id(recommendation_id)
        if recommendation is None:
            raise NotFoundError(
                f"Tavsiya topilmadi (id={recommendation_id})"
            )

        if text is not _UNSET:
            recommendation.text = self._validate_recommendation_text(text)
        if level is not _UNSET:
            recommendation.level = self._validate_level(level)
        if competency_id is not _UNSET:
            if competency_id is None:
                recommendation.competency_id = None
            else:
                validated_competency_id = _validate_competency_id(competency_id)
                self._require_competency(validated_competency_id)
                recommendation.competency_id = validated_competency_id
        self._recommendations.session.flush()
        return recommendation

    def delete_recommendation(self, recommendation_id: int) -> None:
        """Tavsiyani o'chiradi (R14.1). Topilmasa `NotFoundError`."""
        recommendation = self._recommendations.get_by_id(recommendation_id)
        if recommendation is None:
            raise NotFoundError(
                f"Tavsiya topilmadi (id={recommendation_id})"
            )
        self._recommendations.delete(recommendation)

    # -- Ichki yordamchilar -------------------------------------------------

    def _require_competency(self, competency_id: int) -> Competency:
        """Kompetensiya mavjudligini ta'minlaydi; aks holda `NotFoundError` (R14.7)."""
        competency = self._competencies.get_by_id(competency_id)
        if competency is None:
            raise NotFoundError(
                f"Kompetensiya topilmadi (id={competency_id})",
            )
        return competency

    @staticmethod
    def _validate_name(value: Any, field: str) -> str:
        """Nom (kompetensiya) 1–200 belgi va bo'sh bo'lmasligini tekshiradi."""
        if not isinstance(value, str):
            raise _validation_error("Nom matn bo'lishi kerak", field)
        if not value.strip():
            raise _validation_error(
                "Nom bo'sh yoki faqat bo'sh joydan iborat bo'lishi mumkin emas",
                field,
            )
        if len(value) > MAX_TITLE_LENGTH:
            raise _validation_error(
                f"Nom {MAX_TITLE_LENGTH} belgidan oshmasligi kerak", field
            )
        return value

    @staticmethod
    def _validate_recommendation_text(value: Any) -> str:
        """Tavsiya matni bo'sh bo'lmagan matn ekanini tekshiradi (R14.1)."""
        if not isinstance(value, str):
            raise _validation_error("Tavsiya matni matn bo'lishi kerak", "text")
        if not value.strip():
            raise _validation_error(
                "Tavsiya matni bo'sh bo'lishi mumkin emas", "text"
            )
        return value

    @staticmethod
    def _validate_level(value: Any) -> str | None:
        """Daraja (ixtiyoriy) matn yoki ``None`` ekanini tekshiradi (R10.4)."""
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise _validation_error(
                "Daraja bo'sh bo'lmagan matn yoki None bo'lishi kerak", "level"
            )
        return value

    @staticmethod
    def _validate_question_type(value: Any) -> str | None:
        """Savol turi (ixtiyoriy) matn yoki ``None`` ekanini tekshiradi."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise _validation_error(
                "Savol turi matn bo'lishi kerak", "question_type"
            )
        return value

    @staticmethod
    def _validate_order_index(value: Any) -> int | None:
        """Tartib indeksi (ixtiyoriy) manfiy bo'lmagan butun son yoki ``None``."""
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            raise _validation_error(
                "Tartib indeksi butun son bo'lishi kerak", "order_index"
            )
        if value < 0:
            raise _validation_error(
                "Tartib indeksi manfiy bo'lmasligi kerak", "order_index"
            )
        return value


__all__ = [
    "AdminService",
    "VALID_TEST_CATEGORIES",
    "MIN_TITLE_LENGTH",
    "MAX_TITLE_LENGTH",
    "MIN_DURATION_MINUTES",
    "MAX_DURATION_MINUTES",
    "MIN_QUESTION_TEXT_LENGTH",
    "MAX_QUESTION_TEXT_LENGTH",
    "MIN_QUESTION_SCORE",
    "MAX_QUESTION_SCORE",
    "MIN_ANSWER_OPTIONS",
]
