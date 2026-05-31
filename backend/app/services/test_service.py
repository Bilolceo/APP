"""Diagnostika_Moduli — TestService (R6).

Testlar ro'yxati va test tafsilotlari uchun biznes-mantiq. Servis sof
framework'dan mustaqil (FastAPI'ga bog'liq emas): konstruktorda SQLAlchemy
`Session` (yoki tayyor `TestRepository`) oladi va ma'lumotlarga repository
qatlami orqali kiradi.

Mas'uliyat (design.md — "Diagnostika_Moduli (TestService / SessionService)"):
- ``list_tests()`` — faqat faol (``is_active = true``) testlar; faol test
  bo'lmasa bo'sh ro'yxat (xato emas) (R6.1, R6.5).
- ``list_tests_by_category()`` — faol testlarni to'rt yo'nalish bo'yicha
  toifalaydi: kognitiv, kompetensiya, reflexiv, situatsion (R6.2).
- ``get_test(test_id)`` — test tafsilotlari (nomi, tavsifi, toifasi,
  davomiyligi, savollar soni) hamda savollar to'plami ``order_index`` bo'yicha
  belgilangan tartibda, har bir savol javob variantlari bilan; mavjud yoki faol
  bo'lmasa ``NotFoundError`` (-> keyinchalik 404) (R6.3, R6.4).

Eslatma (xavfsizlik): test tafsilotida javob variantlarining to'g'riligi
(``is_correct``) yoki balli (``score``) oshkor qilinmaydi — test topshirayotgan
foydalanuvchiga faqat variant matni va identifikatori beriladi.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.content import Answer, Question, Test
from app.repositories.tests import TestRepository

# Umumiy xato tiplari (`app/services/errors.py`) boshqa vazifada parallel
# yaratilmoqda. Mavjud bo'lsa undan import qilamiz; aks holda quyida minimal
# lokal `NotFoundError` zaxira (fallback) sifatida aniqlanadi.
# TODO(unify): `app.services.errors` tayyor bo'lgach, lokal fallback'ni olib
# tashlab faqat shared importga o'tish kerak.
try:  # pragma: no cover - importning mavjudligiga bog'liq
    from app.services.errors import NotFoundError
except ImportError:  # pragma: no cover - shared modul hali yo'q

    class NotFoundError(Exception):
        """Resurs topilmadi (-> 404). `app.services.errors` uchun zaxira.

        Shared modul tayyor bo'lgach, bu lokal ta'rif olib tashlanadi va
        servis to'g'ridan-to'g'ri `app.services.errors.NotFoundError` dan
        foydalanadi (design.md — "Error Handling": NotFoundError -> 404).
        """

        def __init__(self, message: str = "Topilmadi") -> None:
            super().__init__(message)
            self.message = message


#: Diagnostika yo'nalishlari (R6.2). Toifalash ushbu tartibda qaytariladi.
TEST_CATEGORIES: tuple[str, ...] = (
    "kognitiv",
    "kompetensiya",
    "reflexiv",
    "situatsion",
)


@dataclass(frozen=True)
class TestSummary:
    """Testlar ro'yxatidagi bitta yozuv (R6.1).

    Maydonlar test ro'yxati uchun yetarli minimal ma'lumotni o'z ichiga oladi:
    noyob identifikatori, nomi, tavsifi, toifasi va davomiyligi (daqiqalarda).
    """

    id: int
    title: str
    description: str | None
    category: str | None
    duration_minutes: int | None


@dataclass(frozen=True)
class AnswerOption:
    """Savolning bitta javob varianti (R6.3).

    Faqat foydalanuvchiga ko'rsatiladigan ma'lumot: variant identifikatori va
    matni. To'g'rilik/ball ataylab oshkor qilinmaydi.
    """

    id: int
    answer_text: str


@dataclass(frozen=True)
class QuestionDetail:
    """Test tafsilotidagi bitta savol va uning javob variantlari (R6.3)."""

    id: int
    question_text: str
    question_type: str | None
    order_index: int | None
    competency_id: int | None
    answers: list[AnswerOption] = field(default_factory=list)


@dataclass(frozen=True)
class TestDetail:
    """Test tafsiloti: meta-ma'lumot + savollar to'plami (R6.3).

    ``question_count`` — savollar soni; ``questions`` — ``order_index`` bo'yicha
    belgilangan tartibda joylashtirilgan savollar ro'yxati.
    """

    id: int
    title: str
    description: str | None
    category: str | None
    duration_minutes: int | None
    question_count: int
    questions: list[QuestionDetail] = field(default_factory=list)


def _question_sort_key(question: Question) -> tuple[bool, int, int]:
    """Savollarni ``order_index`` bo'yicha (None oxirida), so'ng ``id`` bo'yicha.

    ``order_index`` ``None`` bo'lgan savollar oxiriga joylashtiriladi; teng
    ``order_index`` qiymatlarida ``id`` bo'yicha o'suvchi tartib (deterministik).
    """
    order_index = question.order_index
    return (order_index is None, order_index or 0, question.id)


def _to_summary(test: Test) -> TestSummary:
    """ORM `Test` -> `TestSummary` DTO."""
    return TestSummary(
        id=test.id,
        title=test.title,
        description=test.description,
        category=test.category,
        duration_minutes=test.duration_minutes,
    )


def _to_answer_option(answer: Answer) -> AnswerOption:
    """ORM `Answer` -> `AnswerOption` DTO (faqat id va matn)."""
    return AnswerOption(id=answer.id, answer_text=answer.answer_text)


def _to_question_detail(question: Question) -> QuestionDetail:
    """ORM `Question` -> `QuestionDetail` DTO; javoblar id bo'yicha tartiblanadi."""
    answers = sorted(question.answers, key=lambda a: a.id)
    return QuestionDetail(
        id=question.id,
        question_text=question.question_text,
        question_type=question.question_type,
        order_index=question.order_index,
        competency_id=question.competency_id,
        answers=[_to_answer_option(a) for a in answers],
    )


class TestService:
    """Diagnostika testlari ro'yxati va tafsiloti uchun servis (R6).

    Args:
        session: faol SQLAlchemy `Session`. ``test_repository`` berilmagan
            bo'lsa, undan `TestRepository` quriladi.
        test_repository: ixtiyoriy, tayyor `TestRepository` (test/inject uchun).

    `session` ham, `test_repository` ham berilmasa `ValueError` ko'tariladi.
    """

    # pytest bu servis klassini test klassi sifatida yig'ishga urinmasligi uchun
    # (nomi "Test" bilan boshlanadi — ORM `Test` modelidagi konvensiya bilan bir xil).
    __test__ = False

    def __init__(
        self,
        session: Session | None = None,
        *,
        test_repository: TestRepository | None = None,
    ) -> None:
        if test_repository is None:
            if session is None:
                raise ValueError(
                    "TestService uchun `session` yoki `test_repository` zarur"
                )
            test_repository = TestRepository(session)
        self._tests = test_repository

    def list_tests(self) -> list[TestSummary]:
        """Faqat faol testlar ro'yxatini qaytaradi (R6.1, R6.5).

        Faol test bo'lmasa bo'sh ro'yxat qaytaradi (xato emas). Tartib
        repository tomonidan deterministik (``id`` bo'yicha).
        """
        return [_to_summary(test) for test in self._tests.list_active()]

    def list_tests_by_category(self) -> dict[str, list[TestSummary]]:
        """Faol testlarni to'rt yo'nalish bo'yicha toifalaydi (R6.2).

        Qaytariladigan lug'at kalitlari har doim to'rtta yo'nalishni o'z ichiga
        oladi (``TEST_CATEGORIES`` tartibida); mos test bo'lmagan yo'nalish bo'sh
        ro'yxat bilan qaytadi. To'rt yo'nalishdan tashqari (yoki ``None``)
        toifadagi testlar bu guruhlashga kiritilmaydi (ular ``list_tests()``
        ning tekis ro'yxatida mavjud bo'ladi).
        """
        grouped: dict[str, list[TestSummary]] = {
            category: [] for category in TEST_CATEGORIES
        }
        for summary in self.list_tests():
            if summary.category in grouped:
                grouped[summary.category].append(summary)
        return grouped

    def get_test(self, test_id: int) -> TestDetail:
        """Test tafsilotini va savollarini belgilangan tartibda qaytaradi (R6.3).

        Mavjud bo'lmagan yoki faol bo'lmagan test so'ralsa `NotFoundError`
        ko'taradi (R6.4 -> keyinchalik 404).
        """
        test = self._tests.get_with_questions(test_id)
        if test is None or not test.is_active:
            raise NotFoundError("Test topilmadi")

        ordered_questions = sorted(test.questions, key=_question_sort_key)
        questions = [_to_question_detail(q) for q in ordered_questions]
        return TestDetail(
            id=test.id,
            title=test.title,
            description=test.description,
            category=test.category,
            duration_minutes=test.duration_minutes,
            question_count=len(questions),
            questions=questions,
        )


__all__ = [
    "TestService",
    "TestSummary",
    "TestDetail",
    "QuestionDetail",
    "AnswerOption",
    "TEST_CATEGORIES",
    "NotFoundError",
]
