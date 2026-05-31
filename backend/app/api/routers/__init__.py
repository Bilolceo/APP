"""REST_API routerlari paketi (R20).

Har bir domen uchun alohida :class:`fastapi.APIRouter` modul sifatida belgilanadi
va ``main.py`` (vazifa 18.1) ularni ``/api/v1`` prefiksi ostida ilovaga ulaydi.
Shu sababli bu yerdagi routerlar **lokal** prefikslar (``/auth``, ``/users``)
bilan e'lon qilinadi.

Konvensiyalar (boshqa router vazifalari 17.2–17.4 ham shularga amal qiladi):
- Har bir router ``APIRouter(prefix=..., tags=[...])`` bilan yaratiladi.
- So'rov/javob modellari :mod:`app.api.schemas` paketidan olinadi; endpointlar
  ``response_model=`` va to'g'ri HTTP holat kodlarini belgilaydi (R20.1, R20.2).
- Autentifikatsiya/RBAC :mod:`app.api.deps` va :mod:`app.api.middleware.rbac`
  bog'liqliklari orqali qo'llanadi.
- Servis istisnolari **markazlashtirilgan** handler (:mod:`app.api.errors`) ga
  tarqaladi; routerlar ularni qo'lda HTTP ga aylantirmaydi (R20.6).

Eksport qilinadigan routerlar:
- :data:`auth_router` — ``/auth/*`` (R1, R2, R3).
- :data:`users_router` — ``/users/*`` (R5, R4).
- :data:`tests_router` — ``/tests/*`` (R6, R7, R8).
- :data:`questions_router` — ``/questions/*`` (R14; admin-guarded).
- :data:`recommendations_router` — ``/recommendations/*`` (R10).
- :data:`portfolio_router` — ``/portfolio/*`` (R11).
- :data:`analytics_router` — ``/analytics/*`` (R9, R15).
- :data:`admin_router` — ``/admin/*`` (R14; admin-guarded).
- :data:`expert_router` — ``/expert/*`` (R13; expert-guarded).
- :data:`reports_router` — ``/reports/*`` (R15; expert/admin-guarded).
- :data:`rating_router` — ``/rating`` (R12; anonim).
- :data:`devices_router` — ``/devices/*`` (R16).
"""

from __future__ import annotations

from app.api.routers.admin import router as admin_router
from app.api.routers.analytics import router as analytics_router
from app.api.routers.auth import router as auth_router
from app.api.routers.devices import router as devices_router
from app.api.routers.expert import router as expert_router
from app.api.routers.portfolio import router as portfolio_router
from app.api.routers.questions import router as questions_router
from app.api.routers.rating import router as rating_router
from app.api.routers.recommendations import router as recommendations_router
from app.api.routers.reports import router as reports_router
from app.api.routers.tests import router as tests_router
from app.api.routers.users import router as users_router

__all__ = [
    "auth_router",
    "users_router",
    "tests_router",
    "questions_router",
    "recommendations_router",
    "portfolio_router",
    "analytics_router",
    "admin_router",
    "expert_router",
    "reports_router",
    "rating_router",
    "devices_router",
]
