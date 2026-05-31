"""Repository / ORM qatlami — ma'lumotlarga kirish nuqtalari.

Servis qatlami (keyingi vazifalar) ma'lumotlarga shu paketdagi repository
klasslari orqali kiradi. Har bir repository yupqa (thin): faqat so'rov va
persistensiya bilan shug'ullanadi; biznes qoidalari servis/domen qatlamida.

Eksport qilinadigan klasslar jadval(lar) bo'yicha:
- ``base``: `BaseRepository` (umumiy CRUD).
- ``users``: `UserRepository`.
- ``tests``: `TestRepository`, `QuestionRepository`, `AnswerRepository`.
- ``sessions``: `SessionRepository`.
- ``results``: `ResultRepository`.
- ``portfolio``: `PortfolioRepository`.
- ``expert``: `ExpertReviewRepository`.
- ``recommendations``: `RecommendationRepository`.
- ``tokens``: `TokenRepository`.
- ``devices``: `DeviceTokenRepository`.
- ``reference``: `RoleRepository`, `RegionRepository`, `OrganizationRepository`,
  `CompetencyRepository`.
"""

from __future__ import annotations

from app.repositories.base import BaseRepository
from app.repositories.devices import DeviceTokenRepository
from app.repositories.expert import ExpertReviewRepository
from app.repositories.portfolio import PortfolioRepository
from app.repositories.recommendations import RecommendationRepository
from app.repositories.reference import (
    CompetencyRepository,
    OrganizationRepository,
    RegionRepository,
    RoleRepository,
)
from app.repositories.results import ResultRepository
from app.repositories.sessions import SessionRepository
from app.repositories.tests import (
    AnswerRepository,
    QuestionRepository,
    TestRepository,
)
from app.repositories.tokens import TokenRepository
from app.repositories.users import UserRepository

__all__ = [
    # base
    "BaseRepository",
    # users
    "UserRepository",
    # content
    "TestRepository",
    "QuestionRepository",
    "AnswerRepository",
    # sessions
    "SessionRepository",
    # results
    "ResultRepository",
    # portfolio
    "PortfolioRepository",
    # expert
    "ExpertReviewRepository",
    # recommendations
    "RecommendationRepository",
    # tokens
    "TokenRepository",
    # devices
    "DeviceTokenRepository",
    # reference
    "RoleRepository",
    "RegionRepository",
    "OrganizationRepository",
    "CompetencyRepository",
]
