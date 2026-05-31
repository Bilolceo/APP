"""Profil_Moduli — profil ko'rish va tahrirlash servisi (R5).

Ushbu servis framework'dan mustaqil (FastAPI'siz): konstruktorga SQLAlchemy
`Session` yoki tayyor `UserRepository` beriladi va biznes qoidalari shu yerda
hal qilinadi. Repository qatlami yupqa (thin) bo'lib qoladi.

Mas'uliyat (design.md — "Profil_Moduli"):
- ``get_profile(user_id)`` — to'liq profil maydonlarini qaytaradi (R5.1);
  foydalanuvchi topilmasa `NotFoundError`.
- ``update_profile(user_id, patch)`` — faqat tahrirlanadigan maydonlarni
  yangilaydi; ish staji 0–60 butun son, matn maydonlari ≤200 belgi (R5.2, R5.3);
  telefon raqami (hisob identifikatori) o'zgartirilishini rad etadi (R5.4);
  validatsiya muvaffaqiyatsiz bo'lsa hech narsa saqlanmaydi va qaysi maydon
  yaroqsizligi bildiriladi.

Tahrirlanadigan maydonlar (R5.2): to'liq ism, ish joyi (tashkilot), lavozim,
ish staji, ta'lim darajasi, malaka oshirish kurslari, sertifikatlar, hudud,
tashkilot turi. ``phone`` (R5.4) va boshqa maydonlar (``role_id``,
``password_hash``, login-lockout holati va h.k.) bu yerda o'zgartirilmaydi.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.users import UserRepository

# ---------------------------------------------------------------------------
# Xato tiplari — app.services.errors mavjud bo'lsa undan import qilinadi.
#
# ESLATMA (unify qilinishi kerak): `app/services/errors.py` moduli AuthService
# vazifasi bilan parallel ishlab chiqilmoqda. U tayyor bo'lgach, quyidagi lokal
# fallback olib tashlanib, faqat `from app.services.errors import ...` qoldirilishi
# kerak. Hozircha modul mavjud bo'lmasligi mumkin, shuning uchun himoyalangan
# (defensive) import + minimal lokal fallback ishlatiladi.
# ---------------------------------------------------------------------------
try:  # pragma: no cover - import yo'li muhitga bog'liq
    from app.services.errors import NotFoundError, ValidationError  # type: ignore
except ImportError:  # pragma: no cover

    class _ProfileServiceError(Exception):
        """Vaqtinchalik lokal asosiy xato — `app.services.errors` bilan birlashtiriladi."""

    class ValidationError(_ProfileServiceError):  # type: ignore[no-redef]
        """Yaroqsiz maydon (400). `app.services.errors.ValidationError` o'rnini bosadi."""

    class NotFoundError(_ProfileServiceError):  # type: ignore[no-redef]
        """Resurs topilmadi (404). `app.services.errors.NotFoundError` o'rnini bosadi."""


# ---------------------------------------------------------------------------
# Tahrirlanadigan maydonlar va validatsiya cheklovlari (R5.2, R5.3)
# ---------------------------------------------------------------------------

#: Matnli tahrirlanadigan maydonlar — har biri ≤200 belgi bo'lishi shart (R5.3).
_TEXT_FIELDS: frozenset[str] = frozenset(
    {
        "full_name",
        "position",
        "education_level",
        "qualification_courses",
        "certificates",
        "org_type",
    }
)

#: Reference (FK) tahrirlanadigan maydonlar: hudud va ish joyi (tashkilot).
#: ``region`` -> ``region_id``, ``workplace``/``ish joyi`` -> ``organization_id``.
_REFERENCE_FIELDS: frozenset[str] = frozenset({"region_id", "organization_id"})

#: Butun son maydoni — ish staji (R5.3).
_INT_FIELD = "experience_years"

#: Boolean tahrirlanadigan maydonlar.
_BOOL_FIELDS: frozenset[str] = frozenset({"notifications_enabled"})

#: Barcha tahrirlanadigan maydonlar to'plami (R5.2, R16.5).
EDITABLE_FIELDS: frozenset[str] = (
    _TEXT_FIELDS | _REFERENCE_FIELDS | _BOOL_FIELDS | {_INT_FIELD}
)

#: Matn maydoni maksimal uzunligi (R5.3).
MAX_TEXT_LENGTH = 200

#: Ish staji oralig'i (R5.3).
MIN_EXPERIENCE_YEARS = 0
MAX_EXPERIENCE_YEARS = 60


@dataclass(frozen=True)
class Profile:
    """Foydalanuvchi profili (R5.1) — o'qish uchun transient ko'rinish.

    ``organization_id`` ish joyini (workplace), ``region_id`` esa hududni
    ifodalaydi (model FK sifatida saqlaydi). Router qatlami zarur bo'lsa
    nomlarini hal qiladi.
    """

    id: int
    full_name: str
    phone: str
    organization_id: int | None
    position: str | None
    experience_years: int | None
    education_level: str | None
    qualification_courses: str | None
    certificates: str | None
    region_id: int | None
    org_type: str | None
    notifications_enabled: bool


def _to_profile(user: User) -> Profile:
    """`User` ORM yozuvini transient `Profile` ga aylantiradi (R5.1)."""
    return Profile(
        id=user.id,
        full_name=user.full_name,
        phone=user.phone,
        organization_id=user.organization_id,
        position=user.position,
        experience_years=user.experience_years,
        education_level=user.education_level,
        qualification_courses=user.qualification_courses,
        certificates=user.certificates,
        region_id=user.region_id,
        org_type=user.org_type,
        notifications_enabled=bool(user.notifications_enabled),
    )


def _validation_error(message: str, field: str | None) -> ValidationError:
    """Yaroqsiz maydonni ko'rsatuvchi `ValidationError` yaratadi (R5.3, R20.6).

    Maydon nomi xabarga ham kiritiladi va instansiyaning ``field`` atributiga ham
    yoziladi — bu `app.services.errors.ValidationError` qanday qurilganidan qat'i
    nazar ishlaydi (atributni o'rnatish har doim mumkin).
    """
    err = ValidationError(message)
    err.field = field  # type: ignore[attr-defined]
    return err


class ProfileService:
    """Profil ko'rish va tahrirlash servisi (R5)."""

    def __init__(self, users: UserRepository | Session) -> None:
        """`UserRepository` yoki SQLAlchemy `Session` qabul qiladi.

        Args:
            users: tayyor `UserRepository` yoki uni qurish uchun faol `Session`.
        """
        self._users = users if isinstance(users, UserRepository) else UserRepository(users)

    # -- O'qish -------------------------------------------------------------

    def get_profile(self, user_id: int) -> Profile:
        """Foydalanuvchining to'liq profilini qaytaradi (R5.1).

        Raises:
            NotFoundError: foydalanuvchi mavjud bo'lmasa.
        """
        user = self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError(f"Foydalanuvchi topilmadi (id={user_id})")
        return _to_profile(user)

    # -- Yangilash ----------------------------------------------------------

    def update_profile(self, user_id: int, patch: Mapping[str, Any] | None) -> Profile:
        """Tahrirlanadigan profil maydonlarini yangilaydi (R5.2, R5.3, R5.4).

        Validatsiya muvaffaqiyatsiz bo'lsa hech narsa saqlanmaydi va qaysi maydon
        yaroqsizligi bildiriladi. Telefon raqamini o'zgartirishga urinish rad
        etiladi (R5.4).

        Args:
            user_id: yangilanadigan foydalanuvchi identifikatori.
            patch: yangilanadigan maydon -> qiymat moslamasi.

        Returns:
            Yangilangan `Profile`.

        Raises:
            NotFoundError: foydalanuvchi mavjud bo'lmasa.
            ValidationError: telefonni o'zgartirishga urinish, yaroqsiz maydon
                yoki ruxsat etilmagan maydon kiritilganda.
        """
        user = self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError(f"Foydalanuvchi topilmadi (id={user_id})")

        # MUHIM: avval to'liq validatsiya, keyin persistensiya — yaroqsiz so'rov
        # hech qanday holatni o'zgartirmasligi kerak (R5.3, R20.6).
        updates = self._validate_patch(patch or {})

        if updates:
            # Repository ``phone`` ni baribir e'tiborsiz qoldiradi (defense in
            # depth), ammo biz uni allaqachon yuqorida rad etganmiz (R5.4).
            self._users.update(user, **updates)

        return _to_profile(user)

    # -- Ichki validatsiya --------------------------------------------------

    def _validate_patch(self, patch: Mapping[str, Any]) -> dict[str, Any]:
        """Patch'ni validatsiya qiladi va yangilanadigan maydonlarni qaytaradi.

        Hech narsa saqlamaydi; faqat tekshiradi va tozalangan dict qaytaradi.
        """
        updates: dict[str, Any] = {}
        for key, value in patch.items():
            # Telefon raqami — hisob identifikatori, o'zgarmas (R5.4).
            if key == "phone":
                raise _validation_error(
                    "Telefon raqami (hisob identifikatori) tahrirlab bo'lmaydi",
                    "phone",
                )
            # Ruxsat etilmagan / noma'lum maydon — saqlashga ruxsat berilmaydi.
            if key not in EDITABLE_FIELDS:
                raise _validation_error(
                    f"'{key}' maydonini tahrirlash mumkin emas",
                    key,
                )

            if key == _INT_FIELD:
                updates[key] = self._validate_experience_years(value)
            elif key in _REFERENCE_FIELDS:
                updates[key] = self._validate_reference(key, value)
            elif key in _BOOL_FIELDS:
                updates[key] = self._validate_bool(key, value)
            else:  # matn maydoni
                updates[key] = self._validate_text(key, value)

        return updates

    @staticmethod
    def _validate_experience_years(value: Any) -> int | None:
        """Ish staji 0–60 oralig'idagi butun son ekanini tekshiradi (R5.3)."""
        if value is None:
            return None
        # ``bool`` — ``int`` ning quyi klassi; uni alohida rad etamiz.
        if isinstance(value, bool) or not isinstance(value, int):
            raise _validation_error(
                "Ish staji 0–60 oralig'idagi butun son bo'lishi kerak",
                _INT_FIELD,
            )
        if value < MIN_EXPERIENCE_YEARS or value > MAX_EXPERIENCE_YEARS:
            raise _validation_error(
                "Ish staji 0–60 oralig'ida bo'lishi kerak",
                _INT_FIELD,
            )
        return value

    @staticmethod
    def _validate_text(key: str, value: Any) -> str | None:
        """Matn maydoni ≤200 belgi ekanini tekshiradi (R5.3).

        ``full_name`` majburiy (NOT NULL, 1–200) bo'lgani uchun bo'sh yoki faqat
        bo'sh joydan iborat qiymat rad etiladi (R5.2 — yaroqli qiymat).
        """
        if value is None:
            if key == "full_name":
                raise _validation_error("To'liq ism bo'sh bo'lishi mumkin emas", key)
            return None
        if not isinstance(value, str):
            raise _validation_error(f"'{key}' maydoni matn bo'lishi kerak", key)
        if len(value) > MAX_TEXT_LENGTH:
            raise _validation_error(
                f"'{key}' maydoni {MAX_TEXT_LENGTH} belgidan oshmasligi kerak",
                key,
            )
        if key == "full_name" and not value.strip():
            raise _validation_error("To'liq ism bo'sh bo'lishi mumkin emas", key)
        return value

    @staticmethod
    def _validate_reference(key: str, value: Any) -> int | None:
        """Reference (FK) maydoni musbat butun son yoki ``None`` ekanini tekshiradi."""
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            raise _validation_error(
                f"'{key}' maydoni butun son (identifikator) bo'lishi kerak",
                key,
            )
        if value <= 0:
            raise _validation_error(
                f"'{key}' maydoni musbat identifikator bo'lishi kerak",
                key,
            )
        return value

    @staticmethod
    def _validate_bool(key: str, value: Any) -> bool:
        """Boolean maydonni tekshiradi."""
        if not isinstance(value, bool):
            raise _validation_error(f"'{key}' maydoni true/false bo'lishi kerak", key)
        return value


__all__ = [
    "ProfileService",
    "Profile",
    "EDITABLE_FIELDS",
    "MAX_TEXT_LENGTH",
    "MIN_EXPERIENCE_YEARS",
    "MAX_EXPERIENCE_YEARS",
]
