"""Ekspert_Moduli domen yadrosi — sof funksiyalar (R13).

Ushbu modul ekspert baholashning sof (I/O'siz, deterministik) mantig'ini
ta'minlaydi:

- :func:`validate_expert_scores` — oltita mezon bo'yicha kiritilgan baholarni
  tekshiradi (har biri 1–5 oralig'idagi butun son va olti mezon to'liq)
  (R13.1, R13.3, R13.4).
- :func:`compute_expert_average` — yaroqli baholardan ekspert o'rtacha bahosini
  (``yig'indi / 6``) hisoblaydi; natija 1.00–5.00 oralig'ida, 2 kasr xonasigacha
  ``ROUND_HALF_UP`` bilan yaxlitlanadi (R13.2).

design.md ("Ekspert o'rtacha bahosi (R13.2)") ga muvofiq::

    ekspert_baho = (m1 + m2 + m3 + m4 + m5 + m6) / 6,  har biri 1..5 butun
    natija 1.00..5.00 oralig'ida, 2 kasr xonasigacha.

Mezon nomlari `expert_reviews` jadvali maydonlariga (design.md) aniq mos keladi.
Bu funksiyalar hech qanday I/O (DB, fayl, tarmoq) ga bog'lanmaydi va shu sababli
property-based testlar (Property 36, 37) uchun ideal nishon hisoblanadi.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal

# --- Konstantalar ---------------------------------------------------------

#: Eng past yaroqli mezon bahosi (R13.1).
MIN_SCORE = 1
#: Eng yuqori yaroqli mezon bahosi (R13.1).
MAX_SCORE = 5

#: Oltita baholash mezoni — `expert_reviews` jadvali maydonlariga mos (R13.1).
#: Tartib o'rtacha hisoblashga ta'sir qilmaydi, ammo deterministik xato
#: xabarlari uchun belgilangan tartibda saqlanadi.
EXPERT_CRITERIA: tuple[str, ...] = (
    "management_culture",  # boshqaruv madaniyati
    "teamwork",  # jamoaviy ishlash
    "pedagogical_process",  # pedagogik jarayonlarni tashkil etish
    "innovation",  # innovatsion yondashuv
    "documentation",  # hujjatlar bilan ishlash
    "strategic_planning",  # strategik rejalashtirish
)

#: Mezonlar soni (o'rtacha shu songa bo'linadi) (R13.2).
CRITERIA_COUNT = len(EXPERT_CRITERIA)

#: Yaxlitlash aniqligi: 2 kasr xonasi (R13.2).
_TWO_PLACES = Decimal("0.01")


# --- Domen istisnosi ------------------------------------------------------


class ExpertScoreValidationError(ValueError):
    """Ekspert baholash validatsiyasi muvaffaqiyatsiz bo'lganda ko'tariladi.

    `errors` atributida har bir yaroqsiz/to'ldirilmagan mezon bo'yicha aniq
    (inson o'qiy oladigan) xato xabarlari ro'yxati saqlanadi (R13.3, R13.4).
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors: list[str] = list(errors)
        super().__init__("; ".join(self.errors) if self.errors else "yaroqsiz ekspert baholash")


# --- Sof funksiyalar ------------------------------------------------------


def validate_expert_scores(scores: Mapping[str, object]) -> list[str]:
    """Oltita mezon bo'yicha ekspert baholarini tekshiradi (R13.1, R13.3, R13.4).

    Qoidalar:
    - Oltita mezon (``EXPERT_CRITERIA``) ning har biri mavjud bo'lishi shart;
      yo'q bo'lsa "to'ldirilmagan mezon" xatosi qo'shiladi (R13.4).
    - Har bir mezon qiymati butun son (``int``) bo'lishi shart; ``bool`` va
      ``float`` kabi turlar butun son sifatida qabul qilinmaydi (R13.3).
    - Har bir mezon qiymati ``MIN_SCORE``–``MAX_SCORE`` (1–5) oralig'ida bo'lishi
      shart (R13.1, R13.3).

    Args:
        scores: mezon nomi -> baho ko'rinishidagi moslama (mapping).

    Returns:
        Xato xabarlari ro'yxati. Bo'sh ro'yxat — barcha mezonlar yaroqli.
        (Sof funksiya: hech qanday istisno ko'tarmaydi, holatni o'zgartirmaydi.)

    Raises:
        TypeError: ``scores`` moslama (``Mapping``) bo'lmasa — bu shartnoma
            buzilishi (validatsiya emas).
    """
    if not isinstance(scores, Mapping):
        raise TypeError("ekspert baholari mezon nomi -> baho moslamasi bo'lishi kerak")

    errors: list[str] = []
    for criterion in EXPERT_CRITERIA:
        if criterion not in scores:
            errors.append(f"'{criterion}' mezoni to'ldirilmagan")
            continue

        value = scores[criterion]
        # `bool` — `int` ning quyi sinfi; uni butun son sifatida qabul qilmaymiz.
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"'{criterion}' mezoni 1–5 oralig'idagi butun son bo'lishi kerak")
            continue

        if value < MIN_SCORE or value > MAX_SCORE:
            errors.append(
                f"'{criterion}' mezoni {MIN_SCORE}–{MAX_SCORE} oralig'ida bo'lishi kerak"
            )

    return errors


def compute_expert_average(scores: Mapping[str, int]) -> Decimal:
    """Ekspert o'rtacha bahosini hisoblaydi (R13.2).

    Avval baholar :func:`validate_expert_scores` orqali tekshiriladi; yaroqsiz
    bo'lsa, hech qanday qiymat qaytarilmaydi va
    :class:`ExpertScoreValidationError` ko'tariladi (R13.3, R13.4) — shu tariqa
    yaroqsiz ma'lumotdan o'rtacha hisoblanmaydi.

    Yaroqli baholar uchun::

        o'rtacha = (m1 + m2 + m3 + m4 + m5 + m6) / 6

    natija 2 kasr xonasigacha ``ROUND_HALF_UP`` bilan yaxlitlanadi. Har bir mezon
    1–5 oralig'ida bo'lgani uchun natija doimo 1.00–5.00 oralig'ida bo'ladi.

    Args:
        scores: mezon nomi -> baho (1–5 butun son) moslamasi.

    Returns:
        Ekspert o'rtacha bahosi — ``Decimal``, 2 kasr xonasi, 1.00–5.00.

    Raises:
        ExpertScoreValidationError: bironta mezon yaroqsiz yoki to'ldirilmagan
            bo'lsa.
    """
    errors = validate_expert_scores(scores)
    if errors:
        raise ExpertScoreValidationError(errors)

    total = sum(int(scores[criterion]) for criterion in EXPERT_CRITERIA)
    average = Decimal(total) / Decimal(CRITERIA_COUNT)
    return average.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


__all__ = [
    "MIN_SCORE",
    "MAX_SCORE",
    "EXPERT_CRITERIA",
    "CRITERIA_COUNT",
    "ExpertScoreValidationError",
    "validate_expert_scores",
    "compute_expert_average",
]
