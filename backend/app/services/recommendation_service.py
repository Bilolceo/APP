"""Tavsiya_Moduli — RecommendationService (R10).

Individual rivojlanish tavsiyalarini natijaga avtomatik bog'lash va o'qish
uchun biznes-mantiq. Servis framework'dan mustaqil (FastAPI'siz): konstruktorda
SQLAlchemy `Session` (yoki tayyor repositorylar) oladi va ma'lumotlarga
repository qatlami orqali kiradi. Tavsiya TANLASH mantig'i (aniq moslik yoki
umumiy standart) sof domen qatlamida (`app.domain.recommendation`) joylashadi;
bu servis faqat darajani aniqlash (`app.domain.scoring.determine_level`),
domen funksiyasini chaqirish va natijani persist qilish/o'qish bilan
shug'ullanadi.

Mas'uliyat (design.md — "Tavsiya_Moduli (RecommendationService)"):
- ``assign_recommendations(result)`` — natija hisoblanganda har bir kompetensiya
  natijasi uchun darajani aniqlaydi, domen ``select_recommendations`` ni chaqiradi
  va tanlangan tavsiyalarni natijaga bog'lab (``text_snapshot`` bilan) saqlaydi
  (R10.1, R10.4). SessionService natija yaratilgandan so'ng chaqiradigan ilgak
  (hook).
- ``get_my_recommendations(user_id)`` — foydalanuvchining eng so'nggi yakunlangan
  natijasiga bog'langan tavsiyalarni har bir kompetensiya nomi, darajasi va
  matni bilan qaytaradi; natija yo'q bo'lsa bo'sh holat (xato emas) (R10.2,
  R10.5).
- ``get_recommendations_by_result(user_id, result_id)`` — berilgan natijaga
  bog'langan tavsiyalarni egalik tekshiruvi bilan qaytaradi; natija mavjud emas
  yoki so'rovchiga tegishli bo'lmasa ``NotFoundError`` (R10.3, R10.6).

Eslatma (mas'uliyatlar ajratilishi): foiz -> daraja konversiyasi Baholash_Moduli
(`determine_level`) mas'uliyatidir; tavsiya tanlash esa sof domen
(`select_recommendations`) mas'uliyatida. Bu servis ikkalasini ulaydi va
persistensiya/egalik (RBAC) qoidalarini qo'llaydi.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.recommendation import (
    EvaluatedCompetency,
    SelectedRecommendation,
)
from app.domain.recommendation import (
    Recommendation as DomainRecommendation,
)
from app.domain.recommendation import (
    select_recommendations as domain_select_recommendations,
)
from app.domain.scoring import determine_level
from app.domain.types import Level
from app.models.recommendation import ResultRecommendation
from app.repositories.recommendations import RecommendationRepository
from app.repositories.results import ResultRepository
from app.services.errors import NotFoundError


@dataclass(frozen=True)
class RecommendationView:
    """Natijaga bog'langan bitta tavsiyaning o'qish ko'rinishi (R10.2).

    Maydonlar (R10.2 — kompetensiya nomi, darajasi va rivojlanish ko'rsatmasi):
    - ``competency_id``: kompetensiya identifikatori (umumiy standart bo'lsa
      ham bu yerda baholangan kompetensiya saqlanadi).
    - ``competency_name``: kompetensiya nomi; topilmasa ``None``.
    - ``level``: baholangan daraja (``"Past"``/``"O'rta"``/``"Yaxshi"``/
      ``"Yuqori"``).
    - ``text``: tavsiya matnining nusxasi (``text_snapshot``).
    """

    competency_id: int | None
    competency_name: str | None
    level: str | None
    text: str | None


def _parse_level(value: str | None) -> Level | None:
    """ORM ``level`` matnini :class:`Level` enum a'zosiga aylantiradi.

    Yaroqsiz yoki ``None`` qiymat uchun ``None`` qaytaradi (domen tavsiyasi
    darajaga ega bo'lishini talab qiladi).
    """
    if value is None:
        return None
    try:
        return Level(value)
    except ValueError:
        return None


def _to_view(link: ResultRecommendation) -> RecommendationView:
    """`ResultRecommendation` ORM yozuvini `RecommendationView` ga aylantiradi.

    Kompetensiya nomi bog'lanish (relationship) orqali olinadi; bog'lanmagan
    bo'lsa ``None``.
    """
    competency = link.competency
    return RecommendationView(
        competency_id=link.competency_id,
        competency_name=competency.name if competency is not None else None,
        level=link.level,
        text=link.text_snapshot,
    )


class RecommendationService:
    """Individual rivojlanish tavsiyalari servisi (R10).

    Args:
        session: faol SQLAlchemy `Session`. Repositorylar berilmagan bo'lsa,
            undan quriladi.
        recommendation_repository: ixtiyoriy, tayyor `RecommendationRepository`.
        result_repository: ixtiyoriy, tayyor `ResultRepository`.

    `session` ham, repositorylar ham berilmasa `ValueError` ko'tariladi.
    """

    def __init__(
        self,
        session: Session | None = None,
        *,
        recommendation_repository: RecommendationRepository | None = None,
        result_repository: ResultRepository | None = None,
    ) -> None:
        if recommendation_repository is None or result_repository is None:
            if session is None:
                raise ValueError(
                    "RecommendationService uchun `session` yoki tayyor "
                    "repositorylar zarur"
                )
            if recommendation_repository is None:
                recommendation_repository = RecommendationRepository(session)
            if result_repository is None:
                result_repository = ResultRepository(session)
        self._recs = recommendation_repository
        self._results = result_repository

    # -- Avtomatik tanlash va bog'lash (R10.1, R10.4) -----------------------

    def assign_recommendations(self, result: object) -> list[RecommendationView]:
        """Natija uchun tavsiyalarni avtomatik tanlaydi va bog'lab saqlaydi.

        Har bir kompetensiya natijasi uchun (R10.1):
        1. Saqlangan kompetensiya foizidan darajani aniqlaydi
           (`determine_level`).
        2. Mavjud tavsiyalar to'plamiga qarshi sof domen
           ``select_recommendations`` ni chaqiradi (aniq moslik, bo'lmasa
           umumiy standart — R10.4).
        3. Tanlangan tavsiyani natijaga bog'lab, matn nusxasi
           (``text_snapshot``) bilan persist qiladi.

        Ushbu metod SessionService natija yaratilgandan keyin chaqiradigan
        ilgak (hook). Kompetensiya natijasi bo'lmasa hech narsa saqlanmaydi.

        Args:
            result: yangi hisoblangan natija (``id`` atributiga ega ORM
                ``TestResult``).

        Returns:
            Saqlangan tavsiyalarning o'qish ko'rinishlari ro'yxati.
        """
        result_id = result.id  # type: ignore[attr-defined]
        competency_results = self._results.list_competency_results(result_id)

        evaluated = [
            EvaluatedCompetency(
                competency_id=cr.competency_id,
                level=determine_level(cr.percentage),
            )
            for cr in competency_results
        ]
        if not evaluated:
            return []

        available = self._available_domain_recommendations()
        try:
            selected = domain_select_recommendations(evaluated, available)
        except ValueError:
            # Umumiy standart tavsiya seed qilinmagan (R10.4 mavjud bo'lishini
            # kutadi). Natija yaratish ilgagini buzmaslik uchun faqat aniq
            # mos kelgan kompetensiyalar uchun tavsiya saqlanadi (graceful).
            selected = self._select_exact_only(evaluated, available)

        views: list[RecommendationView] = []
        for sel in selected:
            link = self._recs.attach_to_result(
                result_id=result_id,
                competency_id=sel.competency_id,
                level=sel.level.value,
                recommendation_id=sel.recommendation_id,
                text_snapshot=sel.text,
            )
            views.append(_to_view(link))
        return views

    # -- O'qish (R10.2, R10.3, R10.5, R10.6) --------------------------------

    def get_my_recommendations(self, user_id: int) -> list[RecommendationView]:
        """So'nggi yakunlangan natijaga bog'langan tavsiyalarni qaytaradi (R10.2).

        Foydalanuvchining hech qanday yakunlangan natijasi bo'lmasa bo'sh ro'yxat
        qaytariladi — bu xato emas, muvaffaqiyatli bo'sh holat (R10.5).
        """
        latest = self._recs.latest_result_for_user(user_id)
        if latest is None:
            return []
        links = self._recs.get_for_result(latest.id)
        return [_to_view(link) for link in links]

    def get_recommendations_by_result(
        self, user_id: int, result_id: int
    ) -> list[RecommendationView]:
        """Berilgan natijaga bog'langan tavsiyalarni egalik bilan qaytaradi (R10.3).

        Egalik tekshiruvi (R10.6): natija mavjud bo'lmasa yoki so'rovchiga
        tegishli bo'lmasa ``NotFoundError`` ko'tariladi (mavjudlikni oshkor
        qilmaslik uchun ikkala holat ham 404 ga keltiriladi).

        Raises:
            NotFoundError: natija topilmasa yoki ``user_id`` ga tegishli bo'lmasa.
        """
        result = self._results.get_for_user(user_id, result_id)
        if result is None:
            raise NotFoundError(f"Natija topilmadi (id={result_id})")
        links = self._recs.get_for_result(result.id)
        return [_to_view(link) for link in links]

    # -- Ichki yordamchilar -------------------------------------------------

    def _available_domain_recommendations(self) -> list[DomainRecommendation]:
        """Mavjud ORM tavsiyalarini sof domen tavsiyalariga aylantiradi.

        - Yaroqli darajaga ega tavsiyalar to'g'ridan-to'g'ri o'tkaziladi.
        - Darajasiz (``level IS NULL``) umumiy standart tavsiya (``competency_id
          IS NULL``) barcha darajalarga taalluqli — har bir darajaga bittadan
          domen tavsiyasiga kengaytiriladi (R10.4 totallik).
        - Darajasi yaroqsiz/``None`` bo'lgan kompetensiyaga xos tavsiya
          (noto'g'ri sozlash) e'tiborsiz qoldiriladi.
        """
        domain_recs: list[DomainRecommendation] = []
        for orm_rec in self._recs.list_all():
            level = _parse_level(orm_rec.level)
            if level is not None:
                domain_recs.append(
                    DomainRecommendation(
                        competency_id=orm_rec.competency_id,
                        level=level,
                        text=orm_rec.text,
                        id=orm_rec.id,
                    )
                )
            elif orm_rec.competency_id is None:
                # Darajasiz umumiy standart -> barcha darajalar uchun.
                for lvl in Level:
                    domain_recs.append(
                        DomainRecommendation(
                            competency_id=None,
                            level=lvl,
                            text=orm_rec.text,
                            id=orm_rec.id,
                        )
                    )
        return domain_recs

    @staticmethod
    def _select_exact_only(
        evaluated: list[EvaluatedCompetency],
        available: list[DomainRecommendation],
    ) -> list[SelectedRecommendation]:
        """Faqat aniq mos kelgan tavsiyalarni tanlaydi (umumiy standart yo'q holat).

        Umumiy standart tavsiya seed qilinmagan kamdan-kam holatda ishlatiladi:
        mos topilmagan kompetensiyalar tashlab ketiladi (ilgak buzilmaydi).
        """
        exact: dict[tuple[int, Level], DomainRecommendation] = {}
        for rec in available:
            if rec.competency_id is not None:
                exact.setdefault((rec.competency_id, rec.level), rec)

        selected: list[SelectedRecommendation] = []
        for comp in evaluated:
            rec = exact.get((comp.competency_id, comp.level))
            if rec is not None:
                selected.append(
                    SelectedRecommendation(
                        competency_id=comp.competency_id,
                        level=comp.level,
                        recommendation_id=rec.id,
                        text=rec.text,
                        is_standard=False,
                    )
                )
        return selected


__all__ = ["RecommendationService", "RecommendationView"]
