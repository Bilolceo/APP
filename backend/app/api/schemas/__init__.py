"""Pydantic so'rov/javob sxemalari paketi (REST_API qatlami — R20.1, R20.2, R20.6).

Ushbu paket routerlar (vazifa 17.x) ishlatadigan **so'rov** (request) va **javob**
(response) modellarini domen bo'yicha modullarga ajratadi:

- :mod:`app.api.schemas.common` — barcha domenlar uchun umumiy javoblar
  (masalan :class:`MessageResponse`).
- :mod:`app.api.schemas.auth` — autentifikatsiya so'rov/javoblari (R1, R2, R3).
- :mod:`app.api.schemas.user` — profil so'rov/javoblari (R5).
- :mod:`app.api.schemas.test` — test/sessiya/topshirish so'rov/javoblari (R6, R7, R8).
- :mod:`app.api.schemas.result` — natija javoblari (R8).

Konvensiyalar (boshqa router vazifalari 17.2–17.4 ham shu naqshga amal qiladi):
- So'rov modellari ``*Request``, javob modellari ``*Response`` deb nomlanadi.
- ORM/dataclass obyektlaridan javob qurish uchun ``ConfigDict(from_attributes=True)``
  ishlatiladi (``Model.model_validate(orm_obj)``).
- Routerlar ``response_model=`` va mos HTTP holat kodlarini belgilaydi; biznes
  validatsiyasi servis qatlamida (xatolar markazlashtirilgan handler orqali).

Barcha modellar shu paketdan to'g'ridan-to'g'ri import qilinishi uchun qayta
eksport qilinadi: ``from app.api.schemas import RegisterRequest`` kabi.
"""

from __future__ import annotations

from app.api.schemas.admin import (
    AdminResultResponse,
    AdminUserResponse,
    TestCreateRequest,
    TestResponse,
    TestUpdateRequest,
)
from app.api.schemas.analytics import (
    AnalyticsResponse,
    CompetencyDistributionResponse,
    CompetencyRefResponse,
    GrowthPointResponse,
    SectionAnalyticsResponse,
)
from app.api.schemas.auth import (
    AccessTokenResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenPairResponse,
)
from app.api.schemas.common import MessageResponse
from app.api.schemas.content import (
    AnswerOptionRequest,
    AnswerResponse,
    QuestionCreateRequest,
    QuestionResponse,
    QuestionUpdateRequest,
)
from app.api.schemas.device import (
    DeviceTokenInvalidateRequest,
    DeviceTokenRegisterRequest,
    DeviceTokenResponse,
)
from app.api.schemas.expert import (
    ExpertLeaderResponse,
    ExpertReviewRequest,
    ExpertReviewResponse,
)
from app.api.schemas.portfolio import PortfolioItemResponse
from app.api.schemas.rating import (
    OutOfRankingEntryResponse,
    RatingEntryResponse,
    RatingResponse,
)
from app.api.schemas.recommendation import RecommendationResponse
from app.api.schemas.report import (
    AdminReportResponse,
    CompetencyExtremeResponse,
    DynamicsPointResponse,
    IndividualDynamicsResponse,
    SectionReportResponse,
    SectionReportRowResponse,
)
from app.api.schemas.result import (
    CompetencyResultResponse,
    ResultDetailResponse,
    ResultSummaryResponse,
)
from app.api.schemas.test import (
    AnswerOptionResponse,
    AnswerSubmission,
    CompetencyScoreResponse,
    QuestionDetailResponse,
    SessionResponse,
    SubmitResultResponse,
    SubmitSessionRequest,
    TestDetailResponse,
    TestSummaryResponse,
)
from app.api.schemas.user import ProfileResponse, ProfileUpdateRequest

__all__ = [
    # common
    "MessageResponse",
    # auth (R1, R2, R3)
    "RegisterRequest",
    "LoginRequest",
    "RefreshRequest",
    "LogoutRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "TokenPairResponse",
    "AccessTokenResponse",
    # user / profil (R5)
    "ProfileUpdateRequest",
    "ProfileResponse",
    # test / sessiya / topshirish (R6, R7, R8)
    "TestSummaryResponse",
    "AnswerOptionResponse",
    "QuestionDetailResponse",
    "TestDetailResponse",
    "SessionResponse",
    "AnswerSubmission",
    "SubmitSessionRequest",
    "CompetencyScoreResponse",
    "SubmitResultResponse",
    # natija (R8)
    "CompetencyResultResponse",
    "ResultSummaryResponse",
    "ResultDetailResponse",
    # content / savollar (R14)
    "AnswerOptionRequest",
    "QuestionCreateRequest",
    "QuestionUpdateRequest",
    "AnswerResponse",
    "QuestionResponse",
    # tavsiya (R10)
    "RecommendationResponse",
    # portfolio (R11)
    "PortfolioItemResponse",
    # analitika (R9)
    "CompetencyDistributionResponse",
    "GrowthPointResponse",
    "CompetencyRefResponse",
    "AnalyticsResponse",
    "SectionAnalyticsResponse",
    # admin (R14)
    "AdminUserResponse",
    "AdminResultResponse",
    "TestCreateRequest",
    "TestUpdateRequest",
    "TestResponse",
    # expert (R13)
    "ExpertReviewRequest",
    "ExpertReviewResponse",
    "ExpertLeaderResponse",
    # report / hisobot (R15)
    "AdminReportResponse",
    "CompetencyExtremeResponse",
    "SectionReportResponse",
    "SectionReportRowResponse",
    "IndividualDynamicsResponse",
    "DynamicsPointResponse",
    # rating / reyting (R12)
    "RatingResponse",
    "RatingEntryResponse",
    "OutOfRankingEntryResponse",
    # device / qurilma (R16)
    "DeviceTokenRegisterRequest",
    "DeviceTokenInvalidateRequest",
    "DeviceTokenResponse",
]
