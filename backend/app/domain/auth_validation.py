"""Autentifikatsiya kirish validatsiyasi — sof (pure) yordamchi funksiyalar.

Ushbu modul ro'yxatdan o'tish (Requirement 1) uchun zarur bo'lgan kirish
validatsiyasini I/O dan (DB, tarmoq, fayl) mustaqil, deterministik sof
funksiyalar sifatida belgilaydi. Shu sababli ular property-based testlar uchun
ideal nishon hisoblanadi (Property 1 — "Ro'yxatdan o'tish validatsiyasi yaroqsiz
maydonni rad etadi").

Bog'liq talablar:
- R1.1: yaroqli kirish to'plami bilan hisob yaratiladi (validatorlar yaroqlilik
  shartini belgilaydi).
- R1.3: majburiy maydon (telefon, parol, to'liq ism, rol) kiritilmagan yoki
  faqat bo'sh joy belgilaridan iborat bo'lsa rad etiladi.
- R1.5: parol uzunligi 8–64 belgi oralig'ida bo'lishi shart.
- R1.6: telefon raqami `+998` bilan boshlanib, jami 13 belgi bo'lishi shart.
- R1.7: rol faqat {Rahbar, Ekspert, Administrator} ro'yxatidan biri bo'lishi shart.

Eslatma: bu yerda faqat sof validatorlar e'lon qilinadi. Parol xeshlash
`app.core.security` modulida, login bloklash/reset-kod mantig'i esa keyingi
vazifalarda (8.4) joylashadi. Validatorlar hech qanday holatni o'zgartirmaydi
va istisno (exception) ko'tarmaydi — ular faqat ``bool`` qaytaradi.
"""

from __future__ import annotations

# --- Telefon raqami formati (R1.6) ---
PHONE_PREFIX = "+998"
PHONE_LENGTH = 13

# --- Parol uzunligi chegaralari (R1.5) ---
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 64

# --- Yaroqli rollar whitelisti (R1.7) ---
VALID_ROLES: frozenset[str] = frozenset({"Rahbar", "Ekspert", "Administrator"})


def validate_phone(phone: object) -> bool:
    """Telefon raqami formatini tekshiradi (R1.6).

    Yaroqlilik sharti: qiymat satr (``str``) bo'lib, ``+998`` bilan boshlanadi
    va jami uzunligi aynan 13 belgi bo'ladi.

    Args:
        phone: tekshiriladigan telefon raqami.

    Returns:
        ``True`` — format yaroqli; aks holda ``False``.
    """
    if not isinstance(phone, str):
        return False
    return len(phone) == PHONE_LENGTH and phone.startswith(PHONE_PREFIX)


def validate_password(password: object) -> bool:
    """Parol uzunligini tekshiradi (R1.5).

    Yaroqlilik sharti: qiymat satr bo'lib, uzunligi 8 dan 64 gacha (chegaralar
    qo'shilgan holda) bo'ladi.

    Args:
        password: tekshiriladigan parol.

    Returns:
        ``True`` — uzunlik 8–64 oralig'ida; aks holda ``False``.
    """
    if not isinstance(password, str):
        return False
    return PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH


def validate_role(role: object) -> bool:
    """Rolni yaroqli rollar whitelistiga nisbatan tekshiradi (R1.7).

    Yaroqlilik sharti: qiymat satr bo'lib, {Rahbar, Ekspert, Administrator}
    to'plamidan biriga aynan teng bo'ladi (katta-kichik harfga sezgir).

    Args:
        role: tekshiriladigan rol nomi.

    Returns:
        ``True`` — rol yaroqli; aks holda ``False``.
    """
    if not isinstance(role, str):
        return False
    return role in VALID_ROLES


def validate_required(value: object) -> bool:
    """Majburiy maydon mavjudligini tekshiradi (R1.3).

    Maydon quyidagi hollarda yaroqsiz (mavjud emas) hisoblanadi:
    - qiymat ``None`` bo'lsa (kiritilmagan);
    - qiymat satr bo'lib, faqat bo'sh joy belgilaridan iborat yoki bo'sh bo'lsa
      (``"   "`` yoki ``""``).

    Bo'sh joy belgilaridan tashqari mazmunga ega satrlar va satr bo'lmagan
    (``None`` dan farqli) qiymatlar mavjud deb qabul qilinadi.

    Args:
        value: tekshiriladigan majburiy maydon qiymati.

    Returns:
        ``True`` — maydon mavjud va bo'sh emas; aks holda ``False``.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


__all__ = [
    "PHONE_PREFIX",
    "PHONE_LENGTH",
    "PASSWORD_MIN_LENGTH",
    "PASSWORD_MAX_LENGTH",
    "VALID_ROLES",
    "validate_phone",
    "validate_password",
    "validate_role",
    "validate_required",
]
