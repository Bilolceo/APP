"""Admin (kontent va ma'lumot boshqaruvi) routeri — ``/admin/*`` (R14, R20.4).

Administrator uchun foydalanuvchi/natija ro'yxati va test CRUD endpointlari.
Router ``AdminService`` (test CRUD) hamda repository qatlami (foydalanuvchi/natija
ro'yxati) ustidagi yupqa (thin) HTTP qatlami: so'rovni tuzilgan Pydantic modeli
sifatida qabul qiladi, servis/repozitoriy chaqiradi va javobni tasdiqlangan
javob modeliga keltiradi. **Biznes validatsiyasi** (nom 1–200, toifa whitelisti,
davomiyligi 1–600 — R14.2, R14.6) servis qatlamida; markazlashtirilgan exception
handler (``app.api.errors``) servis istisnolarini yagona tuzilgan HTTP javobiga
keltiradi (R20.6).

Barcha endpointlar **admin-guarded**: ``require_admin`` bog'liqligi rol
darajasida Administratorni talab qiladi; admin bo'lmagan so'rovchi 403 oladi
(R14.5, R4.5).

Endpointlar (design.md — "API Design / Admin"):

============================  ======  =====================================
Yo'l                          Usul    Tavsif
============================  ======  =====================================
``/admin/users``              GET     foydalanuvchilar ro'yxati (R14.1)
``/admin/results``            GET     natijalar ro'yxati (R14.1)
``/admin/tests``              POST    test yaratish; 201 (R14.2)
``/admin/tests/{id}``         PATCH   testni yangilash (R14.2, R14.6)
``/admin/tests/{id}``         DELETE  testni o'chirish/nofaol qilish (R14.4)
============================  ======  =====================================

Lokal prefiks ``/admin``; ``main.py`` uni ``/api/v1`` ostiga ulaydi (18.1).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.middleware.rbac import require_admin
from app.api.schemas import (
    AdminResultResponse,
    AdminUserResponse,
    TestCreateRequest,
    TestResponse,
    TestUpdateRequest,
)
from app.models.user import User
from app.repositories.results import ResultRepository
from app.repositories.users import UserRepository
from app.services.admin_service import AdminService

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    # Rol darajasi: barcha admin endpointlari Administratorni talab qiladi
    # (R14.5). Egalik/biriktirilganlik bu yerda qo'llanmaydi (global boshqaruv).
    dependencies=[Depends(require_admin)],
)


def _to_user_response(user: User) -> AdminUserResponse:
    """``User`` ORM obyektini admin javobiga keltiradi (rol nomini yoyadi)."""
    return AdminUserResponse(
        id=user.id,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role.name if user.role is not None else None,
        organization_id=user.organization_id,
        region_id=user.region_id,
        position=user.position,
    )


@router.get(
    "/users",
    response_model=list[AdminUserResponse],
    summary="Foydalanuvchilar ro'yxati (admin)",
)
def list_users(
    db: Session = Depends(get_db),
) -> list[AdminUserResponse]:
    """Barcha foydalanuvchilarni qaytaradi (R14.1, R4.3).

    Administrator barcha foydalanuvchilar profiliga kira oladi (R4.3). Faqat
    ``require_admin`` o'tgan so'rovchi bu yerga yetadi.
    """
    users = UserRepository(db).list_all()
    return [_to_user_response(u) for u in users]


@router.get(
    "/results",
    response_model=list[AdminResultResponse],
    summary="Natijalar ro'yxati (admin)",
)
def list_results(
    db: Session = Depends(get_db),
) -> list[AdminResultResponse]:
    """Barcha test natijalarini qaytaradi (R14.1, R4.3).

    Natijalar ``created_at`` bo'yicha o'suvchi tartibda (repozitoriy
    ``list_all_with_user``); Administrator barcha natijalarga kira oladi (R4.3).
    """
    results = ResultRepository(db).list_all_with_user()
    return [AdminResultResponse.model_validate(r) for r in results]


@router.post(
    "/tests",
    response_model=TestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Test yaratish",
)
def create_test(
    payload: TestCreateRequest,
    db: Session = Depends(get_db),
) -> TestResponse:
    """Yangi test yaratadi (R14.2).

    Validatsiya servis qatlamida: yaroqsiz qiymat ``ValidationError`` (400),
    hech narsa saqlanmaydi (R14.6). Tranzaksiya chegarasi router zimmasida.
    """
    service = AdminService(db)
    test = service.create_test(
        title=payload.title,
        category=payload.category,
        duration_minutes=payload.duration_minutes,
        description=payload.description,
        is_active=payload.is_active,
    )
    db.commit()
    db.refresh(test)
    return TestResponse.model_validate(test)


@router.patch(
    "/tests/{test_id}",
    response_model=TestResponse,
    summary="Testni yangilash",
)
def update_test(
    test_id: int,
    payload: TestUpdateRequest,
    db: Session = Depends(get_db),
) -> TestResponse:
    """Mavjud testni qisman yangilaydi (R14.2, R14.6).

    Faqat yuborilgan maydonlar uzatiladi (``exclude_unset``), shunda servis
    validatsiyasi faqat o'sha maydonlarga qo'llanadi. Test topilmasa 404,
    yaroqsiz qiymat 400 (hech narsa o'zgartirilmaydi, R14.6).
    """
    patch = payload.model_dump(exclude_unset=True)
    service = AdminService(db)
    test = service.update_test(test_id, **patch)
    db.commit()
    db.refresh(test)
    return TestResponse.model_validate(test)


@router.delete(
    "/tests/{test_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Testni o'chirish yoki nofaol qilish",
)
def delete_test(
    test_id: int,
    hard_delete: bool = Query(
        default=False,
        description="true bo'lsa to'liq o'chiradi; aks holda nofaol qiladi (R14.4)",
    ),
    db: Session = Depends(get_db),
) -> Response:
    """Testni o'chiradi yoki nofaol qiladi — uni faol ro'yxatdan chiqaradi (R14.4).

    Standart holatda test ``is_active=False`` ga o'tkaziladi (yumshoq o'chirish);
    ``?hard_delete=true`` bo'lsa qatori bazadan o'chiriladi. Test topilmasa 404.
    """
    service = AdminService(db)
    service.delete_or_deactivate_test(test_id, hard_delete=hard_delete)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
