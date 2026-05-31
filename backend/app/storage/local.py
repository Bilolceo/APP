"""`LocalFileStorage` — lokal fayl tizimi backend'i (R11, R18.2).

`FileStorageBackend` abstraksiyasining MVP implementatsiyasi. Fayllar
``settings.file_storage_dir`` katalogi ostida `storage_key` nomi bilan
saqlanadi. Bu backend provayderdan mustaqil shartnomani (`save`/`get`/`delete`)
qondiradi; kelajakda `S3FileStorage` shu interfeysni almashtirib qo'yishi mumkin
(bu vazifada S3 amalga oshirilmaydi).

Tamoyillar:
- `save` fayl baytlarini berilgan kalit ostida yozadi, kerakli kataloglarni
  yaratadi va `StoredFile` metama'lumotini qaytaradi.
- Kalit (`key`) `base_dir` ichida hal qilinadi; katalogdan tashqariga chiqishga
  urinish (path traversal: ``..``, absolyut yo'l) rad etiladi (R17.4 — xavfsizlik).
- `delete` idempotent: mavjud bo'lmagan fayl xato chiqarmaydi (R11.5).
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.storage.base import FileStorageBackend, StoredFile


class LocalFileStorage(FileStorageBackend):
    """Lokal fayl tizimida saqlovchi backend (R18.2).

    Args:
        base_dir: fayllar saqlanadigan ildiz katalog; ``None`` bo'lsa
            ``settings.file_storage_dir`` ishlatiladi.
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base_dir = Path(base_dir if base_dir is not None else settings.file_storage_dir)

    # -- Yordamchi ----------------------------------------------------------

    @staticmethod
    def generate_key(filename: str | None = None) -> str:
        """Provayderdan mustaqil noyob `storage_key` yaratadi.

        Noyoblik uchun ``uuid4`` ishlatiladi; agar ``filename`` berilsa, uning
        kengaytmasi (kichik harflarda) saqlanib qoladi (masalan ``.pdf``).

        Args:
            filename: original fayl nomi (kengaytmani aniqlash uchun, ixtiyoriy).

        Returns:
            Noyob kalit (masalan ``"3f9c...e1.pdf"``).
        """
        suffix = ""
        if filename:
            suffix = Path(filename).suffix.lower()
        return f"{uuid4().hex}{suffix}"

    def _resolve(self, key: str) -> Path:
        """Kalitni `base_dir` ichidagi absolyut yo'lga hal qiladi (xavfsiz).

        ``base_dir`` dan tashqariga chiqishga urinish (``..`` yoki absolyut
        kalit) ``ValueError`` bilan rad etiladi (R17.4).
        """
        if not key:
            raise ValueError("storage_key bo'sh bo'lishi mumkin emas")
        base = self._base_dir.resolve()
        candidate = (base / key).resolve()
        if base != candidate and base not in candidate.parents:
            raise ValueError("storage_key katalog chegarasidan tashqariga chiqa olmaydi")
        return candidate

    # -- FileStorageBackend interfeysi --------------------------------------

    def save(self, key: str, data: bytes, *, content_type: str | None = None) -> StoredFile:
        """Fayl baytlarini berilgan kalit ostida saqlaydi (R11.2).

        Kerakli kataloglar avtomatik yaratiladi. Qaytariladigan `StoredFile`
        kalit, kirish havolasi (``file://`` URI), hajm va MIME turini o'z ichiga
        oladi.
        """
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return StoredFile(
            storage_key=key,
            url=path.as_uri(),
            size_bytes=len(data),
            content_type=content_type,
        )

    def get(self, key: str) -> bytes:
        """Berilgan kalit bo'yicha fayl baytlarini qaytaradi.

        Raises:
            FileNotFoundError: fayl mavjud bo'lmasa.
        """
        path = self._resolve(key)
        if not path.is_file():
            raise FileNotFoundError(f"Fayl topilmadi: {key}")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        """Berilgan kalit bo'yicha faylni o'chiradi (R11.5) — idempotent.

        Mavjud bo'lmagan fayl uchun xato chiqarmaydi.
        """
        path = self._resolve(key)
        path.unlink(missing_ok=True)


__all__ = ["LocalFileStorage"]
