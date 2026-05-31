"""SQLAlchemy ORM modellari — PostgreSQL jadvallari.

Ushbu paket barcha doimiy jadvallarning ORM modellarini (`design.md` —
"Data Models" bo'limi) belgilaydi. Modullar import qilinganda har bir model
umumiy `Base.metadata` reestriga ro'yxatdan o'tadi, shuning uchun Alembic
migratsiyalari (task 2.2) va `Base.metadata.create_all` (lokal sinov) butun
sxemani ko'radi.

Jadvallar bo'yicha modullar:
- ``base``: deklarativ `Base` va `TimestampMixin`.
- ``reference``: roles, regions, organizations, competencies.
- ``user``: users (R1, R5).
- ``content``: tests, questions, answers (R6, R14).
- ``session``: test_sessions, session_answers (R7).
- ``result``: test_results, competency_results (R8).
- ``recommendation``: recommendations, result_recommendations (R10).
- ``portfolio``: portfolios, files (R11, R18.2).
- ``expert``: expert_reviews (R13).
- ``auth``: refresh_tokens, token_blacklist, password_reset_codes, device_tokens.
- ``feedback``: feedbacks (post-MVP, R18.1).
"""

from __future__ import annotations

from app.models.auth import (
    DeviceToken,
    PasswordResetCode,
    RefreshToken,
    TokenBlacklist,
)
from app.models.base import Base, TimestampMixin
from app.models.content import Answer, Question, Test
from app.models.expert import ExpertReview
from app.models.feedback import Feedback
from app.models.portfolio import File, Portfolio
from app.models.recommendation import Recommendation, ResultRecommendation
from app.models.reference import Competency, Organization, Region, Role
from app.models.result import CompetencyResult, TestResult
from app.models.session import SessionAnswer, TestSession
from app.models.user import User

__all__ = [
    # base
    "Base",
    "TimestampMixin",
    # reference
    "Role",
    "Region",
    "Organization",
    "Competency",
    # user
    "User",
    # content
    "Test",
    "Question",
    "Answer",
    # session
    "TestSession",
    "SessionAnswer",
    # result
    "TestResult",
    "CompetencyResult",
    # recommendation
    "Recommendation",
    "ResultRecommendation",
    # portfolio
    "File",
    "Portfolio",
    # expert
    "ExpertReview",
    # auth
    "RefreshToken",
    "TokenBlacklist",
    "PasswordResetCode",
    "DeviceToken",
    # feedback (post-MVP)
    "Feedback",
]
