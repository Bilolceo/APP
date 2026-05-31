"""REST_API middleware qatlami.

Bu paket FastAPI/Starlette middleware'larini saqlaydi. Middleware'lar
`app/main.py` da (18.1-vazifa) to'g'ri tartibda ulanadi; bu yerda ular
mustaqil, sinovdan o'tkaziladigan komponentlar sifatida aniqlanadi.

Mavjud middleware'lar:
- `RateLimitMiddleware` — joriy vaqt oynasi bo'yicha so'rovlarni cheklash
  va chegara oshganda 429 qaytarish (R17.3).
- `LoggingMiddleware` — strukturali so'rov jurnali; maxfiy maydonlarni
  (parol, token, telefon) allow-list yondashuvi bilan maskalovchi (R17.5).

RBAC guardlari (rolga asoslangan kirish nazorati — R4, R17.6):
- `require_roles`/`require_admin`/`require_expert`/`require_leader` — rol darajasi
  FastAPI bog'liqliklari.
- `ensure_self_or_admin`/`ensure_expert_can_access_leader` — router ichida
  chaqiriladigan egalik/biriktirilganlik yordamchilari.
"""

from __future__ import annotations

from app.api.middleware.logging import (
    LoggingMiddleware,
    sanitize_mapping,
)
from app.api.middleware.rate_limit import (
    InMemoryRateLimitStore,
    RateLimitMiddleware,
    RateLimitStore,
)
from app.api.middleware.rbac import (
    PermissionDeniedError,
    ensure_expert_can_access_leader,
    ensure_self_or_admin,
    require_admin,
    require_expert,
    require_leader,
    require_roles,
)

__all__ = [
    "RateLimitMiddleware",
    "RateLimitStore",
    "InMemoryRateLimitStore",
    "LoggingMiddleware",
    "sanitize_mapping",
    "require_roles",
    "require_admin",
    "require_expert",
    "require_leader",
    "ensure_self_or_admin",
    "ensure_expert_can_access_leader",
    "PermissionDeniedError",
]
