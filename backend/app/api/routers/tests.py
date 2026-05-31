"""Test, sessiya va natija routeri — ``/tests/*`` (R6, R7, R8, R20.3).

Diagnostika testlari ro'yxati/tafsiloti, sessiya boshlash/topshirish va natija
o'qish. Router ``TestService`` / ``SessionService`` / ``ResultRepository`` ustidagi
yupqa (thin) HTTP qatlami: autentifikatsiya ``get_current_principal`` bog'liqligi
orqali (R20.3), egalik tekshiruvi esa ``ensure_self_or_admin`` yordamchisi orqali
(R8.7, R4.1) amalga oshiriladi. Biznes validatsiyasi va xatolar servis qatlamida
hal qilinadi; servis istisnolari markazlashtirilgan handler (``app.api.errors``)
ga tarqaladi (R20.6).

Endpointlar (design.md — "API Design / Testlar va natijalar"):

==============================  ====  =====================================
Yo'l                            Usul  Tavsif
==============================  ====  =====================================
``/tests``                      GET   faol testlar ro'yxati (R6.1)
``/tests/results/me``           GET   o'z natijalari (R8)
``/tests/results/{result_id}``  GET   natija tafsiloti (egalik/RBAC) (R8.7)
``/tests/{id}``                 GET   test + savollar; 404 (R6.3, R6.4)
``/tests/{id}/start``           POST  sessiya boshlash/davom; 201 (R7.1, R7.10)
``/tests/{id}/submit``          POST  topshirish (idempotent) (R7.6–R7.9, R8.6)
==============================  ====  =====================================

Yo'l tartibi (muhim): statik ``/results/me`` va ``/results/{result_id}``
yo'llari dinamik ``/{test_id}`` yo'llaridan **oldin** e'lon qilinadi, shunda
``/tests/results/...`` so'rovi ``/tests/{test_id}`` ga tushib qolmaydi.

Lokal prefiks ``/tests``; ``main.py`` uni ``/api/v1`` ostiga ulaydi (vazifa 18.1).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_principal, get_db
from app.api.middleware.rbac import ensure_self_or_admin
from app.api.schemas import (
    CompetencyScoreResponse,
    ResultDetailResponse,
    ResultSummaryResponse,
    SessionResponse,
    SubmitResultResponse,
    SubmitSessionRequest,
    TestDetailResponse,
    TestSummaryResponse,
)
from app.repositories.results import ResultRepository
from app.services.errors import NotFoundError
from app.services.recommendation_service import RecommendationService
from app.services.session_service import SessionService
from app.services.test_service import TestService

router = APIRouter(prefix="/tests", tags=["tests"])


# ---------------------------------------------------------------------------
# Testlar ro'yxati (R6.1)
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[TestSummaryResponse],
    summary="Faol testlar ro'yxati",
)
def list_tests(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[TestSummaryResponse]:
    """Faqat faol testlar ro'yxatini qaytaradi (R6.1).

    Faol test bo'lmasa bo'sh ro'yxat (xato emas, R6.5). Autentifikatsiya talab
    qilinadi (R20.3).
    """
    service = TestService(db)
    summaries = service.list_tests()
    return [TestSummaryResponse.model_validate(s) for s in summaries]


# ---------------------------------------------------------------------------
# Natijalar (R8) — statik yo'llar dinamik ``/{test_id}`` dan OLDIN
# ---------------------------------------------------------------------------


@router.get(
    "/results/me",
    response_model=list[ResultSummaryResponse],
    summary="Joriy foydalanuvchi natijalari",
)
def list_my_results(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[ResultSummaryResponse]:
    """Joriy foydalanuvchining barcha natijalarini qaytaradi (R8.6).

    Natija bo'lmasa bo'sh ro'yxat. Xronologik tartib repository tomonidan
    (``created_at`` o'suvchi).
    """
    results = ResultRepository(db).list_for_user(principal.user_id)
    return [ResultSummaryResponse.model_validate(r) for r in results]


@router.get(
    "/results/{result_id}",
    response_model=ResultDetailResponse,
    summary="Natija tafsiloti (egalik/RBAC)",
)
def get_result(
    result_id: int,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ResultDetailResponse:
    """Natija tafsilotini egalik tekshiruvi bilan qaytaradi (R8.7, R4.1).

    Natija mavjud bo'lmasa ``NotFoundError`` (404). Mavjud bo'lsa, so'rovchi
    natija egasi yoki Administrator ekani ``ensure_self_or_admin`` orqali
    tekshiriladi; aks holda 403 (R4.5).
    """
    result = ResultRepository(db).get_by_id(result_id)
    if result is None:
        raise NotFoundError(f"Natija topilmadi (id={result_id})")
    ensure_self_or_admin(principal, result.user_id)
    return ResultDetailResponse.model_validate(result)


# ---------------------------------------------------------------------------
# Test tafsiloti (R6.3, R6.4)
# ---------------------------------------------------------------------------


@router.get(
    "/{test_id}",
    response_model=TestDetailResponse,
    summary="Test tafsiloti (savollar bilan)",
)
def get_test(
    test_id: int,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> TestDetailResponse:
    """Test tafsilotini va savollarini belgilangan tartibda qaytaradi (R6.3).

    Mavjud bo'lmagan yoki faol bo'lmagan test ``NotFoundError`` (404) beradi
    (R6.4).
    """
    service = TestService(db)
    detail = service.get_test(test_id)
    return TestDetailResponse.model_validate(detail)


# ---------------------------------------------------------------------------
# Sessiyani boshlash / davom ettirish (R7.1, R7.10)
# ---------------------------------------------------------------------------


@router.post(
    "/{test_id}/start",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Test sessiyasini boshlash/davom ettirish",
)
def start_session(
    test_id: int,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> SessionResponse:
    """Yangi sessiya yaratadi yoki mavjud tugatilmaganini davom ettiradi (R7.1, R7.10).

    Tugatilmagan sessiya mavjud bo'lsa, yangisi yaratilmaydi va mavjudi
    qaytariladi (idempotentlik — R7.10). Test mavjud/faol bo'lmasa
    ``NotFoundError`` (404, R6.4).
    """
    service = SessionService(db)
    session_obj = service.start_session(principal.user_id, test_id)
    return SessionResponse.model_validate(session_obj)


# ---------------------------------------------------------------------------
# Topshirish (R7.6–R7.9, R8.6)
# ---------------------------------------------------------------------------


@router.post(
    "/{test_id}/submit",
    response_model=SubmitResultResponse,
    summary="Test sessiyasini topshirish",
)
def submit_session(
    test_id: int,
    payload: SubmitSessionRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> SubmitResultResponse:
    """Javoblarni topshiradi, baholaydi va natijani saqlaydi (R7.6–R7.9, R8.6).

    Tavsiyalar ``RecommendationService.assign_recommendations`` ``on_result_created``
    ilgagi (hook) sifatida ulanadi — shunda tavsiyalar natija bilan **bitta
    tranzaksiyada** saqlanadi (R10.1 seam). Idempotent: takroriy topshirish 409
    (R7.7); begona/yo'q sessiya 404 (R7.9); muddat tugamagan to'liqsiz topshirish
    400 (R7.8). ``now`` joriy UTC vaqt sifatida uzatiladi.
    """
    recommendations = RecommendationService(db)
    service = SessionService(
        db, on_result_created=recommendations.assign_recommendations
    )
    outcome = service.submit_session(
        principal.user_id,
        payload.session_id,
        [answer.model_dump() for answer in payload.answers],
        now=datetime.now(timezone.utc),
    )

    score = outcome.score
    # Saqlangan natijadan qayta topshirish sanasini olamiz (R8.4) — u sof domen
    # ``ScoreResult`` da emas, balki ``test_results`` yozuvida saqlanadi.
    stored = ResultRepository(db).get_by_id(outcome.result_id)
    next_retake_date = stored.next_retake_date if stored is not None else None

    return SubmitResultResponse(
        result_id=outcome.result_id,
        total_score=score.total_score,
        max_score=score.max_score,
        percentage=score.percentage,
        level=str(score.level),
        competencies=[
            CompetencyScoreResponse(
                competency_id=comp.competency_id,
                percentage=comp.percentage,
            )
            for comp in score.competencies
        ],
        strongest=list(score.strongest),
        weakest=list(score.weakest),
        next_retake_date=next_retake_date,
    )


__all__ = ["router"]
