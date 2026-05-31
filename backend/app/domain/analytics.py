"""Analitika va Hisobot domen yadrosi — sof agregatsiya funksiyalari.

Bu modul `Analitika_Moduli` (R9) va `Hisobot_Moduli` (R15) uchun I/O'dan
(DB, fayl, tarmoq) mustaqil sof funksiyalarni belgilaydi. Sof bo'lgani uchun
property-based testlar uchun ideal nishon hisoblanadi (deterministik,
framework'dan mustaqil) — `design.md`, "Testing Strategy" bo'limiga qarang.

Barcha hisob-kitoblar `Decimal` asosida bajariladi (foizlar 0–100 oralig'ida,
odatda 2 kasr xonasi).

----------------------------------------------------------------------
USHBU FAYL BO'LIMLARGA AJRATILGAN:
  1. Kirish/chiqish tiplari (umumiy)
  2. O'sish dinamikasi va farq (5.1-vazifa) — `growth_dynamics`, `growth_diff`
  3. Jamlangan agregatsiya — kirish/chiqish tiplari (5.4-vazifa)
  4. Jamlangan agregatsiya funksiyalari (5.4-vazifa) — `aggregate_average`,
     `aggregate_competencies`, `aggregate_by_section`
----------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol, runtime_checkable

# ======================================================================
# 1. Kirish/chiqish tiplari (umumiy)
# ======================================================================


@runtime_checkable
class DatedPercentage(Protocol):
    """Sana bilan belgilangan umumiy foizni ifodalovchi struktura protokoli.

    Analitika funksiyalari faqat ikki maydonga tayanadi: ``percentage`` (umumiy
    foiz) va ``achieved_at`` (natijaga erishilgan sana/vaqt). Shu sababli ham
    quyidagi ``DatedResult`` dataclassi, ham shu protokolga mos keladigan
    boshqa "RatingRecord-ga o'xshash" obyektlar (``percentage`` + ``achieved_at``
    maydonlariga ega) kirish sifatida qabul qilinadi.
    """

    @property
    def percentage(self) -> Decimal: ...

    @property
    def achieved_at(self) -> datetime: ...


@dataclass(frozen=True)
class DatedResult:
    """Sana bilan belgilangan bitta test natijasining umumiy foizi (transient).

    O'sish dinamikasi (R9.1) va individual dinamika (R15.5) hisoblash uchun
    minimal kirish yozuvi. DB'dan mustaqil; faqat foiz va sana saqlanadi.

    Maydonlar:
    - ``percentage``: shu natijaning umumiy foizi (0–100, odatda 2 kasr xonasi).
    - ``achieved_at``: natijaga erishilgan sana/vaqt; xronologik tartiblash
      uchun ishlatiladi (eng eskidan eng yangiga).
    """

    percentage: Decimal
    achieved_at: datetime


@dataclass(frozen=True)
class GrowthPoint:
    """O'sish dinamikasidagi bitta nuqta — sana bilan belgilangan foiz (R9.1).

    Maydonlar:
    - ``achieved_at``: natija sanasi/vaqti.
    - ``percentage``: shu natijaning umumiy foizi.
    """

    achieved_at: datetime
    percentage: Decimal


# ======================================================================
# 2. O'sish dinamikasi va farq (5.1-vazifa)
# ======================================================================


def growth_dynamics(results: list[DatedPercentage]) -> list[GrowthPoint]:
    """Umumiy foizlarni xronologik (o'suvchi) tartibda qaytaradi (R9.1, R15.5).

    Natijalar sana (``achieved_at``) bo'yicha eng eskidan eng yangiga qarab
    tartiblanadi va har bir nuqta o'z sanasi bilan belgilanadi. Saralash
    barqaror (stable): bir xil sanaga ega yozuvlar kirish tartibini saqlaydi.

    Bo'sh kirish bo'sh ketma-ketlikni qaytaradi (R9.7 — muvaffaqiyatli bo'sh
    holat); funksiya hech qachon xato ko'tarmaydi.

    Args:
        results: ``percentage`` va ``achieved_at`` maydonlariga ega yozuvlar
            (masalan, ``DatedResult``).

    Returns:
        ``GrowthPoint`` ro'yxati, sana bo'yicha o'suvchi tartibda.

    Validates: Requirements 9.1, 15.5
    """
    ordered = sorted(results, key=lambda r: r.achieved_at)
    return [
        GrowthPoint(achieved_at=r.achieved_at, percentage=r.percentage)
        for r in ordered
    ]


def growth_diff(results: list[DatedPercentage]) -> Decimal | None:
    """Joriy (eng so'nggi) va bevosita oldingi natija foizi farqini qaytaradi.

    Natijalar sana bo'yicha xronologik tartiblanadi; eng so'nggi natija foizidan
    bevosita oldingi natija foizi ayiriladi. Farqning ishorasi tabiiy ravishda
    to'g'ri bo'ladi:
    - musbat — o'sish,
    - manfiy — pasayish,
    - nol (``Decimal("0")``) — o'zgarishsiz.

    Agar natija bitta yoki umuman bo'lmasa, taqqoslash mumkin emas va farq
    "mavjud emas" deb belgilanadi — bu holatda ``None`` qaytariladi (sentinel).
    Bu R9.4 dagi "mavjud emas" holatini aniq modellashtiradi.

    Args:
        results: ``percentage`` va ``achieved_at`` maydonlariga ega yozuvlar.

    Returns:
        ``Decimal`` farq (current − previous) ishora bilan, yoki natija ikkitadan
        kam bo'lsa ``None`` ("mavjud emas").

    Validates: Requirements 9.3, 9.4
    """
    if len(results) < 2:
        return None
    ordered = sorted(results, key=lambda r: r.achieved_at)
    current = ordered[-1].percentage
    previous = ordered[-2].percentage
    return current - previous


# ======================================================================
# 3. Jamlangan agregatsiya — kirish/chiqish tiplari (5.4-vazifa)
# ======================================================================
#
# Foiz natijalari 2 kasr xonasigacha (NUMERIC(5,2)) yaxlitlanadi va barcha
# hisob-kitoblar `Decimal` ustida olib boriladi (R15.1, R15.2). Bo'sh doirada
# (hech qanday yakunlangan natija bo'lmasa) funksiyalar xato ko'tarmaydi, balki
# nol qiymatli/bo'sh muvaffaqiyatli holatni qaytaradi (R15.7).

# Jamlangan o'rtacha 2 kasr xonasigacha yaxlitlanadi — scoring._CENTS bilan izchil.
_CENTS = Decimal("0.01")

# Doira bo'sh bo'lganda (natija yo'q) qaytariladigan nol o'rtacha — R15.7.
_ZERO_PERCENT = Decimal("0.00")


@dataclass(frozen=True)
class AggregateResult:
    """Jamlash uchun bitta yakunlangan natija (transient) — R15.1, R15.2.

    `aggregate_average` (umumiy o'rtacha) va `aggregate_competencies` (kompetensiya
    kesimi) funksiyalari uchun minimal kirish yozuvi. DB'dan mustaqil.

    Maydonlar:
    - ``user_id``: natija egasi (rahbar) identifikatori. Hozircha bevosita
      hisobda ishlatilmaydi, biroq natijani manbaga bog'lash va kelajakda
      takror foydalanuvchini ajratish uchun saqlanadi.
    - ``percentage``: shu natijaning umumiy foizi (0–100, odatda 2 kasr xonasi).
    - ``competencies``: kompetensiya identifikatoridan shu natijadagi kompetensiya
      foiziga moslik (``{competency_id: percentage}``). Bo'sh bo'lishi mumkin
      (natijada baholangan kompetensiya bo'lmasa).
    """

    user_id: int
    percentage: Decimal
    competencies: Mapping[int, Decimal] = field(default_factory=dict)


@dataclass(frozen=True)
class SectionRecord:
    """Kesim (hudud/tashkilot) bo'yicha bitta rahbar yozuvi (transient) — R15.3, R15.4.

    `aggregate_by_section` har bir kesim uchun rahbarlar soni, test topshirganlar
    soni va o'rtacha ballni jamlaganda ushbu yozuvlardan foydalanadi. Har bir
    ``SectionRecord`` **bitta rahbarni** ifodalaydi (yuqori qatlamda foydalanuvchi
    bo'yicha yagonalashtirilgan deb taxmin qilinadi).

    Maydonlar:
    - ``user_id``: rahbar identifikatori. Rahbarlar soni shu identifikatorlar
      bo'yicha noyob (distinct) sanaladi.
    - ``percentage``: rahbarning yakunlangan natijasi umumiy foizi (0–100), yoki
      rahbar hali test topshirmagan bo'lsa ``None``. ``None`` yozuv rahbarlar
      soniga kiradi, lekin test topshirganlar soni va o'rtacha balldan tashqarida
      qoladi.
    - ``region``: hudud kesimi kaliti (ixtiyoriy).
    - ``organization``: tashkilot kesimi kaliti (ixtiyoriy).
    """

    user_id: int
    percentage: Decimal | None = None
    region: Hashable | None = None
    organization: Hashable | None = None


@dataclass(frozen=True)
class CompetencyAggregate:
    """Bitta kompetensiya bo'yicha jamlangan foiz (transient) — R15.2.

    Maydonlar:
    - ``competency_id``: kompetensiya identifikatori.
    - ``aggregate_percentage``: shu kompetensiyaga oid barcha natijalar
      foizlarining o'rtachasi (0–100, 2 kasr xonasi).
    """

    competency_id: int
    aggregate_percentage: Decimal


@dataclass(frozen=True)
class CompetencyExtremes:
    """Kompetensiya kesimidagi jamlanma va eng past/yuqori kompetensiyalar — R15.2.

    Maydonlar:
    - ``aggregates``: har bir kompetensiya bo'yicha jamlangan foiz, kompetensiya
      identifikatori bo'yicha o'suvchi tartibda (deterministik).
    - ``lowest``: eng past jamlangan foizli kompetensiya(lar) identifikatorlari;
      teng qiymatda barchasi qaytariladi, identifikatorlar o'suvchi tartibda.
    - ``highest``: eng yuqori jamlangan foizli kompetensiya(lar) identifikatorlari;
      teng qiymatda barchasi qaytariladi, identifikatorlar o'suvchi tartibda.
    """

    aggregates: tuple[CompetencyAggregate, ...] = ()
    lowest: tuple[int, ...] = ()
    highest: tuple[int, ...] = ()


@dataclass(frozen=True)
class SectionSummary:
    """Bitta kesim (hudud yoki tashkilot) bo'yicha jamlangan ko'rsatkichlar — R15.3, R15.4.

    Maydonlar:
    - ``leaders_count``: kesimdagi noyob rahbarlar soni.
    - ``test_takers_count``: kesimda test topshirgan (yakunlangan natijasi bor)
      noyob rahbarlar soni.
    - ``average_score``: kesimdagi yakunlangan natijalar umumiy foizlarining
      o'rtachasi (0–100, 2 kasr); test topshirgan rahbar bo'lmasa ``0.00`` (R15.7).
    """

    leaders_count: int
    test_takers_count: int
    average_score: Decimal


def _mean_percentage(values: list[Decimal]) -> Decimal:
    """Foizlar ro'yxatining arifmetik o'rtachasini 2 kasr xonasida qaytaradi.

    Yagona bo'lish bosqichi bilan ``Decimal`` aniqligini saqlaydi va oddiy
    half-up (banker emas) yaxlitlash qo'llaydi — `scoring.compute_percentage`
    bilan izchil. Bo'sh ro'yxat uchun ``0.00`` qaytaradi (R15.7).
    """
    if not values:
        return _ZERO_PERCENT
    total = sum(values, Decimal(0))
    raw = total / Decimal(len(values))
    return raw.quantize(_CENTS, rounding=ROUND_HALF_UP)


# ======================================================================
# 4. Jamlangan agregatsiya funksiyalari (5.4-vazifa)
# ======================================================================


def aggregate_average(results: list[AggregateResult]) -> Decimal:
    """Yakunlangan natijalar umumiy foizlarining arifmetik o'rtachasini qaytaradi.

    Barcha natijalarning ``percentage`` qiymatlari o'rtachasi hisoblanadi, 0–100
    oralig'ida bo'ladi (kirish foizlari shu oraliqda bo'lsa) va 2 kasr xonasigacha
    oddiy half-up yaxlitlanadi (R15.1).

    Bo'sh kirish (natija yo'q) muvaffaqiyatli ravishda ``Decimal("0.00")``
    qaytaradi — bu R15.7 dagi nol qiymatli bo'sh holat semantikasiga mos keladi;
    funksiya hech qachon xato ko'tarmaydi.

    Args:
        results: ``AggregateResult`` yozuvlari (har biri umumiy ``percentage`` ga ega).

    Returns:
        2 kasr xonasigacha yaxlitlangan o'rtacha foiz (``Decimal``), yoki kirish
        bo'sh bo'lsa ``Decimal("0.00")``.

    Validates: Requirements 15.1
    """
    return _mean_percentage([r.percentage for r in results])


def aggregate_competencies(results: list[AggregateResult]) -> CompetencyExtremes:
    """Kompetensiya bo'yicha jamlangan foizlarni va eng past/yuqori kompetensiyalarni hisoblaydi.

    Har bir kompetensiya uchun jamlangan foiz — shu kompetensiya barcha
    natijalardagi foizlarining o'rtachasi (2 kasr, half-up). So'ng eng past
    jamlangan foizli kompetensiya(lar) ``lowest``, eng yuqori jamlangan foizli
    kompetensiya(lar) ``highest`` sifatida qaytariladi; teng qiymatda barchasi
    qaytariladi (R15.2).

    Taqqoslash yaxlitlangan jamlangan foizlar ustida olib boriladi, shu sababli
    ``lowest``/``highest`` hisobotda ko'rsatiladigan qiymatlarga to'liq mos keladi.
    Natija deterministik: ``aggregates`` va teng holatdagi identifikatorlar
    kompetensiya identifikatori bo'yicha o'suvchi tartibda joylashtiriladi.

    Bo'sh kirish yoki birorta ham baholangan kompetensiya bo'lmaganda, bo'sh
    ``aggregates``, ``lowest`` va ``highest`` bilan muvaffaqiyatli bo'sh holat
    qaytariladi (R15.7).

    Eslatma: faqat bitta kompetensiya bo'lsa, u ham eng past, ham eng yuqori
    hisoblanadi (yagona qiymat bir vaqtning o'zida minimum va maksimum).

    Args:
        results: ``AggregateResult`` yozuvlari; har biri ``competencies``
            (``{competency_id: percentage}``) moslikka ega.

    Returns:
        ``CompetencyExtremes`` — har bir kompetensiya bo'yicha jamlangan foiz va
        eng past/yuqori kompetensiya identifikatorlari.

    Validates: Requirements 15.2
    """
    # Kompetensiya identifikatori -> shu kompetensiyaning barcha natijalardagi foizlari.
    buckets: dict[int, list[Decimal]] = {}
    for result in results:
        for competency_id, percentage in result.competencies.items():
            buckets.setdefault(competency_id, []).append(percentage)

    if not buckets:
        return CompetencyExtremes()

    # Determinizm uchun kompetensiya identifikatori bo'yicha o'suvchi tartiblash.
    aggregates = tuple(
        CompetencyAggregate(
            competency_id=competency_id,
            aggregate_percentage=_mean_percentage(buckets[competency_id]),
        )
        for competency_id in sorted(buckets)
    )

    values = [agg.aggregate_percentage for agg in aggregates]
    lowest_value = min(values)
    highest_value = max(values)

    lowest = tuple(
        agg.competency_id for agg in aggregates if agg.aggregate_percentage == lowest_value
    )
    highest = tuple(
        agg.competency_id for agg in aggregates if agg.aggregate_percentage == highest_value
    )

    return CompetencyExtremes(aggregates=aggregates, lowest=lowest, highest=highest)


def aggregate_by_section(
    records: list[SectionRecord],
    key: str | Callable[[SectionRecord], Hashable],
) -> dict[Hashable, SectionSummary]:
    """Yozuvlarni kesim (hudud yoki tashkilot) bo'yicha guruhlab jamlaydi.

    Har bir kesim uchun quyidagilar hisoblanadi (R15.3, R15.4):
    - ``leaders_count`` — kesimdagi noyob rahbarlar (``user_id``) soni;
    - ``test_takers_count`` — kesimda yakunlangan natijasi bor (``percentage is
      not None``) noyob rahbarlar soni;
    - ``average_score`` — kesimdagi yakunlangan natijalar foizlarining o'rtachasi
      (2 kasr, half-up); test topshirgan rahbar bo'lmasa ``0.00`` (R15.7).

    ``key`` kesim o'lchamini tanlaydi: maydon nomi (masalan ``"region"`` yoki
    ``"organization"``) yoki yozuvdan kesim qiymatini ajratuvchi chaqiriladigan
    funksiya (``Callable[[SectionRecord], Hashable]``) bo'lishi mumkin.

    Guruhlash kirish tartibiga nisbatan deterministik: natija lug'ati kesim
    qiymati birinchi uchragan tartibda joylashtiriladi. Bo'sh kirish bo'sh
    lug'at qaytaradi (R15.7).

    Args:
        records: ``SectionRecord`` yozuvlari (har biri bitta rahbarni ifodalaydi).
        key: kesim maydoni nomi yoki kesim qiymatini ajratuvchi funksiya.

    Returns:
        Kesim qiymatidan ``SectionSummary`` ga moslik (``dict``).

    Validates: Requirements 15.3, 15.4
    """
    extract: Callable[[SectionRecord], Hashable]
    if isinstance(key, str):
        field_name = key

        def extract(record: SectionRecord) -> Hashable:
            return getattr(record, field_name)

    else:
        extract = key

    # Kesim qiymati -> (noyob rahbarlar, noyob test topshirganlar, natija foizlari).
    leaders: dict[Hashable, set[int]] = {}
    test_takers: dict[Hashable, set[int]] = {}
    percentages: dict[Hashable, list[Decimal]] = {}

    for record in records:
        section = extract(record)
        if section not in leaders:
            leaders[section] = set()
            test_takers[section] = set()
            percentages[section] = []
        leaders[section].add(record.user_id)
        if record.percentage is not None:
            test_takers[section].add(record.user_id)
            percentages[section].append(record.percentage)

    return {
        section: SectionSummary(
            leaders_count=len(leaders[section]),
            test_takers_count=len(test_takers[section]),
            average_score=_mean_percentage(percentages[section]),
        )
        for section in leaders
    }


__all__ = [
    "DatedPercentage",
    "DatedResult",
    "GrowthPoint",
    "growth_dynamics",
    "growth_diff",
    # 5.4-vazifa — jamlangan agregatsiya
    "AggregateResult",
    "SectionRecord",
    "CompetencyAggregate",
    "CompetencyExtremes",
    "SectionSummary",
    "aggregate_average",
    "aggregate_competencies",
    "aggregate_by_section",
]
