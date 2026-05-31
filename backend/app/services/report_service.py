"""Hisobot_Moduli — ReportService (R15).

Admin va ekspert uchun jamlangan hisobotlarni shakllantiruvchi biznes-mantiq.
Servis framework'dan mustaqil (FastAPI'siz): konstruktorda SQLAlchemy `Session`
(yoki tayyor repositorylar) oladi va ma'lumotlarga repository qatlami orqali
kiradi. Jamlash (agregatsiya) mantig'i sof domen qatlamida
(`app.domain.analytics`) joylashadi; bu servis faqat domen kirish yozuvlarini
(``AggregateResult``, ``SectionRecord``) qurish, domen funksiyalarini chaqirish
va natijalarni o'qish ko'rinishi (frozen dataclass) ga keltirish bilan
shug'ullanadi.

Mas'uliyat (design.md — "Hisobot_Moduli (ReportService)"):
- ``admin_report()`` — rahbarlar soni, test topshirganlar soni, o'rtacha ball
  (barcha yakunlangan natijalar umumiy foizlari arifmetik o'rtachasi, 2 kasr),
  eng past va eng yuqori kompetensiyalar (`aggregate_competencies`) (R15.1, R15.2).
- ``report_by_region()`` / ``report_by_organization()`` — har bir kesim bo'yicha
  rahbarlar soni, test topshirganlar soni va o'rtacha ball (`aggregate_by_section`
  over ``SectionRecord``) (R15.3, R15.4).
- ``individual_dynamics(leader_id)`` — tanlangan rahbar natijalarining xronologik
  (eng eskidan eng yangiga) dinamikasi (`growth_dynamics`) (R15.5).
- Ekspert doirasi cheklovi (R15.6): har bir metod ixtiyoriy ``expert_id`` qabul
  qiladi; berilgan bo'lsa hisobot faqat shu ekspertga biriktirilgan rahbarlar
  bilan cheklanadi.
- Bo'sh doira (yakunlangan natija yo'q) — nol qiymatli/bo'sh muvaffaqiyatli holat,
  xato emas (R15.7).

Loyihalashtirish qarorlari (denominator va manbalar) — aniq hujjatlashtirilgan:

- **Rahbarlar (leaders).** "Rahbar" — ``role.name == "Rahbar"`` bo'lgan
  foydalanuvchi. Rahbarlar soni `users` jadvalidan olinadi (ekspert/administrator
  rollaridan ajratilgan holda), shu sababli **test topshirmagan rahbarlar ham**
  hisoblanadi. Bu R15.1 dagi "rahbarlar soni" va "test topshirganlar soni"
  o'rtasidagi farqni mazmunli qiladi.
- **Test topshirganlar (test takers).** Kamida bitta yakunlangan natijaga ega
  noyob rahbarlar. ``TestResult`` faqat sessiya yakunlanganda yaratilgani uchun
  (sessiyaga 1:1, R7.7) har bir ``TestResult`` "yakunlangan natija" hisoblanadi.
- **Umumiy o'rtacha ball (admin_report).** R15.1 ga muvofiq **barcha yakunlangan
  natijalar** foizlarining o'rtachasi (rahbar boshiga emas).
- **Kesim o'rtacha balli (region/organization).** Har bir ``SectionRecord``
  **bitta rahbarni** ifodalaydi (domen shartnomasi); rahbarning vakil (representative)
  foizi sifatida **eng so'nggi** (created_at bo'yicha) yakunlangan natijasi
  ishlatiladi, natijasi bo'lmaganlar uchun ``None``. Shunday qilib kesim o'rtachasi
  rahbar boshiga hisoblanadi va bir rahbar bir necha marta test topshirsa ham
  qiyshaymaydi.
- **Ekspert doirasi (R15.6).** Tizimda "ekspertning tashkilotlari" uchun bevosita
  so'rov yo'q; shu sababli doira rahbar bo'yicha
  ``ExpertReviewRepository.is_expert_assigned(expert_id, leader_id)`` orqali
  filtrlangan (umumiy tashkilot qoidasi — MVP). ``expert_id`` berilganda ham
  rahbarlar, ham natijalar shu predikat bo'yicha cheklanadi.
"""

from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.analytics import (
    AggregateResult,
    DatedResult,
    SectionRecord,
    aggregate_average,
    aggregate_by_section,
    aggregate_competencies,
    growth_dynamics,
)
from app.models.result import TestResult
from app.models.user import User
from app.repositories.expert import ExpertReviewRepository
from app.repositories.reference import CompetencyRepository
from app.repositories.results import ResultRepository
from app.repositories.users import UserRepository

#: "Rahbar" roli nomi — hisobot rahbarlarini ekspert/administratordan ajratadi
#: (R1.7). Boshqa seed nomi ishlatilsa, bu konstanta orqali moslashtiriladi.
LEADER_ROLE_NAME = "Rahbar"

#: Bo'sh doira uchun nol o'rtacha (R15.7) — domen `_mean_percentage` bilan izchil.
_ZERO_PERCENT = Decimal("0.00")


# ---------------------------------------------------------------------------
# O'qish ko'rinishlari (frozen dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompetencyExtreme:
    """Eng past/yuqori jamlangan kompetensiyaning o'qish ko'rinishi (R15.2).

    Maydonlar:
    - ``competency_id``: kompetensiya identifikatori.
    - ``competency_name``: kompetensiya nomi; topilmasa ``None``.
    - ``aggregate_percentage``: shu kompetensiya bo'yicha jamlangan foiz
      (barcha yakunlangan natijalar o'rtachasi, 2 kasr).
    """

    competency_id: int
    competency_name: str | None
    aggregate_percentage: Decimal


@dataclass(frozen=True)
class AdminReport:
    """Administrator umumiy hisoboti (R15.1, R15.2).

    Maydonlar:
    - ``leaders_count``: tizimdagi (yoki ekspert doirasidagi) noyob rahbarlar soni.
    - ``test_takers_count``: kamida bitta yakunlangan natijaga ega noyob rahbarlar.
    - ``average_score``: barcha yakunlangan natijalar umumiy foizlari o'rtachasi
      (0–100, 2 kasr); natija yo'q bo'lsa ``0.00`` (R15.7).
    - ``lowest_competencies``: eng past jamlangan foizli kompetensiya(lar); teng
      qiymatda barchasi (R15.2). Natija yo'q bo'lsa bo'sh.
    - ``highest_competencies``: eng yuqori jamlangan foizli kompetensiya(lar).
    """

    leaders_count: int
    test_takers_count: int
    average_score: Decimal
    lowest_competencies: tuple[CompetencyExtreme, ...] = ()
    highest_competencies: tuple[CompetencyExtreme, ...] = ()


@dataclass(frozen=True)
class SectionReportRow:
    """Bitta kesim (hudud yoki tashkilot) bo'yicha jamlanma qatori (R15.3, R15.4).

    Maydonlar:
    - ``section_id``: kesim identifikatori (hudud/tashkilot id); biriktirilmagan
      (NULL) rahbarlar uchun ``None``.
    - ``section_name``: kesim nomi; ``None`` (biriktirilmagan) yoki topilmasa ``None``.
    - ``leaders_count``: kesimdagi noyob rahbarlar soni.
    - ``test_takers_count``: kesimda test topshirgan noyob rahbarlar soni.
    - ``average_score``: kesim o'rtacha balli (rahbar boshiga, 2 kasr); test
      topshirgan rahbar bo'lmasa ``0.00`` (R15.7).
    """

    section_id: Hashable | None
    section_name: str | None
    leaders_count: int
    test_takers_count: int
    average_score: Decimal


@dataclass(frozen=True)
class SectionReport:
    """Kesim (hudud yoki tashkilot) bo'yicha hisobot (R15.3, R15.4).

    ``rows`` deterministik tartibda (kesim identifikatori bo'yicha o'suvchi;
    biriktirilmagan ``None`` kesim oxirida). Bo'sh doira -> bo'sh ``rows`` (R15.7).
    """

    rows: tuple[SectionReportRow, ...] = ()


@dataclass(frozen=True)
class DynamicsPoint:
    """Individual dinamikadagi bitta nuqta — sana bilan belgilangan foiz (R15.5)."""

    achieved_at: datetime
    percentage: Decimal


@dataclass(frozen=True)
class IndividualDynamics:
    """Bitta rahbarning xronologik o'sish dinamikasi (R15.5).

    Maydonlar:
    - ``leader_id``: rahbar identifikatori.
    - ``points``: sana bo'yicha o'suvchi (eng eskidan eng yangiga) nuqtalar;
      natija yo'q bo'lsa bo'sh (R15.7).
    """

    leader_id: int
    points: tuple[DynamicsPoint, ...] = ()


class ReportService:
    """Jamlangan hisobotlar servisi (R15).

    Args:
        session: faol SQLAlchemy `Session`. Repositorylar berilmagan bo'lsa,
            ulardan shu sessiya orqali quriladi.
        result_repository: ixtiyoriy, tayyor `ResultRepository`.
        user_repository: ixtiyoriy, tayyor `UserRepository`.
        expert_repository: ixtiyoriy, tayyor `ExpertReviewRepository`.
        competency_repository: ixtiyoriy, tayyor `CompetencyRepository`.
        leader_role_name: rahbar roli nomi (standart ``"Rahbar"``).

    `session` ham, repositorylar ham berilmasa `ValueError` ko'tariladi.

    Eslatma (xavfsizlik / RBAC): admin yoki ekspert ruxsati router/RBAC qatlamida
    (task 16.5/17.4) tekshiriladi. Ekspert doirasini cheklash uchun chaqiruvchi
    ``expert_id`` ni uzatadi (R15.6); ushbu servis o'zi rol tekshirmaydi.
    """

    def __init__(
        self,
        session: Session | None = None,
        *,
        result_repository: ResultRepository | None = None,
        user_repository: UserRepository | None = None,
        expert_repository: ExpertReviewRepository | None = None,
        competency_repository: CompetencyRepository | None = None,
        leader_role_name: str = LEADER_ROLE_NAME,
    ) -> None:
        needs_session = (
            result_repository is None
            or user_repository is None
            or expert_repository is None
            or competency_repository is None
        )
        if needs_session and session is None:
            raise ValueError(
                "ReportService uchun `session` yoki tayyor repositorylar zarur"
            )
        self._results = result_repository or ResultRepository(session)  # type: ignore[arg-type]
        self._users = user_repository or UserRepository(session)  # type: ignore[arg-type]
        self._experts = expert_repository or ExpertReviewRepository(session)  # type: ignore[arg-type]
        self._competencies = competency_repository or CompetencyRepository(
            session  # type: ignore[arg-type]
        )
        self._leader_role_name = leader_role_name

    # -- Admin umumiy hisoboti (R15.1, R15.2) -------------------------------

    def admin_report(self, *, expert_id: int | None = None) -> AdminReport:
        """Umumiy jamlangan hisobotni qaytaradi (R15.1, R15.2).

        Rahbarlar soni `users` jadvalidan (rol bo'yicha), test topshirganlar soni,
        o'rtacha ball va kompetensiya kesimi esa yakunlangan natijalardan olinadi.
        ``expert_id`` berilsa, ham rahbarlar, ham natijalar shu ekspertga
        biriktirilganlar bilan cheklanadi (R15.6). Hech qanday natija bo'lmasa
        nol qiymatli/bo'sh muvaffaqiyatli holat qaytadi (R15.7).
        """
        leaders = self._leaders(expert_id=expert_id)
        results = self._scoped_results(expert_id=expert_id)

        aggregate_results = [self._to_aggregate_result(r) for r in results]
        extremes = aggregate_competencies(aggregate_results)

        return AdminReport(
            leaders_count=len(leaders),
            test_takers_count=len({r.user_id for r in results}),
            average_score=aggregate_average(aggregate_results),
            lowest_competencies=self._to_extreme_views(extremes, extremes.lowest),
            highest_competencies=self._to_extreme_views(
                extremes, extremes.highest
            ),
        )

    # -- Kesim bo'yicha hisobotlar (R15.3, R15.4) ---------------------------

    def report_by_region(self, *, expert_id: int | None = None) -> SectionReport:
        """Hudud kesimi bo'yicha hisobotni qaytaradi (R15.3)."""
        return self._section_report("region", expert_id=expert_id)

    def report_by_organization(
        self, *, expert_id: int | None = None
    ) -> SectionReport:
        """Tashkilot kesimi bo'yicha hisobotni qaytaradi (R15.4)."""
        return self._section_report("organization", expert_id=expert_id)

    # -- Individual dinamika (R15.5) ----------------------------------------

    def individual_dynamics(self, leader_id: int) -> IndividualDynamics:
        """Tanlangan rahbar natijalarining xronologik dinamikasi (R15.5).

        Natijalar sana (created_at) bo'yicha o'suvchi tartibda qaytadi (domen
        ``growth_dynamics``). Rahbarning natijasi bo'lmasa bo'sh ``points`` —
        muvaffaqiyatli bo'sh holat (R15.7).
        """
        results = self._results.list_for_user(leader_id)
        dated = [
            DatedResult(percentage=r.percentage, achieved_at=r.created_at)
            for r in results
        ]
        points = tuple(
            DynamicsPoint(achieved_at=p.achieved_at, percentage=p.percentage)
            for p in growth_dynamics(dated)
        )
        return IndividualDynamics(leader_id=leader_id, points=points)

    # -- Ichki yordamchilar -------------------------------------------------

    def _section_report(
        self, dimension: str, *, expert_id: int | None
    ) -> SectionReport:
        """Berilgan o'lcham (``"region"``/``"organization"``) bo'yicha hisobot.

        Har bir rahbar uchun bitta ``SectionRecord`` quriladi: vakil foizi sifatida
        eng so'nggi yakunlangan natijasi (yoki natijasi bo'lmasa ``None``)
        ishlatiladi. Domen ``aggregate_by_section`` rahbarlar/topshirganlar sonini
        va o'rtacha ballni jamlaydi (R15.3, R15.4).
        """
        leaders = self._leaders(expert_id=expert_id)
        results = self._scoped_results(expert_id=expert_id)
        latest_percentage = self._latest_percentage_by_user(results)

        records: list[SectionRecord] = []
        section_names: dict[Hashable | None, str | None] = {}
        for leader in leaders:
            if dimension == "region":
                section_id: Hashable | None = leader.region_id
                section_name = leader.region.name if leader.region else None
            else:
                section_id = leader.organization_id
                section_name = (
                    leader.organization.name if leader.organization else None
                )
            section_names.setdefault(section_id, section_name)
            records.append(
                SectionRecord(
                    user_id=leader.id,
                    percentage=latest_percentage.get(leader.id),
                    region=leader.region_id,
                    organization=leader.organization_id,
                )
            )

        summaries = aggregate_by_section(records, dimension)
        rows = tuple(
            SectionReportRow(
                section_id=section_id,
                section_name=section_names.get(section_id),
                leaders_count=summary.leaders_count,
                test_takers_count=summary.test_takers_count,
                average_score=summary.average_score,
            )
            for section_id, summary in sorted(
                summaries.items(), key=lambda kv: (kv[0] is None, kv[0])
            )
        )
        return SectionReport(rows=rows)

    def _leaders(self, *, expert_id: int | None) -> list[User]:
        """Rahbar rolidagi foydalanuvchilar (ixtiyoriy ekspert doirasi bilan).

        ``expert_id`` berilsa, faqat shu ekspertga biriktirilgan rahbarlar
        qaytadi (R15.6).
        """
        leaders = [
            user
            for user in self._users.list_all()
            if user.role is not None and user.role.name == self._leader_role_name
        ]
        if expert_id is not None:
            leaders = [
                leader
                for leader in leaders
                if self._experts.is_expert_assigned(expert_id, leader.id)
            ]
        return leaders

    def _scoped_results(self, *, expert_id: int | None) -> list[TestResult]:
        """Barcha yakunlangan natijalar (ixtiyoriy ekspert doirasi bilan).

        ``expert_id`` berilsa, faqat shu ekspertga biriktirilgan rahbarlar
        natijalari qaytadi (R15.6).
        """
        results = self._results.list_all_with_user()
        if expert_id is not None:
            results = [
                result
                for result in results
                if self._experts.is_expert_assigned(expert_id, result.user_id)
            ]
        return results

    @staticmethod
    def _latest_percentage_by_user(
        results: list[TestResult],
    ) -> dict[int, Decimal]:
        """Har bir foydalanuvchi uchun eng so'nggi natija foizini qaytaradi.

        ``list_all_with_user`` natijalari ``created_at`` bo'yicha o'suvchi
        tartibda bo'lgani uchun keyingi yozuv oldingisini qoplaydi — natijada
        oxirgi (eng so'nggi) foiz saqlanadi.
        """
        latest: dict[int, Decimal] = {}
        for result in results:
            latest[result.user_id] = result.percentage
        return latest

    @staticmethod
    def _to_aggregate_result(result: TestResult) -> AggregateResult:
        """ORM natijasini domen ``AggregateResult`` ga aylantiradi (R15.1, R15.2)."""
        competencies = {
            cr.competency_id: cr.percentage for cr in result.competency_results
        }
        return AggregateResult(
            user_id=result.user_id,
            percentage=result.percentage,
            competencies=competencies,
        )

    def _to_extreme_views(
        self, extremes: object, competency_ids: tuple[int, ...]
    ) -> tuple[CompetencyExtreme, ...]:
        """Kompetensiya identifikatorlarini nom va jamlangan foiz bilan ko'rinishga aylantiradi."""
        aggregate_by_id = {
            agg.competency_id: agg.aggregate_percentage
            for agg in extremes.aggregates  # type: ignore[attr-defined]
        }
        views: list[CompetencyExtreme] = []
        for competency_id in competency_ids:
            competency = self._competencies.get_by_id(competency_id)
            views.append(
                CompetencyExtreme(
                    competency_id=competency_id,
                    competency_name=(
                        competency.name if competency is not None else None
                    ),
                    aggregate_percentage=aggregate_by_id.get(
                        competency_id, _ZERO_PERCENT
                    ),
                )
            )
        return tuple(views)


__all__ = [
    "ReportService",
    "AdminReport",
    "CompetencyExtreme",
    "SectionReport",
    "SectionReportRow",
    "IndividualDynamics",
    "DynamicsPoint",
    "LEADER_ROLE_NAME",
]
