"""Parol xeshlash yordamchilari — `passlib` ustidagi yupqa o'ram (wrapper).

Ushbu modul ochiq parolni xavfsiz, tuz (salt) qo'shilgan xesh ko'rinishiga
o'tkazadi va tekshiradi. Ochiq parol hech qachon saqlanmaydi yoki qaytarilmaydi
(R1.4, R17.1; design.md — "Parol xeshlash").

Xeshlash sxemasi: design `bcrypt` yoki `argon2id` ni ruxsat etadi. Bu yerda
asosiy sxema sifatida **argon2** (`argon2-cffi`) ishlatiladi — u zamonaviy,
xotira-qattiq (memory-hard) algoritm bo'lib, parol uzunligi bo'yicha bcrypt'ning
72 baytlik cheklovidan xoli. Eski `bcrypt` xeshlari ham (agar mavjud bo'lsa)
``deprecated="auto"`` orqali tekshirilishi mumkin, shuning uchun kelajakda
migratsiya muammosiz bo'ladi.

Funksiyalar deterministik shartnomaga ega:
- ``hash_password(password)`` -> har safar tasodifiy tuz bilan yangi xesh satri.
- ``verify_password(password, hashed)`` -> mos kelsa ``True``, aks holda ``False``
  (yaroqsiz/buzilgan xesh uchun ham istisno ko'tarmasdan ``False``).
"""

from __future__ import annotations

from passlib.context import CryptContext

# Afzal ko'riladigan sxemalar tartibi: argon2id (zamonaviy, xotira-qattiq) birinchi,
# bcrypt esa muqobil/legacy sifatida. Faqat backendi haqiqatda yuklanadigan
# sxemalar ishlatiladi, shunda turli muhitlarda (qaysi kutubxona o'rnatilganiga
# qarab) modul ishonchli ishlaydi (R1.4, R17.1; design.md — "Parol xeshlash").
_PREFERRED_SCHEMES = ("argon2", "bcrypt")


def _available_schemes() -> list[str]:
    """Backendi haqiqatda yuklanadigan parol xeshlash sxemalarini aniqlaydi.

    Har bir nomzod sxema uchun sinov xeshi hisoblab ko'riladi; backend mavjud
    bo'lmasa yoki yuklab bo'lmasa (masalan, ``passlib``/``bcrypt`` versiya
    nomuvofiqligi), sxema o'tkazib yuboriladi. Bu import vaqtidagi aniqlash
    bo'lgani uchun keng ``Exception`` ushlash ataylab qo'llaniladi.
    """
    schemes: list[str] = []
    for scheme in _PREFERRED_SCHEMES:
        try:
            CryptContext(schemes=[scheme]).hash("probe")
        except Exception:  # noqa: BLE001 - backend mavjudligini aniqlash
            continue
        schemes.append(scheme)
    return schemes


_SCHEMES = _available_schemes() or list(_PREFERRED_SCHEMES)

# ``deprecated="auto"`` — birinchi (afzal) sxemadan boshqa barchasi eskirgan deb
# belgilanadi; shu sababli ``needs_update`` orqali kelajakdagi migratsiya
# aniqlanishi mumkin.
_pwd_context = CryptContext(
    schemes=_SCHEMES,
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """Ochiq parolni tuz qo'shilgan xesh satriga o'tkazadi (R1.4, R17.1).

    Args:
        password: xeshlanadigan ochiq parol.

    Returns:
        Parolning xeshlangan ko'rinishi (sxema, parametrlar va tuzni o'z ichiga
        oluvchi o'zini-tavsiflovchi satr). Har bir chaqiruv tasodifiy tuz
        sababli boshqacha satr qaytaradi.

    Raises:
        TypeError: ``password`` satr (``str``) bo'lmasa.
    """
    if not isinstance(password, str):
        raise TypeError("password must be a string")
    return _pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Ochiq parolni saqlangan xesh bilan solishtiradi (R17.1).

    Funksiya hech qachon istisno ko'tarmaydi: yaroqsiz yoki buzilgan xesh,
    yoxud satr bo'lmagan kirish uchun ham ``False`` qaytaradi.

    Args:
        password: tekshiriladigan ochiq parol.
        hashed: ``hash_password`` qaytargan saqlangan xesh satri.

    Returns:
        ``True`` — parol xeshga mos keladi; aks holda ``False``.
    """
    if not isinstance(password, str) or not isinstance(hashed, str):
        return False
    try:
        return _pwd_context.verify(password, hashed)
    except (ValueError, TypeError):
        # Yaroqsiz yoki tan olinmagan xesh formati — oshkor qilmasdan rad etiladi.
        return False


__all__ = ["hash_password", "verify_password"]
