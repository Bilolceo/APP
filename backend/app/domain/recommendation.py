"""Tavsiya_Moduli — tavsiya tanlash sof mantig'i (6.4-vazifa).

Ushbu modul kompetensiya + daraja bo'yicha rivojlanish tavsiyasini tanlovchi
sof (pure) funksiyani belgilaydi. Funksiya hech qanday I/O (DB, fayl, tarmoq)
bajarmaydi: mavjud tavsiyalar to'plami kirish parametri sifatida uzatiladi va
tanlangan tavsiyalar qaytariladi. Shu sababli u property-based testlar uchun
ideal nishon hisoblanadi (sof, deterministik, framework'dan mustaqil).

Bog'liq talablar va dizayn:
- R10.1: har bir baholangan kompetensiya va uning darajasiga (Past/O'rta/
  Yaxshi/Yuqori) mos tavsiya avtomatik tanlanadi.
- R10.4: agar (kompetensiya, daraja) kombinatsiyasi uchun aniq mos tavsiya
  mavjud bo'lmasa, umumiy standart rivojlanish tavsiyasi tanlanadi — shu tarzda
  HAR DOIM tavsiya tanlanadi (totallik, design.md Property 28).
- design.md (Data Models): ``recommendations(id, competency_id FK NULL, level,
  text)`` — ``competency_id IS NULL`` + daraja = umumiy standart tavsiya.
- design.md (Data Models): ``result_recommendations(result_id, competency_id,
  level, recommendation_id, text_snapshot)`` — tanlangan tavsiya natijaga
  bog'lab persist qilinadi; bu yerda persistensiyasiz, sof tanlash qaytariladi.

Eslatma: daraja (Level) bu modulga KIRISH sifatida uzatiladi. Foiz -> daraja
konversiyasi Baholash_Moduli (`determine_level`, 3.1-vazifa) mas'uliyatidir;
bu modul faqat allaqachon baholangan (kompetensiya, daraja) juftliklari uchun
tavsiya tanlaydi va shu tarzda mas'uliyatlar ajratiladi.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.domain.types import Level

# Darajalarni deterministik tartiblash uchun (Past < O'rta < Yaxshi < Yuqori).
_LEVEL_ORDER: dict[Level, int] = {
    Level.PAST: 0,
    Level.ORTA: 1,
    Level.YAXSHI: 2,
    Level.YUQORI: 3,
}


@dataclass(frozen=True)
class Recommendation:
    """Mavjud tavsiya yozuvi (``recommendations`` jadvaliga mos, transient).

    Maydonlar:
    - ``competency_id``: bog'langan kompetensiya identifikatori; ``None`` bo'lsa
      bu umumiy standart tavsiya (R10.4) — faqat darajaga bog'langan.
    - ``level``: tavsiya mo'ljallangan baholash darajasi.
    - ``text``: rivojlanish ko'rsatmasi matni.
    - ``id``: tavsiya identifikatori (``recommendations.id``, ixtiyoriy).
    """

    competency_id: int | None
    level: Level
    text: str
    id: int | None = None


@dataclass(frozen=True)
class EvaluatedCompetency:
    """Baholangan kompetensiya va uning aniqlangan darajasi (kirish, transient).

    Daraja Baholash_Moduli tomonidan kompetensiya foizidan aniqlanadi
    (`determine_level`) va shu yerga tayyor holda uzatiladi.

    Maydonlar:
    - ``competency_id``: kompetensiya identifikatori.
    - ``level``: shu kompetensiya bo'yicha aniqlangan daraja (R10.1).
    """

    competency_id: int
    level: Level


@dataclass(frozen=True)
class SelectedRecommendation:
    """Bitta kompetensiya uchun tanlangan tavsiya (chiqish, transient).

    ``result_recommendations`` jadvaliga persist qilinishi mumkin bo'lgan
    ma'lumotni aks ettiradi (``text`` => ``text_snapshot``).

    Maydonlar:
    - ``competency_id``: kompetensiya identifikatori.
    - ``level``: shu kompetensiya darajasi.
    - ``recommendation_id``: tanlangan tavsiya identifikatori (``None`` bo'lishi
      mumkin, agar manba tavsiyada ``id`` berilmagan bo'lsa).
    - ``text``: tanlangan tavsiya matnining nusxasi (snapshot).
    - ``is_standard``: ``True`` bo'lsa, aniq mos topilmagani uchun umumiy
      standart tavsiya tanlangan (R10.4).
    """

    competency_id: int
    level: Level
    recommendation_id: int | None
    text: str
    is_standard: bool


def _rec_sort_key(rec: Recommendation) -> tuple[int, int, int, str]:
    """Tavsiyalarni deterministik tartiblash kaliti.

    Kirish to'plami tartibsiz bo'lsa ham (masalan, ``set``) takroriy kalitlarni
    barqaror hal qilish va umumiy zaxira tavsiyani aniqlash uchun ishlatiladi.
    """
    return (
        _LEVEL_ORDER[rec.level],
        rec.competency_id if rec.competency_id is not None else -1,
        rec.id if rec.id is not None else -1,
        rec.text,
    )


def select_recommendations(
    evaluated_competencies: Iterable[EvaluatedCompetency],
    available_recommendations: Iterable[Recommendation],
) -> list[SelectedRecommendation]:
    """Har bir baholangan kompetensiya + daraja uchun tavsiya tanlaydi.

    Tanlash tartibi (R10.1, R10.4):
    1. Aniq mos: ``competency_id`` va ``level`` bo'yicha to'g'ridan-to'g'ri
       mos keladigan tavsiya.
    2. Darajaga mos umumiy standart tavsiya: ``competency_id is None`` va
       o'sha ``level`` (R10.4).
    3. Istalgan umumiy standart tavsiya (``competency_id is None``) — totallikni
       (har doim tavsiya bo'lishini) kafolatlash uchun yakuniy zaxira.

    Funksiya sof va deterministik: chiqish tartibi ``evaluated_competencies``
    kirish tartibini saqlaydi; takroriy/tartibsiz tavsiyalar deterministik
    tarzda hal qilinadi.

    Args:
        evaluated_competencies: baholangan (kompetensiya, daraja) juftliklari.
        available_recommendations: mavjud tavsiyalar to'plami; har biri
            ``competency_id`` + ``level`` bo'yicha kalitlanadi, umumiy standart
            tavsiya esa ``competency_id is None`` bilan belgilanadi.

    Returns:
        Har bir kirish kompetensiyasi uchun bittadan ``SelectedRecommendation``,
        kirish tartibida.

    Raises:
        ValueError: kamida bitta kompetensiya uchun na aniq mos, na umumiy
            standart tavsiya topilmasa (totallik kafolati buzilsa). Totallik
            uchun ``available_recommendations`` kamida bitta umumiy standart
            tavsiyani (``competency_id is None``) o'z ichiga olishi shart.
    """
    # Deterministik tartiblash: tartibsiz kirishda ham barqaror natija.
    recs = sorted(available_recommendations, key=_rec_sort_key)

    exact: dict[tuple[int, Level], Recommendation] = {}
    general_by_level: dict[Level, Recommendation] = {}
    general_catch_all: Recommendation | None = None

    for rec in recs:
        if rec.competency_id is None:
            # Umumiy standart tavsiya (R10.4) — darajaga bog'langan.
            general_by_level.setdefault(rec.level, rec)
            if general_catch_all is None:
                general_catch_all = rec
        else:
            exact.setdefault((rec.competency_id, rec.level), rec)

    selected: list[SelectedRecommendation] = []
    for comp in evaluated_competencies:
        rec = exact.get((comp.competency_id, comp.level))
        if rec is None:
            # Aniq mos yo'q -> darajaga mos umumiy standart (R10.4).
            rec = general_by_level.get(comp.level)
        if rec is None:
            # So'nggi zaxira -> istalgan umumiy standart (totallik kafolati).
            rec = general_catch_all
        if rec is None:
            raise ValueError(
                "Tavsiya tanlab bo'lmadi: kompetensiya "
                f"{comp.competency_id} (daraja {comp.level.value}) uchun aniq "
                "mos ham, umumiy standart tavsiya ham mavjud emas. Totallik "
                "uchun kamida bitta umumiy standart tavsiya (competency_id is "
                "None) berilishi shart."
            )

        selected.append(
            SelectedRecommendation(
                competency_id=comp.competency_id,
                level=comp.level,
                recommendation_id=rec.id,
                text=rec.text,
                is_standard=rec.competency_id is None,
            )
        )

    return selected


__all__ = [
    "Recommendation",
    "EvaluatedCompetency",
    "SelectedRecommendation",
    "select_recommendations",
]
