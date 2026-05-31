"""4.1-vazifa: `compute_ranking` sof funksiyasi uchun namunaviy unit testlar.

Bu testlar aniq misollar va muhim chegaraviy holatlarni tekshiradi: kamayuvchi
saralash (R12.2), teng o'rinlar va o'tkazib yuborilgan ranklar (standart
musobaqa reytingi, R12.3), teng yozuvlarni sana bo'yicha o'suvchi tartiblash
(R12.3) va kirish permutatsiyasiga nisbatan determinizm. Property-based test
(Property 33) alohida vazifada (4.2) qo'shiladi.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.domain.rating import compute_ranking
from app.domain.types import RankedEntry, RatingRecord

BASE = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _record(entity_id: int, metric: str, *, days: int = 0) -> RatingRecord:
    return RatingRecord(
        entity_id=entity_id,
        sort_metric=Decimal(metric),
        achieved_at=BASE + timedelta(days=days),
    )


def test_empty_input_returns_empty_list() -> None:
    """Bo'sh kirish bo'sh ro'yxat qaytaradi."""
    assert compute_ranking([]) == []


def test_single_record_gets_rank_one() -> None:
    """Yagona yozuv 1-o'rinni oladi."""
    result = compute_ranking([_record(7, "55.50")])
    assert result == [RankedEntry(entity_id=7, rank=1, sort_metric=Decimal("55.50"))]


def test_sorted_descending_by_metric() -> None:
    """Yozuvlar saralash ko'rsatkichi bo'yicha kamayuvchi tartibda chiqadi (R12.2)."""
    result = compute_ranking([_record(1, "70.00"), _record(2, "90.00"), _record(3, "80.00")])
    assert [(e.entity_id, e.rank) for e in result] == [(2, 1), (3, 2), (1, 3)]


def test_standard_competition_ranking_skips_after_ties() -> None:
    """Teng qiymatlar bir xil rank oladi, keyingi o'rin o'tkazib yuboriladi (R12.3).

    Ko'rsatkichlar [90, 80, 80, 70] -> ranklar [1, 2, 2, 4].
    """
    result = compute_ranking(
        [
            _record(1, "90.00"),
            _record(2, "80.00", days=1),
            _record(3, "80.00", days=2),
            _record(4, "70.00"),
        ]
    )
    assert [(e.entity_id, e.rank) for e in result] == [(1, 1), (2, 2), (3, 2), (4, 4)]


def test_ties_ordered_by_achieved_at_ascending() -> None:
    """Teng ko'rsatkichli yozuvlar sana bo'yicha o'suvchi (eng erta birinchi) (R12.3)."""
    earlier = _record(10, "80.00", days=1)
    later = _record(20, "80.00", days=5)
    result = compute_ranking([later, earlier])
    assert [e.entity_id for e in result] == [10, 20]
    assert all(e.rank == 1 for e in result)


def test_deterministic_under_input_permutation() -> None:
    """Bir xil to'plam qanday tartibda berilsa ham, bir xil natija (determinizm)."""
    records = [
        _record(1, "90.00"),
        _record(2, "80.00", days=1),
        _record(3, "80.00", days=2),
        _record(4, "70.00"),
    ]
    forward = compute_ranking(records)
    backward = compute_ranking(list(reversed(records)))
    assert forward == backward


def test_input_list_not_mutated() -> None:
    """Kirish ro'yxati o'zgartirilmaydi."""
    records = [_record(1, "70.00"), _record(2, "90.00")]
    snapshot = list(records)
    compute_ranking(records)
    assert records == snapshot


# ----------------------------------------------------------------------
# 4.3-vazifa: anonimlashtirish (R12.4) va natijasiz foydalanuvchini
# reytingdan chiqarish (R12.5) uchun namunaviy unit testlar.
# Property-based testlar (Property 34, 35) alohida vazifalarda (4.4, 4.5).
# ----------------------------------------------------------------------

from app.domain.rating import (  # noqa: E402
    AnonymizedRatingEntry,
    OutOfRankingEntry,
    RatingParticipant,
    build_anonymized_rating,
    exclude_unranked,
    is_ranked,
)


def _participant(
    entity_id: int,
    metric: str | None,
    *,
    days: int = 0,
    region: str = "Toshkent",
    org_type: str = "MTT",
    position: str = "Rahbar",
) -> RatingParticipant:
    return RatingParticipant(
        entity_id=entity_id,
        percentage=Decimal(metric) if metric is not None else None,
        region=region,
        org_type=org_type,
        position=position,
        achieved_at=(BASE + timedelta(days=days)) if metric is not None else None,
    )


def test_is_ranked_true_when_percentage_present() -> None:
    """Yakunlangan natijasi bor subyekt reytingga kiradi (R12.5)."""
    assert is_ranked(_participant(1, "55.00")) is True


def test_is_ranked_false_when_percentage_none() -> None:
    """Natijasi yo'q subyekt reytingdan tashqarida (R12.5)."""
    assert is_ranked(_participant(1, None)) is False


def test_exclude_unranked_partitions_by_result_presence() -> None:
    """Natijasi borlar reytingli, yo'qlar reytingsiz qismga ajraladi (R12.5)."""
    partition = exclude_unranked(
        [_participant(1, "80.00"), _participant(2, None), _participant(3, "60.00")]
    )
    assert [r.entity_id for r in partition.ranked] == [1, 3]
    assert [p.entity_id for p in partition.unranked] == [2]


def test_anonymized_entry_excludes_identifying_fields() -> None:
    """Anonim yozuv faqat hudud/turi/lavozim/ko'rsatkich/rank maydonlarini oshkor qiladi (R12.4)."""
    entry_fields = set(AnonymizedRatingEntry.__dataclass_fields__)
    assert entry_fields == {
        "rank",
        "percentage",
        "region",
        "org_type",
        "position",
        "is_requester",
    }
    # Bevosita identifikatsiyalovchi maydonlar mavjud emasligini aniq tasdiqlaymiz.
    for forbidden in ("full_name", "name", "phone", "entity_id", "user_id"):
        assert forbidden not in entry_fields


def test_build_anonymized_rating_orders_and_ranks() -> None:
    """Anonim reyting kamayuvchi tartibda saralanadi va rank oladi (R12.2, R12.4)."""
    rating = build_anonymized_rating(
        [
            _participant(1, "70.00", region="A"),
            _participant(2, "90.00", region="B"),
            _participant(3, "80.00", region="C"),
        ]
    )
    assert [(e.rank, e.region, e.percentage) for e in rating.ranked] == [
        (1, "B", Decimal("90.00")),
        (2, "C", Decimal("80.00")),
        (3, "A", Decimal("70.00")),
    ]
    assert rating.out_of_ranking == []


def test_build_anonymized_rating_marks_requester() -> None:
    """So'rovchining o'z yozuvi ajratib ko'rsatiladi (R12.4)."""
    rating = build_anonymized_rating(
        [_participant(1, "70.00"), _participant(2, "90.00")],
        requester_id=1,
    )
    by_requester = {e.is_requester: e.percentage for e in rating.ranked}
    assert by_requester[True] == Decimal("70.00")
    assert by_requester[False] == Decimal("90.00")
    assert sum(1 for e in rating.ranked if e.is_requester) == 1


def test_build_anonymized_rating_excludes_resultless_user() -> None:
    """Natijasi yo'q foydalanuvchi reytingdan tashqarida, rank berilmaydi (R12.5)."""
    rating = build_anonymized_rating(
        [_participant(1, "70.00"), _participant(2, None, region="Z")],
        requester_id=2,
    )
    assert [e.rank for e in rating.ranked] == [1]
    assert rating.out_of_ranking == [
        OutOfRankingEntry(
            region="Z", org_type="MTT", position="Rahbar", is_requester=True
        )
    ]


def test_build_anonymized_rating_does_not_mutate_input() -> None:
    """Kirish ro'yxati o'zgartirilmaydi."""
    participants = [_participant(1, "70.00"), _participant(2, None)]
    snapshot = list(participants)
    build_anonymized_rating(participants)
    assert participants == snapshot
