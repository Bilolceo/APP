"""Savollar (kontent) routeri — ``/questions/*`` (R14, R20.4).

Administrator uchun savol CRUD endpointlari. Router ``AdminService`` ustidagi
yupqa (thin) HTTP qatlami: so'rovni tuzilgan Pydantic modeli sifatida qabul
qiladi, servis metodini chaqiradi va javobni tasdiqlangan javob modeliga
keltiradi. **Biznes validatsiyasi** (matn 1–1000, ball 0.01–1000, kamida 2
variant, mavjud kompetensiya — R14.3, R14.7) servis qatlamida; markazlashtirilgan
exception handler (``app.api.errors``) servis istisnolarini yagona tuzilgan HTTP
javobiga keltiradi (R20.6).

Bu endpointlar **kontent boshqaruvi** bo'lgani uchun admin-guarded:
``require_admin`` bog'liqligi rol darajasida Administratorni talab qiladi; admin
bo'lmagan so'rovchi 403 oladi (R14.5, R4.5). ``GET /questions`` test bo'yicha
savollarni (``?test_id=``) yoki barchasini qaytaradi.

Endpointlar (design.md — "API Design / Savollar (Admin)"):

=========================  ======  ==========================================
Yo'l                       Usul    Tavsif
=========================  ======  ==========================================
``/questions``             GET     savollar ro'yxati (admin)
``/questions``             POST    savol yaratish; 201 (R14.3, R14.7)
``/questions/{id}``        PATCH   tahrirlash (R14.3, R14.6)
``/questions/{id}``        DELETE  o'chirish; 204 (R14.1)
=========================  ======  ==========================================

Lokal prefiks ``/questions``; ``main.py`` uni ``/api/v1`` ostiga ulaydi (18.1).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.middleware.rbac import require_admin
from app.api.schemas import (
    QuestionCreateRequest,
    QuestionResponse,
    QuestionUpdateRequest,
)
from app.repositories.tests import QuestionRepository
from app.services.admin_service import AdminService

router = APIRouter(
    prefix="/questions",
    tags=["questions"],
    # Rol darajasi: barcha savol CRUD endpointlari Administratorni talab qiladi
    # (R14.5). Egalik/biriktirilganlik bu yerda qo'llanmaydi (global kontent).
    dependencies=[Depends(require_admin)],
)


@router.get(
    "",
    response_model=list[QuestionResponse],
    summary="Savollar ro'yxati (admin)",
)
def list_questions(
    test_id: int | None = Query(
        default=None, description="Faqat shu test savollarini qaytaradi (ixtiyoriy)"
    ),
    db: Session = Depends(get_db),
) -> list[QuestionResponse]:
    """Savollar ro'yxatini qaytaradi (R14.1).

    ``test_id`` berilsa, shu testning savollari ``order_index`` bo'yicha
    tartibda qaytadi (R6.3); berilmasa barcha savollar qaytadi. Faqat
    Administrator kira oladi (``require_admin``).
    """
    questions_repo = QuestionRepository(db)
    if test_id is not None:
        questions = questions_repo.list_for_test(test_id)
    else:
        questions = questions_repo.list_all()
    return [QuestionResponse.model_validate(q) for q in questions]


@router.post(
    "",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Savol yaratish",
)
def create_question(
    payload: QuestionCreateRequest,
    db: Session = Depends(get_db),
) -> QuestionResponse:
    """Yangi savol va uning javob variantlarini yaratadi (R14.3, R14.7).

    Validatsiya servis qatlamida: yaroqsiz/to'liqsiz qiymat ``ValidationError``
    (400), mavjud bo'lmagan kompetensiya yoki test ``NotFoundError`` (404).
    Tranzaksiya chegarasi router zimmasida (``commit``).
    """
    service = AdminService(db)
    question = service.create_question(
        test_id=payload.test_id,
        question_text=payload.question_text,
        score=payload.score,
        competency_id=payload.competency_id,
        answers=[a.model_dump() for a in payload.answers],
        question_type=payload.question_type,
        order_index=payload.order_index,
    )
    db.commit()
    db.refresh(question)
    return QuestionResponse.model_validate(question)


@router.patch(
    "/{question_id}",
    response_model=QuestionResponse,
    summary="Savolni tahrirlash",
)
def update_question(
    question_id: int,
    payload: QuestionUpdateRequest,
    db: Session = Depends(get_db),
) -> QuestionResponse:
    """Mavjud savolni qisman yangilaydi (R14.3, R14.6).

    Faqat yuborilgan maydonlar uzatiladi (``exclude_unset``), shunda servis
    validatsiyasi faqat o'sha maydonlarga qo'llanadi. Savol topilmasa 404,
    yaroqsiz qiymat 400, mavjud bo'lmagan kompetensiya 404.
    """
    patch = payload.model_dump(exclude_unset=True)
    service = AdminService(db)
    question = service.update_question(question_id, **patch)
    db.commit()
    db.refresh(question)
    return QuestionResponse.model_validate(question)


@router.delete(
    "/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Savolni o'chirish",
)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
) -> Response:
    """Savolni va uning javob variantlarini o'chiradi (R14.1).

    Savol topilmasa ``NotFoundError`` (404). Muvaffaqiyatda tanasi yo'q 204.
    """
    service = AdminService(db)
    service.delete_question(question_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
