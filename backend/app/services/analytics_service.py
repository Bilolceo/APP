"""Analitika_Moduli — AnalyticsService (R9).

Foydalanuvchining test natijalari asosida grafik taqdimot uchun ma'lumot va
o'sish dinamikasini shakllantiruvchi biznes-mantiq. Servis framework'dan
mustaqil (FastAPI'siz): konstruktorda SQLAlchemy `Session` (yoki tayyor
repositorylar) oladi va ma'lumotlarga repository qatlami orqali kiradi.
Hisoblash mantig'i (o'sish dinamikasi, farq, jamlangan o'rtacha va kompetensiya
ekstремumlari) sof domen qatlamida (`app.domain.analytics`) joylashadi; daraja
aniqlash esa Baholash_Moduli (`app.domain.scoring.determine_level`)
mas'uliyatidir. Bu servis ORM yozuvlarini sof domen kirishlariga moslaydi
(adapter), domen funksiyalarini chaqiradi va natijani frozen dataclasslar
(DTO) sifatida qaytaradi.

Mas'uliyat (design.md — "Analitika_Moduli (AnalyticsService)"):
- ``get_my_analytics(user_id)`` — umumiy ball, kompetensiya taqsimoti (radar /
  progress bar / line chart / category card uchun yetarli ma'lumot — R9.2),
  xronologik (eng eskidan eng yangiga) o'sish dinamikasi (R9.1) va o'sish farqi
  (R9.3); bitta natija bo'lsa farq "mavjud emas" (``None``) (R9.4); eng kuchli
  va rivojlantirilishi lozim bo'lgan kompetensiya(lar), teng qiymatda barchasi
  (R9.5, R9.6); natija umuman bo'lmasa muvaffaqiyatli bo'sh holat (xato emas)
  (R9.7).

Agregatsiya tanlovi (hujjatlash — R9.2, R9.5, R9.6):
  Kompetensiya taqsimoti va eng kuchli/rivojlantirilishi lozim kompetensiyalar
  foydalanuvchining **barcha** natijalari bo'yicha **jamlangan (o'rtacha)
  kompetensiya foizlari** asosida hisoblanadi (har bir kompetensiya uchun shu
  kompetensiya barcha natijalardagi foizlarining o'rtachasi). Bu R9.5/R9.6
  dagi "eng yuqori/past **umumiy foiz**" iborasiga mos keladi va `Hisobot_Moduli`
  (`aggregate_competencies`) bilan izchil. Umumiy ball (``overall_score``) ham
  shu izchillik bilan barcha natijalar umumiy foizlarining o'rtachasi sifatida
  qaytariladi (`aggregate_average`). Vaqt o'lchami esa o'sish dinamikasi va
  farqi orqali alohida taqdim etiladi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.analytics import (
    AggregateResult,
    DatedResult,
    GrowthPoint,
    aggregate_average,
    aggregate_competencies,
    growth_diff,
    growth_dynamics,
)
from app.domain.scoring import determine_level
from app.models.result import TestResult
from app.repositories.reference import CompetencyRepository
from app.repositories.results import ResultRepository

# Natija umuman bo'lmaganda qaytariladigan nol umumiy ball — R9.7.
_ZERO_PERCENT = Decimal("0.00")


@dataclass(frozen=True)
class CompetencyDistributionItem:
    """Kompetensiya taqsimotidagi bitta yozuv (R9.2).

    Radar diagramma, progress bar va toifa ball kartochkasi uchun yetarli
    ma'lumot: kompetensiya nomi (radar o'qi / kartochka sarlavhasi), jamlangan
    foiz (radar/progress qiymati) va daraja (kartochka toifasi).

    Maydonlar:
    - ``competency_id``: kompetensiya identifikatori.
    - ``competency_name``: kompetensiya nomi; topilmasa ``None``.
    - ``percentage``: shu kompetensiya bo'yicha jamlangan (o'rtacha) foiz
      (0–100, 2 kasr xonasi).
    - ``level``: jamlangan foizdan aniqlangan daraja
      (``"Past"``/``"O'rta"``/``"Yaxshi"``/``"Yuqori"``).
    """

    competency_id: int
    competency_name: str | None
    percentage: Decimal
    level: str


@dataclass(frozen=True)
class CompetencyRef:
    """Kompetensiyaga ishora (kuchli/rivojlantirilishi lozim ro'yxatlari uchun).

    Maydonlar:
    - ``competency_id``: kompetensiya identifikatori.
    - ``competency_name``: kompetensiya nomi; topilmasa ``None``.
    """

    competency_id: int
    competency_name: str | None


@dataclass(frozen=True)
class AnalyticsView:
    """Foydalanuvchi analitikasining to'liq o'qish ko'rinishi (R9).

    Maydonlar:
    - ``overall_score``: barcha natijalar umumiy foizlarining jamlangan
      o'rtachasi (0–100, 2 kasr); natija yo'q bo'lsa ``0.00`` (R9.1, R9.7).
    - ``distribution``: kompetensiya taqsimoti — radar/progress/line/card uchun
      ma'lumot, kompetensiya identifikatori bo'yicha o'suvchi tartibda (R9.2).
    - ``dynamics``: o'sish dinamikasi — xronologik (eng eskidan eng yangiga)
      ``GrowthPoint`` ketma-ketligi; line chart uchun (R9.1).
    - ``growth_diff``: joriy (eng so'nggi) va bevosita oldingi natija foizlari
      farqi (musbat/manfiy/nol); natija ikkitadan kam bo'lsa "mavjud emas"
      (``None``) (R9.3, R9.4).
    - ``strongest``: eng yuqori jamlangan foizli kompetensiya(lar); teng
      qiymatda barchasi (R9.5, R9.6).
    - ``to_develop``: eng past jamlangan foizli kompetensiya(lar); teng qiymatda
      barchasi (R9.5, R9.6).
    - ``result_count``: hisobga olingan natijalar soni.
    - ``has_results``: foydalanuvchining kamida bitta natijasi bor-yo'qligi
      (bo'sh holatni aniq belgilash uchun — R9.7).
    """

    overall_score: Decimal
    distribution: tuple[CompetencyDistributionItem, ...] = ()
    dynamics: tuple[GrowthPoint, ...] = ()
    growth_diff: Decimal | None = None
    strongest: tuple[CompetencyRef, ...] = ()
    to_develop: tuple[CompetencyRef, ...] = ()
    result_count: int = 0
    has_results: bool = False


class AnalyticsService:
    """Natijalar va analitika servisi (R9).

    Args:
        session: faol SQLAlchemy `Session`. Repositorylar berilmagan bo'lsa,
            undan quriladi.
        result_repository: ixtiyoriy, tayyor `ResultRepository`.
        competency_repository: ixtiyoriy, tayyor `CompetencyRepository`.

    `session` ham, repositorylar ham berilmasa `ValueError` ko'tariladi.
    """

    def __init__(
        self,
        session: Session | None = None,
        *,
        result_repository: ResultRepository | None = None,
        competency_repository: CompetencyRepository | None = None,
    ) -> None:
        if result_repository is None or competency_repository is None:
            if session is None:
                raise ValueError(
                    "AnalyticsService uchun `session` yoki tayyor "
                    "repositorylar zarur"
                )
            if result_repository is None:
                result_repository = ResultRepository(session)
            if competency_repository is None:
                competency_repository = CompetencyRepository(session)
        self._results = result_repository
        self._competencies = competency_repository

    # -- Asosiy operatsiya (R9.1–R9.7) --------------------------------------

    def get_my_analytics(self, user_id: int) -> AnalyticsView:
        """Foydalanuvchi analitikasini shakllantiradi (R9.1–R9.7).

        Foydalanuvchining barcha natijalari xronologik (o'suvchi) tartibda
        olinadi va quyidagilar hisoblanadi:
        - umumiy ball (jamlangan o'rtacha foiz) — R9.1;
        - kompetensiya taqsimoti (radar/progress/line/card uchun) — R9.2;
        - o'sish dinamikasi (xronologik ketma-ketlik) — R9.1;
        - o'sish farqi (joriy vs oldingi; bitta natijada ``None``) — R9.3, R9.4;
        - eng kuchli/rivojlantirilishi lozim kompetensiya(lar), teng qiymatda
          barchasi — R9.5, R9.6.

        Foydalanuvchining hech qanday natijasi bo'lmasa, xato emas, balki
        muvaffaqiyatli bo'sh holat qaytariladi (``overall_score = 0.00``, bo'sh
        taqsimot, bo'sh dinamika, ``growth_diff = None``) — R9.7.

        Args:
            user_id: analitika so'ralayotgan foydalanuvchi identifikatori.

        Returns:
            To'ldirilgan :class:`AnalyticsView` (frozen DTO).
        """
        results = self._results.list_for_user(user_id)

        # R9.7: natija yo'q -> muvaffaqiyatli bo'sh holat.
        if not results:
            return AnalyticsView(overall_score=_ZERO_PERCENT)

        # -- O'sish dinamikasi va farqi (R9.1, R9.3, R9.4) ------------------
        # ORM `TestResult` (.percentage + .created_at) -> sof `DatedResult`.
        dated = [
            DatedResult(percentage=r.percentage, achieved_at=r.created_at)
            for r in results
        ]
        dynamics = tuple(growth_dynamics(dated))
        diff = growth_diff(dated)

        # -- Jamlangan o'rtacha va kompetensiya ekstремumlari (R9.1, R9.5, R9.6)
        aggregate_inputs = [self._to_aggregate(r) for r in results]
        overall_score = aggregate_average(aggregate_inputs)
        extremes = aggregate_competencies(aggregate_inputs)

        # -- Kompetensiya nomlarini bir marta yechib olish (cache) ----------
        name_cache: dict[int, str | None] = {}
        for agg in extremes.aggregates:
            name_cache[agg.competency_id] = self._competency_name(
                agg.competency_id, name_cache
            )

        # -- Taqsimot (R9.2): jamlangan foiz + daraja ----------------------
        distribution = tuple(
            CompetencyDistributionItem(
                competency_id=agg.competency_id,
                competency_name=name_cache.get(agg.competency_id),
                percentage=agg.aggregate_percentage,
                level=determine_level(agg.aggregate_percentage).value,
            )
            for agg in extremes.aggregates
        )

        # -- Kuchli / rivojlantirilishi lozim kompetensiyalar (R9.5, R9.6) --
        strongest = tuple(
            CompetencyRef(
                competency_id=cid,
                competency_name=name_cache.get(cid),
            )
            for cid in extremes.highest
        )
        to_develop = tuple(
            CompetencyRef(
                competency_id=cid,
                competency_name=name_cache.get(cid),
            )
            for cid in extremes.lowest
        )

        return AnalyticsView(
            overall_score=overall_score,
            distribution=distribution,
            dynamics=dynamics,
            growth_diff=diff,
            strongest=strongest,
            to_develop=to_develop,
            result_count=len(results),
            has_results=True,
        )

    # -- Ichki yordamchilar -------------------------------------------------

    @staticmethod
    def _to_aggregate(result: TestResult) -> AggregateResult:
        """ORM `TestResult` -> sof `AggregateResult` (kompetensiya kesimi bilan).

        Har bir natijaning kompetensiya foizlari ``{competency_id: percentage}``
        moslikка yig'iladi; baholangan kompetensiya bo'lmasa bo'sh moslik.
        """
        competencies = {
            cr.competency_id: cr.percentage
            for cr in result.competency_results
        }
        return AggregateResult(
            user_id=result.user_id,
            percentage=result.percentage,
            competencies=competencies,
        )

    def _competency_name(
        self, competency_id: int, cache: dict[int, str | None]
    ) -> str | None:
        """Kompetensiya nomini repository orqali yechadi (cache bilan).

        Topilmasa ``None`` qaytaradi (analitika nomsiz ham yumshoq ishlaydi).
        """
        if competency_id in cache:
            return cache[competency_id]
        competency = self._competencies.get_by_id(competency_id)
        return competency.name if competency is not None else None


__all__ = [
    "AnalyticsService",
    "AnalyticsView",
    "CompetencyDistributionItem",
    "CompetencyRef",
]
