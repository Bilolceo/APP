"""Reyting routeri — ``/rating`` (R12, R20.4).

Foydalanuvchilar reytingini **anonim** tarzda taqdim etadi. Tizimda alohida
``RatingService`` yo'q; shu sababli router reyting mantig'ini sof domen
funksiyasi (``app.domain.rating.build_anonymized_rating``) va repository
(``ResultRepository``/``UserRepository``) yordamida quradi — hisoblash yadrosi
(saralash R12.1–R12.3, anonimlik R12.4, natijasizni chiqarish R12.5) domen
qatlamida, router esa faqat domen kirish yozuvlarini tayyorlaydi va natijani
javob sxemasiga keltiradi.

Reyting subyektlari — **Rahbar** rolidagi foydalanuvchilar (hisobot moduli bilan
izchil). Har bir rahbar uchun saralash ko'rsatkichi sifatida uning **eng so'nggi**
yakunlangan natijasi foizi olinadi; yakunlangan natijasi bo'lmagan rahbarlar
reytingdan chiqariladi va ``out_of_ranking`` ga (rank berilmasdan) joylanadi
(R12.5). Har bir yozuv faqat anonim maydonlar (hudud, tashkilot turi, lavozim,
ko'rsatkich, rank) bilan taqdim etiladi; to'liq ism/telefon oshkor qilinmaydi
(R12.4). So'rovchining o'z yozuvi ``is_requester`` bilan ajratiladi (R12.4).

``?scope=`` parametri (MVP)
--------------------------
Qo'llab-quvvatlanadigan qiymatlar: ``overall`` (standart), ``region``,
``organization``, ``competency``. MVP da to'rt kesim ham rahbarning eng so'nggi
**umumiy** foizi bo'yicha bitta anonim reyting qaytaradi; har bir yozuvda hudud,
tashkilot turi va lavozim mavjud bo'lgani uchun mijoz kerakli kesim bo'yicha
guruhlashi mumkin. ``scope`` qiymati javobda qaytariladi va kelajakda kesim
bo'yicha alohida saralash (masalan tanlangan kompetensiya foizi) uchun
kengaytiriladi. Yaroqsiz ``scope`` -> ``ValidationError`` (400).

Kirish: autentifikatsiyalangan har qanday foydalanuvchi (Rahbar/Ekspert/Admin)
reytingni ko'rishi mumkin (R12) — anonim bo'lgani uchun rol darajasidagi
qo'shimcha cheklov qo'yilmaydi.

Endpoint (design.md — "API Design / Reyting"):

=================  =====  ============================================
Yo'l               Usul   Tavsif
=================  =====  ============================================
``/rating``        GET    anonim reyting; ``?scope=`` (R12.1–R12.5)
=================  =====  ============================================

Lokal prefiks yo'q (yagona yo'l ``/rating``); ``main.py`` uni ``/api/v1`` ostiga
ulaydi (18.1).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_principal, get_db
from app.api.schemas import RatingResponse
from app.domain.rating import RatingParticipant, build_anonymized_rating
from app.models.result import TestResult
from app.models.user import User
from app.repositories.results import ResultRepository
from app.repositories.users import UserRepository
from app.services.errors import ValidationError

router = APIRouter(tags=["rating"])

#: Rahbar roli nomi (R1.7) — reyting subyektlarini ajratadi (hisobot bilan izchil).
_LEADER_ROLE_NAME = "Rahbar"

#: Qo'llab-quvvatlanadigan reyting kesimlari (R12.1).
_VALID_SCOPES: frozenset[str] = frozenset(
    {"overall", "region", "organization", "competency"}
)


def _str_or_none(value: object | None) -> str | None:
    """Anonim maydon qiymatini matnga keltiradi (yoki ``None``)."""
    return None if value is None else str(value)


def _build_participants(
    leaders: list[User], results: list[TestResult]
) -> list[RatingParticipant]:
    """Rahbarlardan reyting subyektlarini quradi (R12.4, R12.5).

    Har bir rahbar uchun eng so'nggi yakunlangan natija foizi olinadi (natijalar
    ``created_at`` bo'yicha o'suvchi bo'lgani uchun keyingi yozuv oldingisini
    qoplaydi — oxirgisi eng so'nggi). Natijasi bo'lmagan rahbar ``percentage=None``
    bilan kiritiladi va domen uni reytingdan chiqaradi (R12.5).

    Anonimlik: faqat hudud (nomi), tashkilot turi va lavozim uzatiladi; to'liq
    ism/telefon domen yadrosiga umuman berilmaydi (R12.4).
    """
    latest_by_user: dict[int, TestResult] = {}
    for result in results:
        latest_by_user[result.user_id] = result

    participants: list[RatingParticipant] = []
    for leader in leaders:
        latest = latest_by_user.get(leader.id)
        region_name = leader.region.name if leader.region is not None else None
        participants.append(
            RatingParticipant(
                entity_id=leader.id,
                percentage=latest.percentage if latest is not None else None,
                region=_str_or_none(region_name),
                org_type=_str_or_none(leader.org_type),
                position=_str_or_none(leader.position),
                achieved_at=latest.created_at if latest is not None else None,
            )
        )
    return participants


@router.get(
    "/rating",
    response_model=RatingResponse,
    summary="Anonim reyting",
)
def get_rating(
    scope: str = Query(
        default="overall",
        description="Reyting kesimi: overall/region/organization/competency",
    ),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> RatingResponse:
    """Anonim reytingni qaytaradi (R12.1–R12.5).

    Rahbarlar eng so'nggi umumiy foizi bo'yicha kamayuvchi tartibda saralanadi
    (R12.2, R12.3); yakunlangan natijasi bo'lmaganlar reytingdan chiqariladi
    (R12.5). Yozuvlar anonim (R12.4); so'rovchining o'z yozuvi ``is_requester``
    bilan belgilanadi (R12.4). Yaroqsiz ``scope`` -> 400.
    """
    if scope not in _VALID_SCOPES:
        allowed = ", ".join(sorted(_VALID_SCOPES))
        raise ValidationError(
            f"Yaroqsiz scope; ruxsat etilgan qiymatlar: {allowed}",
            field="scope",
        )

    users = UserRepository(db).list_all()
    leaders = [
        u for u in users if u.role is not None and u.role.name == _LEADER_ROLE_NAME
    ]
    results = ResultRepository(db).list_all_with_user()

    participants = _build_participants(leaders, results)
    rating = build_anonymized_rating(participants, requester_id=principal.user_id)

    return RatingResponse(
        scope=scope,
        ranked=list(rating.ranked),
        out_of_ranking=list(rating.out_of_ranking),
    )


__all__ = ["router"]
