"""1.2-vazifa: sof domen tiplari va `FileStorageBackend` abstraksiyasi testlari.

Bu testlar faqat tip ta'riflarini (struktura, immutability, Level enum
moslashuvi) va abstrakt interfeys shartnomasini tekshiradi. Hisoblash mantig'i
keyingi vazifalarda (3.x, 4.x) qo'shiladi va alohida test qilinadi.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain import (
    AnsweredQuestion,
    CompetencyResult,
    Level,
    RankedEntry,
    RatingRecord,
    ScoreInput,
    ScoreResult,
)
from app.storage.base import FileStorageBackend, StoredFile


# --- Level enum (R8.2) ---


def test_level_values_match_uzbek_labels() -> None:
    """Level a'zolari talab/dizayndagi o'zbekcha yorliqlarga aniq mos keladi."""
    assert Level.PAST.value == "Past"
    assert Level.ORTA.value == "O'rta"
    assert Level.YAXSHI.value == "Yaxshi"
    assert Level.YUQORI.value == "Yuqori"


def test_level_is_str_enum_and_has_four_members() -> None:
    """Level `str` dan meros oladi va aynan to'rt darajadan iborat."""
    assert isinstance(Level.PAST, str)
    assert {m.value for m in Level} == {"Past", "O'rta", "Yaxshi", "Yuqori"}
    assert str(Level.YUQORI) == "Yuqori"


# --- AnsweredQuestion ---


def test_answered_question_construction_and_optional_competency() -> None:
    """AnsweredQuestion yaratiladi; competency_id ixtiyoriy (standart None)."""
    aq = AnsweredQuestion(
        question_id=1,
        awarded_score=Decimal("3.00"),
        max_score=Decimal("5.00"),
    )
    assert aq.competency_id is None

    aq2 = AnsweredQuestion(
        question_id=2,
        awarded_score=Decimal("4"),
        max_score=Decimal("4"),
        competency_id=10,
    )
    assert aq2.competency_id == 10


def test_answered_question_is_frozen() -> None:
    """AnsweredQuestion immutable (frozen dataclass)."""
    aq = AnsweredQuestion(question_id=1, awarded_score=Decimal("1"), max_score=Decimal("2"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        aq.awarded_score = Decimal("9")  # type: ignore[misc]


# --- ScoreInput ---


def test_score_input_defaults_to_empty_list() -> None:
    """ScoreInput.answered standart bo'sh ro'yxat bo'ladi."""
    assert ScoreInput().answered == []
    items = [AnsweredQuestion(1, Decimal("1"), Decimal("2"))]
    assert ScoreInput(answered=items).answered == items


# --- CompetencyResult / ScoreResult ---


def test_competency_result_optional_score_fields() -> None:
    """CompetencyResult foiz bilan yaratiladi; score/max_score ixtiyoriy."""
    cr = CompetencyResult(competency_id=5, percentage=Decimal("80.00"))
    assert cr.score is None and cr.max_score is None


def test_score_result_holds_all_design_fields() -> None:
    """ScoreResult design.md dagi barcha maydonlarni saqlaydi."""
    cr = CompetencyResult(competency_id=5, percentage=Decimal("80.00"))
    result = ScoreResult(
        total_score=Decimal("40.00"),
        max_score=Decimal("50.00"),
        percentage=Decimal("80.00"),
        level=Level.YUQORI,
        competencies=[cr],
        strongest=[5],
        weakest=[7],
    )
    assert result.level is Level.YUQORI
    assert result.competencies[0] is cr
    assert result.strongest == [5]
    assert result.weakest == [7]


def test_score_result_collection_defaults() -> None:
    """ScoreResult kolleksiya maydonlari standart bo'sh ro'yxat bo'ladi."""
    result = ScoreResult(
        total_score=Decimal("0"),
        max_score=Decimal("0"),
        percentage=Decimal("0.00"),
        level=Level.PAST,
    )
    assert result.competencies == []
    assert result.strongest == []
    assert result.weakest == []


# --- RatingRecord / RankedEntry ---


def test_rating_record_and_ranked_entry() -> None:
    """RatingRecord va RankedEntry maydonlari design.md ga mos."""
    achieved = datetime(2024, 1, 1, tzinfo=timezone.utc)
    record = RatingRecord(entity_id=1, sort_metric=Decimal("75.50"), achieved_at=achieved)
    assert record.achieved_at == achieved

    entry = RankedEntry(entity_id=1, rank=1, sort_metric=Decimal("75.50"))
    assert entry.rank == 1


# --- FileStorageBackend (R18.2) ---


def test_file_storage_backend_is_abstract() -> None:
    """FileStorageBackend bevosita instansiyalanmaydi (abstrakt)."""
    with pytest.raises(TypeError):
        FileStorageBackend()  # type: ignore[abstract]


def test_file_storage_backend_declares_required_methods() -> None:
    """save/get/delete abstrakt metodlar sifatida e'lon qilingan."""
    assert FileStorageBackend.__abstractmethods__ == frozenset({"save", "get", "delete"})


def test_concrete_backend_must_implement_all_methods() -> None:
    """To'liq implementatsiya instansiyalanadi va shartnomaga amal qiladi."""

    class InMemoryBackend(FileStorageBackend):
        def __init__(self) -> None:
            self._store: dict[str, bytes] = {}

        def save(self, key: str, data: bytes, *, content_type: str | None = None) -> StoredFile:
            self._store[key] = data
            return StoredFile(
                storage_key=key,
                url=f"mem://{key}",
                size_bytes=len(data),
                content_type=content_type,
            )

        def get(self, key: str) -> bytes:
            return self._store[key]

        def delete(self, key: str) -> None:
            self._store.pop(key, None)

    backend = InMemoryBackend()
    stored = backend.save("a.txt", b"hello", content_type="text/plain")
    assert stored.size_bytes == 5
    assert backend.get("a.txt") == b"hello"
    backend.delete("a.txt")
    with pytest.raises(KeyError):
        backend.get("a.txt")
