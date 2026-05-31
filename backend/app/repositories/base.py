"""Repository asosiy klassi — umumiy CRUD yordamchilari.

Repository qatlami ORM ustida o'tiradi va servislar uchun ma'lumotlarga kirish
nuqtasi bo'lib xizmat qiladi (design.md — "Backend ichki qatlamlari"). Repository
klasslari **yupqa** (thin) bo'ladi: faqat so'rov/persistensiya bilan shug'ullanadi,
biznes qoidalari servis qatlamida (keyingi vazifalar) joylashadi.

Konvensiyalar:
- Har bir repository konstruktorda SQLAlchemy `Session` ni oladi.
- So'rovlar SQLAlchemy 2.x `select()` uslubida yoziladi.
- Yaratish (`create`/`add`) operatsiyalari `flush` qiladi (ID populyatsiyasi
  uchun), ammo `commit` qilmaydi — tranzaksiya chegarasi chaqiruvchida (masalan
  `app.core.db.get_session` kontekst-menejeri yoki servis) boshqariladi.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Barcha repositorylar uchun umumiy asos.

    Args:
        session: faol SQLAlchemy `Session`.
    """

    #: Ushbu repository boshqaradigan ORM model klassi.
    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int) -> ModelT | None:
        """Birlamchi kalit bo'yicha bitta yozuvni qaytaradi (yoki ``None``)."""
        return self.session.get(self.model, entity_id)

    def list_all(self) -> list[ModelT]:
        """Modelning barcha yozuvlarini qaytaradi."""
        return list(self.session.scalars(select(self.model)).all())

    def add(self, instance: ModelT) -> ModelT:
        """Yangi yozuvni sessiyaga qo'shadi va ID uchun `flush` qiladi."""
        self.session.add(instance)
        self.session.flush()
        return instance

    def delete(self, instance: ModelT) -> None:
        """Yozuvni o'chiradi va o'zgarishni `flush` qiladi."""
        self.session.delete(instance)
        self.session.flush()


__all__ = ["BaseRepository"]
