"""Tavsiya routeri — ``/recommendations/*`` (R10, R20.4).

Individual rivojlanish tavsiyalarini o'qish endpointlari. Router
``RecommendationService`` ustidagi yupqa HTTP qatlami: autentifikatsiya
``get_current_principal`` orqali; egalik (R10.6) servis qatlamida (begona/yo'q
natija ``NotFoundError`` -> 404). Natija yo'q bo'lsa bo'sh ro'yxat (xato emas,
R10.5).

Endpointlar (design.md — "API Design / Tavsiyalar"):

=================================================  =====  ========================
Yo'l                                               Usul   Tavsif
=================================================  =====  ========================
``/recommendations/me``                            GET    so'nggi natija (R10.2)
``/recommendations/by-result/{result_id}``         GET    natija bo'yicha (R10.3)
=================================================  =====  ========================

Lokal prefiks ``/recommendations``; ``main.py`` uni ``/api/v1`` ostiga ulaydi.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_principal, get_db
from app.api.schemas import RecommendationResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get(
    "/me",
    response_model=list[RecommendationResponse],
    summary="So'nggi natija tavsiyalari",
)
def get_my_recommendations(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[RecommendationResponse]:
    """Joriy foydalanuvchining so'nggi natijasiga bog'langan tavsiyalar (R10.2).

    Yakunlangan natija yo'q bo'lsa bo'sh ro'yxat qaytadi — bu xato emas,
    muvaffaqiyatli bo'sh holat (R10.5).
    """
    service = RecommendationService(db)
    views = service.get_my_recommendations(principal.user_id)
    return [RecommendationResponse.model_validate(v) for v in views]


@router.get(
    "/by-result/{result_id}",
    response_model=list[RecommendationResponse],
    summary="Natija bo'yicha tavsiyalar",
)
def get_recommendations_by_result(
    result_id: int,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[RecommendationResponse]:
    """Berilgan natijaga bog'langan tavsiyalarni egalik bilan qaytaradi (R10.3).

    Egalik tekshiruvi servis qatlamida (R10.6): natija mavjud bo'lmasa yoki
    so'rovchiga tegishli bo'lmasa ``NotFoundError`` (404) — mavjudlikni oshkor
    qilmaslik uchun ikkala holat ham 404 ga keltiriladi.
    """
    service = RecommendationService(db)
    views = service.get_recommendations_by_result(principal.user_id, result_id)
    return [RecommendationResponse.model_validate(v) for v in views]


__all__ = ["router"]
