"""`FileStorageBackend` abstrakt interfeysi — fayl xotirasi abstraksiyasi.

Portfolio fayllarini (R11) provayderdan mustaqil saqlash uchun yagona shartnoma
belgilanadi. MVP'da `LocalFileStorage`, kelajakda esa `S3FileStorage`
implementatsiyasi shu interfeysni qondiradi (R18.2). Servis qatlami faqat shu
abstraksiyaga bog'lanadi, shuning uchun xotira provayderini kodning qolgan
qismini o'zgartirmasdan almashtirish mumkin.

Eslatma: bu vazifada (1.2) faqat abstrakt interfeys e'lon qilinadi; konkret
backendlar (`LocalFileStorage`, `S3FileStorage`) alohida vazifalarda (13.x)
qo'shiladi.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class StoredFile:
    """Saqlangan fayl haqidagi metama'lumot.

    Maydonlar:
    - ``storage_key``: provayderdan mustaqil noyob kalit (`files.storage_key`).
    - ``url``: faylga kirish havolasi (`files.file_url`).
    - ``size_bytes``: fayl hajmi (baytlarda) (`files.size_bytes`).
    - ``content_type``: fayl MIME turi (ixtiyoriy).
    """

    storage_key: str
    url: str
    size_bytes: int
    content_type: str | None = None


class FileStorageBackend(ABC):
    """Fayl xotirasi uchun abstrakt backend (provayderdan mustaqil).

    Konkret implementatsiyalar (`LocalFileStorage`, `S3FileStorage`) quyidagi
    abstrakt metodlarni amalga oshirishi shart (R18.2).
    """

    @abstractmethod
    def save(self, key: str, data: bytes, *, content_type: str | None = None) -> StoredFile:
        """Fayl baytlarini berilgan kalit ostida saqlaydi.

        Args:
            key: faylni saqlash uchun provayderdan mustaqil noyob kalit.
            data: fayl mazmuni (baytlar).
            content_type: fayl MIME turi (ixtiyoriy).

        Returns:
            Saqlangan fayl metama'lumoti (`StoredFile`).
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Berilgan kalit bo'yicha fayl baytlarini qaytaradi.

        Args:
            key: saqlashda ishlatilgan kalit.

        Returns:
            Fayl mazmuni (baytlar).
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        """Berilgan kalit bo'yicha faylni o'chiradi (R11.5).

        Args:
            key: o'chiriladigan faylning kaliti.
        """
        raise NotImplementedError


__all__ = ["FileStorageBackend", "StoredFile"]
