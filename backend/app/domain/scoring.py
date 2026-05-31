"""Baholash_Moduli domen yadrosi — sof funksiyalar (ball hisoblash).

Bu modul I/O (DB, fayl, tarmoq) qatlamidan mutlaqo mustaqil sof funksiyalarni
o'z ichiga oladi va shu sababli property-based testlar uchun asosiy nishon
hisoblanadi (design.md — "Scoring Algoritmi va Daraja Oraliqlari").

3.1-vazifa doirasida ikkita sof funksiya aniqlanadi:

- ``compute_percentage(collected, max_score)`` — umumiy foizni hisoblaydi
  (R8.1, R8.8).
- ``determine_level(percentage)`` — foizga mos darajani aniqlaydi (R8.2).

Hisoblash ``app.domain.types`` bilan izchil ravishda ``Decimal`` ustida olib
boriladi: kirish qiymatlari (``awarded_score``, ``max_score``) ham ``Decimal``,
natija (``ScoreResult.percentage``, ``CompetencyResult.percentage``) ham
``Decimal`` (``NUMERIC(5,2)`` ustuniga mos, 2 kasr xonasi).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.domain.types import (
    AnsweredQuestion,
    CompetencyResult,
    Level,
    ScoreResult,
)

# Foiz natijasi 2 kasr xonasigacha yaxlitlanadi (NUMERIC(5,2)) — R8.1.
_CENTS = Decimal("0.01")

# max == 0 holatida nolga bo'lmasdan qaytariladigan qiymat — R8.8.
_ZERO_PERCENT = Decimal("0.00")

# Daraja chegaralari (uzluksiz, o'zaro istisno oraliqlar) — R8.2.
_PAST_UPPER = Decimal(40)
_ORTA_UPPER = Decimal(60)
_YAXSHI_UPPER = Decimal(80)


def _to_decimal(value: Decimal | int | str) -> Decimal:
    """Kirishni xavfsiz ``Decimal`` ga keltiradi.

    ``Decimal`` va ``int`` to'g'ridan-to'g'ri ishlatiladi. ``float`` qiymatlar
    aniqlik yo'qotmaslik uchun ``str`` orqali aylantiriladi (masalan,
    ``float`` 0.1 ning ikkilik noaniqligini oldini olish).
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        # float'ni str orqali aylantirish ikkilik vakillik noaniqligini chetlaydi.
        return Decimal(str(value))
    return Decimal(value)


def compute_percentage(collected: Decimal | int, max_score: Decimal | int) -> Decimal:
    """Umumiy foizni ``yig'ilgan / maksimal * 100`` formulasi bilan hisoblaydi.

    Algoritm (design.md — "Umumiy foiz"):

    - ``max_score > 0`` bo'lsa: ``foiz = (collected / max_score) * 100``,
      so'ng 2 kasr xonasigacha **oddiy half-up** (banker emas) yaxlitlanadi
      (R8.1).
    - ``max_score == 0`` bo'lsa: nolga bo'lish amalisiz ``0.00`` qaytariladi
      (R8.8).

    Args:
        collected: yig'ilgan ball (manfiy bo'lmasligi kutiladi).
        max_score: maksimal ball (manfiy bo'lmasligi kutiladi).

    Returns:
        2 kasr xonasigacha yaxlitlangan foiz (``Decimal``). ``collected``
        ``max_score`` dan oshmasa, natija 0–100 oralig'ida bo'ladi.
    """
    max_dec = _to_decimal(max_score)
    if max_dec == 0:
        # R8.8: maksimal ball 0 bo'lsa, foiz nolga bo'linmasdan 0.00 deb belgilanadi.
        return _ZERO_PERCENT

    collected_dec = _to_decimal(collected)
    # Avval 100 ga ko'paytirib, so'ng bo'lish — yagona bo'lish bosqichi bilan
    # eng yuqori aniqlik (Decimal konteksti standart 28 muhim raqam).
    raw = (collected_dec * 100) / max_dec
    # Oddiy half-up yaxlitlash: x.xx5 -> yuqoriga (ROUND_HALF_UP).
    return raw.quantize(_CENTS, rounding=ROUND_HALF_UP)


def determine_level(percentage: Decimal | int) -> Level:
    """Foizga mos baholash darajasini aniqlaydi (R8.2).

    Uzluksiz, o'zaro istisno oraliqlar (design.md — "Daraja aniqlash"):

    - ``0 <= foiz <= 40``  -> :attr:`Level.PAST`
    - ``40 < foiz <= 60``  -> :attr:`Level.ORTA`
    - ``60 < foiz <= 80``  -> :attr:`Level.YAXSHI`
    - ``80 < foiz <= 100`` -> :attr:`Level.YUQORI`

    Chegara nuqtalari pastki oraliqqa tegishli (``<=`` yuqori chegara), shu
    sababli har bir foiz qiymati aynan bitta darajaga mos keladi (masalan,
    ``40 -> Past``, ``40.5 -> O'rta``, ``60 -> O'rta``, ``80 -> Yaxshi``).

    Funksiya total: hisoblangan foiz har doim 0–100 oralig'ida bo'ladi, biroq
    ehtiyot uchun chegaradan tashqari qiymatlar ham eng yaqin darajaga
    moslashtiriladi (manfiy -> Past, 100 dan katta -> Yuqori).

    Args:
        percentage: baholash foizi (odatda 0–100, ``Decimal``).

    Returns:
        Mos :class:`Level` enum a'zosi.
    """
    pct = _to_decimal(percentage)
    if pct <= _PAST_UPPER:
        return Level.PAST
    if pct <= _ORTA_UPPER:
        return Level.ORTA
    if pct <= _YAXSHI_UPPER:
        return Level.YAXSHI
    return Level.YUQORI


def compute_competency_scores(
    answered: list[AnsweredQuestion],
) -> list[CompetencyResult]:
    """Har bir kompetensiya bo'yicha foizni hisoblaydi (R8.3, R8.5, R8.8).

    Algoritm (design.md — "Kompetensiya bo'yicha foiz"):

    - Faqat ``competency_id is not None`` bo'lgan javoblar e'tiborga olinadi;
      bog'lanmagan savollar (``competency_id is None``) kompetensiya foizidan
      **tashqarida** qoldiriladi (R8.5). Bunday savollar umumiy ballga ta'sir
      qiladi (qarang: :func:`build_result`), biroq bu yerda hisobga olinmaydi.
    - Har bir kompetensiya uchun shu kompetensiyaga tegishli savollardan
      yig'ilgan ball va maksimal ball jamlanadi, so'ng
      :func:`compute_percentage` orqali foiz hisoblanadi (``max == 0 -> 0.00``,
      R8.8).

    Natija kompetensiyalar uchun deterministik tartibda (savollar birinchi
    uchragan tartib bo'yicha, ya'ni insertion order) qaytariladi — bu sof,
    qayta ishlab chiqariladigan natijani ta'minlaydi.

    Args:
        answered: baholangan javoblar ro'yxati.

    Returns:
        Har bir bog'langan kompetensiya uchun bitta :class:`CompetencyResult`
        (``score`` va ``max_score`` to'ldirilgan holda).
    """
    # Insertion order saqlanadi (Python 3.7+ dict): determinizm uchun.
    totals: dict[int, tuple[Decimal, Decimal]] = {}
    for item in answered:
        if item.competency_id is None:
            # R8.5: bog'lanmagan savol kompetensiya foizidan tashqarida.
            continue
        collected, maximum = totals.get(
            item.competency_id, (Decimal(0), Decimal(0))
        )
        totals[item.competency_id] = (
            collected + _to_decimal(item.awarded_score),
            maximum + _to_decimal(item.max_score),
        )

    return [
        CompetencyResult(
            competency_id=competency_id,
            percentage=compute_percentage(collected, maximum),
            score=collected,
            max_score=maximum,
        )
        for competency_id, (collected, maximum) in totals.items()
    ]


def build_result(answered: list[AnsweredQuestion]) -> ScoreResult:
    """To'liq baholash natijasini (transient) yig'adi (R8.3, R8.4, R8.5, R8.8).

    Yig'iladigan tarkib (design.md — "Natija qurish"):

    - **Umumiy ball** (``total_score``): barcha javoblardan yig'ilgan ball
      yig'indisi (bog'lanmagan savollar ham hisobga olinadi — R8.5).
    - **Umumiy maksimal ball** (``max_score``): barcha javoblar maksimal
      ballari yig'indisi.
    - **Umumiy foiz** (``percentage``): :func:`compute_percentage` orqali butun
      to'plam bo'yicha (``max == 0 -> 0.00``, R8.8).
    - **Daraja** (``level``): :func:`determine_level` orqali umumiy foizdan
      aniqlanadi (R8.2).
    - **Kompetensiya natijalari** (``competencies``):
      :func:`compute_competency_scores` natijasi (R8.3, R8.5).
    - **Kuchli/zaif kompetensiyalar** (``strongest`` / ``weakest``): mos ravishda
      eng yuqori va eng past kompetensiya foiziga ega kompetensiya
      identifikatorlari; teng qiymatda **barcha** teng kompetensiyalar
      qaytariladi (R8.4, R9.5, R9.6). Kompetensiya bo'lmasa, ikkala ro'yxat ham
      bo'sh bo'ladi.

    Funksiya sof va deterministik: bir xil kirish uchun har doim bir xil natija
    qaytaradi (kompetensiyalar va kuchli/zaif ro'yxatlar insertion order'da).

    Args:
        answered: baholangan javoblar ro'yxati.

    Returns:
        To'ldirilgan :class:`ScoreResult`.
    """
    total_score = sum((_to_decimal(a.awarded_score) for a in answered), Decimal(0))
    max_score = sum((_to_decimal(a.max_score) for a in answered), Decimal(0))
    percentage = compute_percentage(total_score, max_score)
    level = determine_level(percentage)

    competencies = compute_competency_scores(answered)
    strongest, weakest = _strongest_weakest(competencies)

    return ScoreResult(
        total_score=total_score,
        max_score=max_score,
        percentage=percentage,
        level=level,
        competencies=competencies,
        strongest=strongest,
        weakest=weakest,
    )


def _strongest_weakest(
    competencies: list[CompetencyResult],
) -> tuple[list[int], list[int]]:
    """Eng yuqori/past foizli kompetensiya identifikatorlarini ajratadi.

    Teng qiymatda barcha tenglar qaytariladi (R8.4, R9.5, R9.6). Tartib
    ``competencies`` ro'yxatidagi paydo bo'lish tartibini saqlaydi.
    """
    if not competencies:
        return [], []

    percentages = [c.percentage for c in competencies]
    highest = max(percentages)
    lowest = min(percentages)

    strongest = [c.competency_id for c in competencies if c.percentage == highest]
    weakest = [c.competency_id for c in competencies if c.percentage == lowest]
    return strongest, weakest


__all__ = [
    "compute_percentage",
    "determine_level",
    "compute_competency_scores",
    "build_result",
]
