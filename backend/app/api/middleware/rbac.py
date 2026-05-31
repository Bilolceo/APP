"""RBACGuard — ikki bosqichli rolga asoslangan kirish nazorati (R4, R17.6).

Ushbu modul REST_API qatlami (vazifa 17.x routerlari) uchun **rolga asoslangan
kirish nazorati** (RBAC) ni FastAPI bog'liqliklari (dependencies) va sof
callable yordamchilar ko'rinishida taqdim etadi. Dizayn (design.md — "Security
Design / RBAC (R4)") ikki bosqichni belgilaydi:

1. **Rol darajasi** (role-level) — endpoint qaysi rol(lar)ni talab qiladi.
   :func:`require_roles` bog'liqlik fabrikasi (dependency factory) joriy
   :class:`~app.api.deps.Principal` ning roli ruxsat etilgan to'plamda ekanini
   ta'minlaydi; aks holda 403 (``code="forbidden"``) ko'tariladi (R4.4, R4.5).
   Qulaylik uchun :data:`require_admin`, :data:`require_expert`,
   :data:`require_leader` tayyor guardlar beriladi.

2. **Egalik / biriktirilganlik** (ownership/assignment) — resurs so'rovchiga
   tegishlimi yoki ekspertga biriktirilgan rahbarga oidmi. Bu darajadagi
   tekshiruv resurs identifikatorini (masalan ``target_user_id``, ``leader_id``)
   talab qilgani uchun router ichida chaqiriladigan **callable yordamchilar**
   sifatida beriladi:
   - :func:`ensure_self_or_admin` — Rahbar faqat o'z resurslariga; Administrator
     barchasiga (R4.1, R4.3, R17.6).
   - :func:`ensure_expert_can_access_leader` — Ekspert faqat o'ziga biriktirilgan
     rahbarlarga; Administrator barchasiga (R4.2).

Ruxsat etilmagan murojaatda **hech narsa o'zgartirmasdan/oshkor qilmasdan** 403
ko'tariladi (R4.5): yordamchilar faqat tekshiradi va istisno ko'taradi; ular
ma'lumotni o'qimaydi yoki o'zgartirmaydi (biriktirilganlik tekshiruvidan tashqari,
u faqat o'qiy oladigan predikat).

Forbidden (403) tipi
--------------------
``app.services.errors`` da Forbidden/Authorization semantik tipi yo'q va u modul
o'zgartirilmaydi. Shu sababli — ``PortfolioService`` va ``ExpertReviewService``
dagi bilan **bir xil naqsh** bo'yicha — shu modulda ``ServiceError`` ustiga
``PermissionDeniedError`` (``code="forbidden"``) belgilanadi. Markazlashtirilgan
exception handler (``app.api.errors``) ``code == "forbidden"`` ni 403 ga
keltiradi.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_principal, get_db
from app.repositories.expert import ExpertReviewRepository
from app.services.errors import ServiceError

__all__ = [
    "ROLE_LEADER",
    "ROLE_EXPERT",
    "ROLE_ADMIN",
    "PermissionDeniedError",
    "require_roles",
    "require_admin",
    "require_expert",
    "require_leader",
    "ensure_self_or_admin",
    "ensure_expert_can_access_leader",
]


# ---------------------------------------------------------------------------
# Rol nomlari (roles jadvali / token role da'vosidagi qiymatlar — R1.7, R4)
# ---------------------------------------------------------------------------

#: MTT rahbari roli — asosiy foydalanuvchi (test topshiruvchi) (R4.1).
ROLE_LEADER = "Rahbar"

#: Ekspert/metodist roli — biriktirilgan rahbarlarni baholovchi (R4.2).
ROLE_EXPERT = "Ekspert"

#: Administrator — barcha resurslarga kirish huquqiga ega (R4.3).
ROLE_ADMIN = "Administrator"


# ---------------------------------------------------------------------------
# Forbidden (403) — errors.py o'zgartirilmaydi (PortfolioService naqshi)
# ---------------------------------------------------------------------------


class PermissionDeniedError(ServiceError):
    """So'rovchiga ruxsat yo'q — HTTP 403 (R4.5, R17.6).

    `app.services.errors` da Forbidden/Authorization tipi mavjud emas; uni
    o'zgartirmaslik uchun shu modulda `ServiceError` ustiga aniq semantik tip
    belgilanadi (PortfolioService/ExpertReviewService bilan izchil). Markaziy
    exception handler ``code == "forbidden"`` ni 403 ga keltiradi. Xabar ataylab
    umumiy bo'ladi va resurs mavjudligini oshkor qilmaydi (R4.5).
    """

    code = "forbidden"


# ---------------------------------------------------------------------------
# 1-bosqich: rol darajasi guardlari (dependency factory)
# ---------------------------------------------------------------------------


def require_roles(*roles: str) -> Callable[..., Principal]:
    """Joriy ``Principal`` roli ruxsat etilgan to'plamda ekanini ta'minlaydi.

    Bu **bog'liqlik fabrikasi** (dependency factory): u FastAPI bog'liqligi
    sifatida ishlatiladigan callable qaytaradi. Qaytarilgan bog'liqlik avval
    :func:`~app.api.deps.get_current_principal` orqali autentifikatsiyani
    bajaradi (yaroqsiz token -> 401), so'ngra rolni tekshiradi: rol ruxsat
    etilgan to'plamda bo'lmasa :class:`PermissionDeniedError` (403, R4.4, R4.5)
    ko'taradi. Aks holda ``Principal`` ni qaytaradi, shunda router uni qabul
    qilib qo'shimcha egalik tekshiruvlarini bajarishi mumkin.

    Misol::

        @router.get("/admin/users", dependencies=[Depends(require_admin)])
        def list_users(...): ...

        # yoki principalни ham olish uchun:
        @router.get("/reports")
        def reports(principal: Principal = Depends(require_roles(ROLE_ADMIN, ROLE_EXPERT))):
            ...

    Args:
        *roles: ruxsat etilgan rol nomlari (masalan ``ROLE_ADMIN``).

    Returns:
        FastAPI bog'liqligi sifatida ishlatiladigan callable; muvaffaqiyatda
        ``Principal`` ni qaytaradi, aks holda ``PermissionDeniedError`` ko'taradi.
    """
    allowed = frozenset(roles)

    def _guard(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        if principal.role not in allowed:
            # Ruxsat yo'q: hech narsa oshkor qilmasdan 403 (R4.4, R4.5).
            raise PermissionDeniedError("Bu amal uchun ruxsat yo'q")
        return principal

    return _guard


#: Faqat Administrator (R4.3, R14.5).
require_admin = require_roles(ROLE_ADMIN)

#: Ekspert yoki Administrator (R4.2) — ekspert endpointlari uchun rol darajasi.
#: Resurs darajasidagi biriktirilganlik :func:`ensure_expert_can_access_leader`
#: orqali alohida tekshiriladi.
require_expert = require_roles(ROLE_EXPERT, ROLE_ADMIN)

#: Rahbar yoki Administrator (R4.1) — rahbar resurslari uchun rol darajasi.
#: Egalik :func:`ensure_self_or_admin` orqali alohida tekshiriladi.
require_leader = require_roles(ROLE_LEADER, ROLE_ADMIN)


# ---------------------------------------------------------------------------
# 2-bosqich: egalik / biriktirilganlik yordamchilari (router ichida chaqiriladi)
# ---------------------------------------------------------------------------


def ensure_self_or_admin(principal: Principal, target_user_id: int) -> None:
    """So'rovchi resurs egasi yoki Administrator ekanini ta'minlaydi (R4.1, R4.3, R17.6).

    Qoida:
    - Administrator istalgan foydalanuvchi resursiga kira oladi (R4.3).
    - Boshqa har qanday rol (Rahbar va h.k.) faqat **o'z** resurslariga
      (``principal.user_id == target_user_id``) kira oladi (R4.1, R17.6).

    Aks holda :class:`PermissionDeniedError` (403) ko'tariladi; funksiya hech
    qanday holatni o'zgartirmaydi yoki ma'lumot oshkor qilmaydi (R4.5).

    Args:
        principal: joriy autentifikatsiyalangan so'rovchi.
        target_user_id: murojaat qilinayotgan resurs egasining ID si.

    Raises:
        PermissionDeniedError: so'rovchi egasi ham, administrator ham bo'lmasa.
    """
    if principal.role == ROLE_ADMIN:
        return
    if principal.user_id == target_user_id:
        return
    raise PermissionDeniedError("Bu resursga ruxsat yo'q")


def ensure_expert_can_access_leader(
    principal: Principal,
    leader_id: int,
    session: Session,
) -> None:
    """Ekspert berilgan rahbarga kira olishini ta'minlaydi (R4.2, R4.3).

    Qoida:
    - Administrator istalgan rahbarga kira oladi (R4.3).
    - Ekspert faqat o'ziga **biriktirilgan** rahbarga kira oladi; biriktirilganlik
      :meth:`ExpertReviewRepository.is_expert_assigned` (umumiy tashkilot — MVP
      qoidasi) orqali aniqlanadi (R4.2).
    - Boshqa rollar (masalan Rahbar) ekspert doirasidagi rahbarlarga kira olmaydi.

    Aks holda :class:`PermissionDeniedError` (403) ko'tariladi; biriktirilganlik
    tekshiruvi faqat o'qiy oladigan predikat bo'lib, hech qanday holatni
    o'zgartirmaydi (R4.5).

    Args:
        principal: joriy autentifikatsiyalangan so'rovchi.
        leader_id: murojaat qilinayotgan rahbarning ID si.
        session: biriktirilganlik tekshiruvi uchun DB sessiyasi.

    Raises:
        PermissionDeniedError: so'rovchi administrator emas va (ekspert sifatida)
            rahbarga biriktirilmagan bo'lsa.
    """
    if principal.role == ROLE_ADMIN:
        return
    if principal.role == ROLE_EXPERT:
        reviews = ExpertReviewRepository(session)
        if reviews.is_expert_assigned(principal.user_id, leader_id):
            return
    raise PermissionDeniedError("Bu rahbar natijalariga ruxsat yo'q")
