"""Portfolio routeri — ``/portfolio/*`` (R11, R20.4).

Foydalanuvchining portfolio yozuvlari: ro'yxat, yuklash (``multipart/form-data``)
va o'chirish. Router ``PortfolioService`` ustidagi yupqa HTTP qatlami:
autentifikatsiya ``get_current_principal`` orqali, barcha amallar so'rovchining
``principal.user_id`` doirasida (owner-scoped). Validatsiya (tur/hajm/nom),
egalik (begona -> 403) va mavjudlik (yo'q -> 404) servis qatlamida (R11.2–R11.7);
markazlashtirilgan handler servis istisnolarini HTTP ga keltiradi.

Fayl xotirasi backend'i sifatida ``LocalFileStorage`` (MVP) ishlatiladi
(``settings.file_storage_dir`` standart bazaviy katalog bilan) — R11, R18.2.

Endpointlar (design.md — "API Design / Portfolio"):

=========================  ======  ==========================================
Yo'l                       Usul    Tavsif
=========================  ======  ==========================================
``/portfolio/me``          GET     yozuvlar (R11.1)
``/portfolio/upload``      POST    multipart; tur/hajm validatsiyasi (R11.2–R11.4)
``/portfolio/{id}``        DELETE  egalik tekshiruvi (R11.5–R11.7)
=========================  ======  ==========================================

Lokal prefiks ``/portfolio``; ``main.py`` uni ``/api/v1`` ostiga ulaydi (18.1).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_principal, get_db
from app.api.schemas import PortfolioItemResponse
from app.services.portfolio_service import PortfolioService
from app.storage.local import LocalFileStorage

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def get_file_storage() -> LocalFileStorage:
    """Fayl xotirasi backend'ini (``LocalFileStorage``) beradi (R18.2).

    Standart bazaviy katalog ``settings.file_storage_dir`` dan olinadi. Alohida
    bog'liqlik sifatida ajratilgani uchun testlar uni vaqtinchalik katalog bilan
    override qilishi mumkin.
    """
    return LocalFileStorage()


@router.get(
    "/me",
    response_model=list[PortfolioItemResponse],
    summary="Portfolio yozuvlari",
)
def list_my_portfolio(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: LocalFileStorage = Depends(get_file_storage),
) -> list[PortfolioItemResponse]:
    """Joriy foydalanuvchi portfoliosini sana bo'yicha kamayuvchi tartibda (R11.1).

    Yozuv bo'lmasa bo'sh ro'yxat qaytadi (xato emas).
    """
    service = PortfolioService(db, storage)
    items = service.list_portfolio(principal.user_id)
    return [PortfolioItemResponse.model_validate(item) for item in items]


@router.post(
    "/upload",
    response_model=PortfolioItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Portfolio fayl yuklash",
)
async def upload_portfolio(
    file: UploadFile = File(..., description="Yuklanadigan fayl (PDF/JPG/PNG/DOC/DOCX)"),
    title: str | None = Form(default=None, description="Yozuv nomi (1–200 belgi)"),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: LocalFileStorage = Depends(get_file_storage),
) -> PortfolioItemResponse:
    """Faylni validatsiya qilib saqlaydi va portfolio yozuvini yaratadi (R11.2).

    So'rov ``multipart/form-data``: ``file`` (UploadFile) va ixtiyoriy ``title``
    form maydoni. Tur (PDF/JPG/PNG/DOC/DOCX — kengaytma + magic/MIME), hajm
    (≤10 485 760 bayt) va nom (1–200) validatsiyasi servis qatlamida; yaroqsiz
    bo'lsa hech narsa saqlanmaydi va 400 qaytadi (R11.3, R11.4, R17.4).
    """
    file_bytes = await file.read()
    service = PortfolioService(db, storage)
    item = service.upload(
        principal.user_id,
        file.filename or "",
        file_bytes,
        content_type=file.content_type,
        title=title,
    )
    db.commit()
    return PortfolioItemResponse.model_validate(item)


@router.delete(
    "/{portfolio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Portfolio yozuvini o'chirish",
)
def delete_portfolio(
    portfolio_id: int,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: LocalFileStorage = Depends(get_file_storage),
) -> Response:
    """Yozuvni va bog'langan faylni o'chiradi (R11.5–R11.7).

    Egalik tekshiruvi servis qatlamida: begona yozuv ``PermissionDeniedError``
    (403, holat o'zgarmaydi — R11.6), mavjud bo'lmagan yozuv ``NotFoundError``
    (404, R11.7). Muvaffaqiyatda tanasi yo'q 204.
    """
    service = PortfolioService(db, storage)
    service.delete(principal.user_id, portfolio_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router", "get_file_storage"]
