"""Sof domen tiplari (transient strukturalar) — DB va I/O dan mustaqil.

Ushbu modul ball hisoblash (Baholash_Moduli) va reyting (Reyting_Moduli)
domen yadrosi uchun ishlatiladigan sof ma'lumot strukturalarini belgilaydi.
Bu tiplar `design.md` — "Domen ma'lumot strukturalari (transient, hisoblash
uchun)" bo'limiga aniq mos keladi va hech qanday I/O (DB, fayl, tarmoq) ga
bog'lanmaydi. Shu sababli ular property-based testlar uchun ideal nishon
hisoblanadi (sof, deterministik, framework'dan mustaqil).

Bog'liq talablar:
- R8.4: natija tarkibi (umumiy ball, kompetensiya ballari, kuchli/zaif tomonlar).
- R12.1: reyting yozuvi va saralash ko'rsatkichi (umumiy foiz).

Eslatma: bu yerda faqat tiplar e'lon qilinadi; hisoblash mantig'i (foiz,
daraja, reyting) keyingi vazifalarda (3.x, 4.x) sof funksiyalar sifatida
qo'shiladi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


class Level(str, Enum):
    """Baholash darajasi — foiz natijasiga mos toifa (R8.2, Glossary: Daraja).

    Oraliqlar (uzluksiz, har bir foiz aynan bitta darajaga tegishli):
    - Past:   0%   <= foiz <= 40%
    - O'rta:  40%  <  foiz <= 60%
    - Yaxshi: 60%  <  foiz <= 80%
    - Yuqori: 80%  <  foiz <= 100%

    `str` dan meros olinadi, shuning uchun a'zo qiymati bevosita o'zbekcha
    yorliqqa (`test_results.level` VARCHAR ustuni) teng bo'ladi. Python
    identifikatorlari (apostrofsiz) sifatida xavfsiz nomlardan foydalaniladi.
    """

    PAST = "Past"
    ORTA = "O'rta"
    YAXSHI = "Yaxshi"
    YUQORI = "Yuqori"

    def __str__(self) -> str:  # pragma: no cover - qulaylik uchun
        return self.value


@dataclass(frozen=True)
class AnsweredQuestion:
    """Bitta savolga berilgan javobning baholash uchun zarur ma'lumoti.

    design.md: ``AnsweredQuestion { question_id, competency_id?, awarded_score,
    max_score }``.

    Maydonlar:
    - ``question_id``: savol identifikatori.
    - ``awarded_score``: shu savol uchun yig'ilgan ball.
    - ``max_score``: shu savolning maksimal balli.
    - ``competency_id``: bog'langan kompetensiya identifikatori; ``None`` bo'lsa
      savol hech qanday kompetensiyaga bog'lanmagan (R8.5) va kompetensiya
      foizidan tashqarida qoldiriladi.
    """

    question_id: int
    awarded_score: Decimal
    max_score: Decimal
    competency_id: int | None = None


@dataclass(frozen=True)
class ScoreInput:
    """Ball hisoblash sof funksiyasiga uzatiladigan kirish to'plami.

    design.md: ``ScoreInput { answered: [AnsweredQuestion] }``.
    """

    answered: list[AnsweredQuestion] = field(default_factory=list)


@dataclass(frozen=True)
class CompetencyResult:
    """Bitta kompetensiya bo'yicha baholash natijasi.

    design.md ``ScoreResult.competencies`` elementi ``{competency_id,
    percentage}`` shaklida. Bu yerda qo'shimcha ``score`` va ``max_score``
    maydonlari ixtiyoriy (``None`` standart) sifatida saqlanadi, chunki ular
    ``competency_results`` jadvaliga (R8.3) persist qilinishi mumkin.

    Maydonlar:
    - ``competency_id``: kompetensiya identifikatori.
    - ``percentage``: shu kompetensiya bo'yicha foiz (0–100, 2 kasr xonasi).
    - ``score``: yig'ilgan ball (ixtiyoriy).
    - ``max_score``: maksimal ball (ixtiyoriy).
    """

    competency_id: int
    percentage: Decimal
    score: Decimal | None = None
    max_score: Decimal | None = None


@dataclass(frozen=True)
class ScoreResult:
    """To'liq baholash natijasi (transient).

    design.md::

        ScoreResult { total_score, max_score, percentage, level,
                      competencies: [{competency_id, percentage}],
                      strongest: [competency_id], weakest: [competency_id] }

    Maydonlar:
    - ``total_score``: umumiy yig'ilgan ball.
    - ``max_score``: umumiy maksimal ball.
    - ``percentage``: umumiy foiz (0–100, 2 kasr xonasi) (R8.1).
    - ``level``: aniqlangan daraja (R8.2).
    - ``competencies``: kompetensiya bo'yicha natijalar (R8.3).
    - ``strongest``: eng yuqori foizli kompetensiya(lar) identifikatorlari;
      teng qiymatda bir nechta bo'lishi mumkin (R8.4, R9.5, R9.6).
    - ``weakest``: eng past foizli kompetensiya(lar) identifikatorlari.
    """

    total_score: Decimal
    max_score: Decimal
    percentage: Decimal
    level: Level
    competencies: list[CompetencyResult] = field(default_factory=list)
    strongest: list[int] = field(default_factory=list)
    weakest: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class RatingRecord:
    """Reyting hisoblash uchun kirish yozuvi (transient).

    design.md: ``RatingRecord { entity_id, sort_metric (percentage),
    achieved_at }``.

    Maydonlar:
    - ``entity_id``: reyting subyekti (foydalanuvchi/tashkilot/hudud) identifikatori.
    - ``sort_metric``: saralash ko'rsatkichi — umumiy foiz (0–100, 2 kasr) (R12.1).
    - ``achieved_at``: natijaga erishilgan sana/vaqt; teng ko'rsatkichlarni
      o'suvchi tartibda joylashtirish uchun ishlatiladi (R12.3).
    """

    entity_id: int
    sort_metric: Decimal
    achieved_at: datetime


@dataclass(frozen=True)
class RankedEntry:
    """Reyting natijasidagi bitta o'rin (transient).

    design.md: ``RankedEntry { entity_id, rank, sort_metric }``.

    Maydonlar:
    - ``entity_id``: subyekt identifikatori.
    - ``rank``: reyting o'rni (1 dan boshlanadi); teng ko'rsatkichda bir xil
      rank beriladi va keyingi o'rin o'tkazib yuboriladi (R12.2, R12.3).
    - ``sort_metric``: saralash ko'rsatkichi (umumiy foiz).
    """

    entity_id: int
    rank: int
    sort_metric: Decimal


__all__ = [
    "Level",
    "AnsweredQuestion",
    "ScoreInput",
    "CompetencyResult",
    "ScoreResult",
    "RatingRecord",
    "RankedEntry",
]
