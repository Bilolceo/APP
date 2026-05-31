"""Login bloklash va parolni tiklash kodi — sof (pure) domen mantig'i.

Ushbu modul autentifikatsiyaning ikki xavfsizlik mexanizmini I/O dan (DB,
tarmoq, fayl) **mustaqil**, deterministik sof funksiyalar sifatida belgilaydi:

1. **Login bloklash (R2.7)** — ketma-ket 5 marta noto'g'ri parol urinishidan
   keyin hisob 15 daqiqaga vaqtincha bloklanadi; muvaffaqiyatli kirish
   hisoblagichni nolga tushiradi (design.md — "Login bloklash").
2. **Parolni tiklash kodi (R3.1, R3.4, R3.5, R3.6, R3.7)** — 6 raqamli kod,
   yuborilgandan keyin 15 daqiqa amal qiladi; noto'g'ri yoki muddati o'tgan kod
   rad etiladi; bitta kod uchun 5 martadan ko'p noto'g'ri urinishda kod bekor
   qilinadi (design.md — "Parolni tiklash xavfsizligi").

Barcha funksiyalar **vaqtni** tashqaridan (``now`` parametri) qabul qiladi va
hech qanday holatni o'zgartirmaydi — ular kirish maydonlari asosida yangi qiymat
yoki qaror qaytaradi. Shu sababli ular property-based testlar uchun ideal nishon
hisoblanadi (sof, deterministik, framework'dan mustaqil — Property 3, 8, 9).

Eslatma (vazifa doirasi 8.4): bu yerda faqat sof mantiq joylashadi. Doimiy
saqlash (``users.failed_login_count``/``locked_until``, ``password_reset_codes``)
va kodni xeshlash/yuborish keyingi vazifada (9.3 — AuthService) shu funksiyalarni
ulaydi. Bu funksiyalar kodni ochiq matnda solishtirishni majburlamaydi:
chaqiruvchi ``expected_code`` o'rnida xeshlangan qiymatlarni ham uzatishi mumkin
(konstanta-vaqtli solishtirish servis qatlamining mas'uliyati).

Vaqt belgilari (``now``, ``locked_until``, ``expires_at``, ``issued_at``) bir xil
timezone konvensiyasida (masalan, barchasi UTC-aware) berilishi shart; modul
ularni faqat solishtiradi va qo'shadi, tabiatini o'zgartirmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from app.core.config import settings
from app.domain.auth_validation import PASSWORD_MIN_LENGTH

# ---------------------------------------------------------------------------
# Konstantalar (config'dan standart, lekin funksiyalar parametrlangan)
# ---------------------------------------------------------------------------

# Login bloklash chegarasi va davomiyligi (R2.7) — config'dan standart qiymatlar.
MAX_FAILED_LOGIN_ATTEMPTS: int = settings.max_failed_login_attempts
LOGIN_LOCKOUT_MINUTES: int = settings.login_lockout_minutes

# Parolni tiklash kodi (R3.1, R3.5) — aynan 6 raqam, 15 daqiqa amal.
RESET_CODE_LENGTH: int = 6
RESET_CODE_TTL_MINUTES: int = settings.password_reset_code_expire_minutes

# Bitta tasdiqlash kodi uchun ruxsat etilgan noto'g'ri urinishlar soni (R3.7):
# "5 martadan ko'p" noto'g'ri urinishda kod bekor qilinadi. Config'da alohida
# maydon yo'q, shuning uchun modul darajasidagi konstanta sifatida belgilanadi.
MAX_RESET_CODE_ATTEMPTS: int = 5

_ASCII_DIGITS = frozenset("0123456789")


def _coerce_comparable(left: datetime, right: datetime) -> tuple[datetime, datetime]:
    """Ikki ``datetime`` ni solishtirishga yaroqli holatga keltiradi.

    Modul shartnomasi vaqt belgilarini bir xil timezone konvensiyasida kutadi
    (odatda UTC-aware). Ammo ayrim saqlash backendlari (masalan SQLite test
    muhitida) tz-**naive** ``datetime`` qaytaradi, production PostgreSQL
    ``TIMESTAMPTZ`` esa tz-**aware** beradi. Bunday aralash holatda Python
    ``TypeError`` ko'taradi. Bu yordamchi mosligini ta'minlaydi: agar biri aware
    va ikkinchisi naive bo'lsa, **naive** qiymat ikkinchisining ``tzinfo`` siga
    o'rnatiladi (qiymat o'zgartirilmaydi — UTC konvensiyasi nazarda tutiladi).

    Args:
        left: birinchi vaqt.
        right: ikkinchi vaqt.

    Returns:
        Ikkalasi ham aware yoki ikkalasi ham naive bo'lgan juftlik.
    """
    left_aware = left.tzinfo is not None
    right_aware = right.tzinfo is not None
    if left_aware == right_aware:
        return left, right
    if left_aware:
        return left, right.replace(tzinfo=left.tzinfo)
    return left.replace(tzinfo=right.tzinfo), right


# ===========================================================================
# Login bloklash (R2.7)
# ===========================================================================


@dataclass(frozen=True)
class LockoutState:
    """Hisobning login bloklash holati (transient, sof qiymat).

    Maydonlar:
    - ``failed_count``: ketma-ket noto'g'ri urinishlar soni
      (``users.failed_login_count`` ga mos).
    - ``locked_until``: bloklash tugaydigan vaqt; ``None`` bo'lsa hisob
      bloklanmagan (``users.locked_until`` ga mos).
    """

    failed_count: int
    locked_until: datetime | None = None


def register_failed_attempt(
    current_count: int,
    now: datetime,
    *,
    threshold: int = MAX_FAILED_LOGIN_ATTEMPTS,
    lockout_minutes: int = LOGIN_LOCKOUT_MINUTES,
) -> LockoutState:
    """Noto'g'ri parol urinishini hisobga oladi va yangi bloklash holatini qaytaradi (R2.7).

    Hisoblagich bittaga oshiriladi. Yangi hisoblagich ``threshold`` (standart 5)
    ga yetganda yoki undan oshganda, hisob ``now + lockout_minutes`` (standart
    15 daqiqa) gacha bloklanadi va ``locked_until`` shu vaqtga o'rnatiladi. Aks
    holda ``locked_until`` ``None`` bo'ladi (hali bloklanmagan).

    Funksiya sof: u kirishni o'zgartirmaydi va faqat yangi ``LockoutState``
    qaytaradi.

    Args:
        current_count: joriy ketma-ket noto'g'ri urinishlar soni (>= 0).
        now: joriy vaqt (bloklash boshlanish nuqtasi).
        threshold: bloklashga olib keladigan urinishlar soni (standart — config).
        lockout_minutes: bloklash davomiyligi daqiqalarda (standart — config).

    Returns:
        Yangilangan ``LockoutState`` (yangi hisoblagich va, kerak bo'lsa,
        ``locked_until``).
    """
    new_count = current_count + 1
    if new_count >= threshold:
        return LockoutState(
            failed_count=new_count,
            locked_until=now + timedelta(minutes=lockout_minutes),
        )
    return LockoutState(failed_count=new_count, locked_until=None)


def is_locked(locked_until: datetime | None, now: datetime) -> bool:
    """Hisob hozir bloklanganligini aniqlaydi (R2.7).

    Args:
        locked_until: bloklash tugaydigan vaqt yoki ``None``.
        now: joriy vaqt.

    Returns:
        ``True`` — ``locked_until`` belgilangan va ``now`` undan oldin
        (``now < locked_until``); aks holda ``False``. ``locked_until`` ``None``
        bo'lsa hisob hech qachon bloklanmagan deb hisoblanadi. Bloklash muddati
        tugagach (``now >= locked_until``) hisob avtomatik ochiladi.
    """
    if locked_until is None:
        return False
    now, locked_until = _coerce_comparable(now, locked_until)
    return now < locked_until


def reset_after_success() -> LockoutState:
    """Muvaffaqiyatli kirishdan keyingi bloklash holatini qaytaradi (R2.7).

    Muvaffaqiyatli login hisoblagichni **nolga** tushiradi va har qanday
    bloklashni bekor qiladi. Bu reset semantikasini bitta joyda hujjatlashtiradi:
    chaqiruvchi (AuthService) muvaffaqiyatli autentifikatsiyadan so'ng
    ``users.failed_login_count = 0`` va ``users.locked_until = NULL`` qilib
    saqlashi lozim.

    Returns:
        Toza ``LockoutState(failed_count=0, locked_until=None)``.
    """
    return LockoutState(failed_count=0, locked_until=None)


# ===========================================================================
# Parolni tiklash kodi (R3.1, R3.4, R3.5, R3.6, R3.7)
# ===========================================================================


class ResetCodeStatus(str, Enum):
    """Parolni tiklash kodini tekshirish natijasi (R3.4, R3.5, R3.7).

    A'zolar:
    - ``VALID``: kod yaroqli — parolni yangilash davom ettirilishi mumkin.
    - ``CONSUMED``: kod allaqachon ishlatilgan (R3.3) — qayta ishlatib bo'lmaydi.
    - ``TOO_MANY_ATTEMPTS``: kod 5 martadan ko'p noto'g'ri urinish tufayli
      allaqachon bekor qilingan (R3.7).
    - ``EXPIRED``: kod muddati o'tgan (yuborilganidan 15 daqiqadan ko'p; R3.4).
    - ``INVALID_FORMAT``: kiritilgan kod 6 raqamli formatga mos emas (R3.5).
    - ``MISMATCH``: kod formati to'g'ri, lekin kutilgan kodga mos kelmadi (R3.5).
    """

    VALID = "valid"
    CONSUMED = "consumed"
    TOO_MANY_ATTEMPTS = "too_many_attempts"
    EXPIRED = "expired"
    INVALID_FORMAT = "invalid_format"
    MISMATCH = "mismatch"


@dataclass(frozen=True)
class ResetCodeCheck:
    """Parolni tiklash kodini tekshirishning sof natijasi.

    Maydonlar:
    - ``status``: tekshiruv natijasi (``ResetCodeStatus``).
    - ``attempts``: tekshiruvdan keyingi noto'g'ri urinishlar soni. Noto'g'ri
      format yoki mos kelmagan kod uchun bittaga oshadi; boshqa holatlarda
      o'zgarmaydi.
    - ``invalidated``: kod shu tekshiruvdan keyin bekor qilinishi kerakligini
      bildiradi (muddati o'tgan, allaqachon ishlatilgan yoki 5 dan ortiq
      urinish — R3.4, R3.7).
    """

    status: ResetCodeStatus
    attempts: int
    invalidated: bool

    @property
    def is_valid(self) -> bool:
        """Kod yaroqli bo'lsa (parolni yangilashga ruxsat) ``True`` qaytaradi."""
        return self.status is ResetCodeStatus.VALID


def is_reset_code_format_valid(code: object) -> bool:
    """Tasdiqlash kodi aynan 6 raqamdan iboratligini tekshiradi (R3.5).

    Yaroqlilik sharti: qiymat satr (``str``) bo'lib, uzunligi aynan 6 va barcha
    belgilari ASCII raqamlari (``0``–``9``). ``str.isdigit`` ataylab
    ishlatilmaydi, chunki u ba'zi unicode raqam belgilarini (masalan, yuqori
    indeks) ham qabul qiladi.

    Args:
        code: tekshiriladigan kod.

    Returns:
        ``True`` — format yaroqli; aks holda ``False``.
    """
    if not isinstance(code, str):
        return False
    if len(code) != RESET_CODE_LENGTH:
        return False
    return all(ch in _ASCII_DIGITS for ch in code)


def compute_reset_code_expiry(
    issued_at: datetime,
    *,
    ttl_minutes: int = RESET_CODE_TTL_MINUTES,
) -> datetime:
    """Kod yuborilgan vaqtdan amal qilish muddatini hisoblaydi (R3.1).

    Args:
        issued_at: kod yuborilgan (yaratilgan) vaqt.
        ttl_minutes: amal qilish muddati daqiqalarda (standart — config 15 daqiqa).

    Returns:
        Kodning amal qilish tugash vaqti (``issued_at + ttl_minutes``).
    """
    return issued_at + timedelta(minutes=ttl_minutes)


def is_reset_code_expired(expires_at: datetime, now: datetime) -> bool:
    """Tasdiqlash kodi muddati o'tganligini aniqlaydi (R3.1, R3.4).

    Kod yuborilganidan keyin 15 daqiqa amal qiladi; R3.4 ga ko'ra faqat
    **15 daqiqadan ko'p** vaqt o'tganda kod muddati o'tgan hisoblanadi. Shu
    sababli aynan ``expires_at`` vaqtida kod hali yaroqli (chegara qo'shilgan),
    va u qat'iy ``now > expires_at`` bo'lganda muddati o'tgan deb belgilanadi.

    Args:
        expires_at: kodning amal qilish tugash vaqti
            (``compute_reset_code_expiry`` qarang).
        now: joriy vaqt.

    Returns:
        ``True`` — kod muddati o'tgan (``now > expires_at``); aks holda ``False``.
    """
    now, expires_at = _coerce_comparable(now, expires_at)
    return now > expires_at


def is_new_password_acceptable(
    password: object,
    *,
    min_length: int = PASSWORD_MIN_LENGTH,
) -> bool:
    """Tiklashdagi yangi parol minimal uzunlik talabiga mosligini tekshiradi (R3.3, R3.6).

    R3.3/R3.6 ga ko'ra yangi parol kamida 8 belgidan iborat bo'lishi shart;
    8 belgidan kam parol rad etiladi.

    Args:
        password: tekshiriladigan yangi parol.
        min_length: minimal ruxsat etilgan uzunlik (standart — 8, R3.6).

    Returns:
        ``True`` — parol satr va uzunligi ``min_length`` dan kam emas; aks holda
        ``False``.
    """
    if not isinstance(password, str):
        return False
    return len(password) >= min_length


def register_failed_code_attempt(current_attempts: int) -> int:
    """Bitta kod uchun noto'g'ri urinishlar hisoblagichini oshiradi (R3.7).

    Args:
        current_attempts: joriy noto'g'ri urinishlar soni (>= 0).

    Returns:
        Bittaga oshirilgan hisoblagich.
    """
    return current_attempts + 1


def is_reset_code_invalidated(
    attempts: int,
    *,
    max_attempts: int = MAX_RESET_CODE_ATTEMPTS,
) -> bool:
    """Kod noto'g'ri urinishlar soni tufayli bekor qilinganligini aniqlaydi (R3.7).

    R3.7: bitta tasdiqlash kodi uchun noto'g'ri kod **5 martadan ko'p** kiritilsa,
    kod bekor qilinadi. Demak ``attempts`` ``max_attempts`` dan oshganda
    (``attempts > max_attempts``) kod bekor hisoblanadi.

    Args:
        attempts: shu kodga nisbatan noto'g'ri urinishlar soni.
        max_attempts: ruxsat etilgan maksimal noto'g'ri urinishlar (standart 5).

    Returns:
        ``True`` — kod bekor qilingan; aks holda ``False``.
    """
    return attempts > max_attempts


def check_reset_code(
    *,
    entered_code: object,
    expected_code: str,
    expires_at: datetime,
    now: datetime,
    attempts: int = 0,
    consumed: bool = False,
    max_attempts: int = MAX_RESET_CODE_ATTEMPTS,
) -> ResetCodeCheck:
    """Tasdiqlash kodini sof tekshiruvchi o'tish (transition) funksiyasi (R3.4, R3.5, R3.7).

    Tekshiruv quyidagi ustuvor tartibda amalga oshiriladi (har biri kodni rad
    etishga olib keladi, lekin chaqiruvchiga aniq sababni qaytaradi):

    1. **Ishlatilgan** (``consumed``) — kod allaqachon parolni yangilashda
       ishlatilgan (R3.3); rad etiladi, ``invalidated=True``.
    2. **Urinishlar oshib ketgan** (``attempts > max_attempts``) — kod oldingi
       noto'g'ri urinishlar tufayli bekor qilingan (R3.7).
    3. **Muddati o'tgan** (``now > expires_at``) — vaqt asosida bekor (R3.1,
       R3.4); ``invalidated=True``. Bu urinish noto'g'ri urinish sifatida
       sanalmaydi (hisoblagich oshmaydi).
    4. **Noto'g'ri format** — 6 raqamli bo'lmagan kod (R3.5); noto'g'ri urinish
       sifatida sanaladi (hisoblagich oshadi).
    5. **Mos kelmaslik** — format to'g'ri, lekin kutilgan kodga teng emas
       (R3.5); noto'g'ri urinish sifatida sanaladi.
    6. Aks holda kod **yaroqli** (``VALID``).

    4 va 5-holatlarda yangi hisoblagich ``max_attempts`` dan oshsa, kod shu
    tekshiruvdan keyin bekor qilinadi (``invalidated=True``, R3.7).

    Args:
        entered_code: foydalanuvchi kiritgan kod (har qanday tur — format
            tekshiriladi).
        expected_code: kutilgan kod qiymati. Chaqiruvchi ochiq-matn yoki
            xeshlangan qiymatlarni izchil tarzda uzatishi mumkin.
        expires_at: kodning amal qilish tugash vaqti.
        now: joriy vaqt.
        attempts: shu kodga nisbatan oldingi noto'g'ri urinishlar soni.
        consumed: kod allaqachon ishlatilganligi.
        max_attempts: ruxsat etilgan maksimal noto'g'ri urinishlar (standart 5).

    Returns:
        ``ResetCodeCheck`` — natija statusi, yangilangan urinishlar soni va
        kod bekor qilinishi kerakligi.
    """
    if consumed:
        return ResetCodeCheck(
            status=ResetCodeStatus.CONSUMED,
            attempts=attempts,
            invalidated=True,
        )

    if is_reset_code_invalidated(attempts, max_attempts=max_attempts):
        return ResetCodeCheck(
            status=ResetCodeStatus.TOO_MANY_ATTEMPTS,
            attempts=attempts,
            invalidated=True,
        )

    if is_reset_code_expired(expires_at, now):
        return ResetCodeCheck(
            status=ResetCodeStatus.EXPIRED,
            attempts=attempts,
            invalidated=True,
        )

    if not is_reset_code_format_valid(entered_code):
        new_attempts = register_failed_code_attempt(attempts)
        return ResetCodeCheck(
            status=ResetCodeStatus.INVALID_FORMAT,
            attempts=new_attempts,
            invalidated=is_reset_code_invalidated(new_attempts, max_attempts=max_attempts),
        )

    if entered_code != expected_code:
        new_attempts = register_failed_code_attempt(attempts)
        return ResetCodeCheck(
            status=ResetCodeStatus.MISMATCH,
            attempts=new_attempts,
            invalidated=is_reset_code_invalidated(new_attempts, max_attempts=max_attempts),
        )

    return ResetCodeCheck(
        status=ResetCodeStatus.VALID,
        attempts=attempts,
        invalidated=False,
    )


__all__ = [
    # Login bloklash (R2.7)
    "MAX_FAILED_LOGIN_ATTEMPTS",
    "LOGIN_LOCKOUT_MINUTES",
    "LockoutState",
    "register_failed_attempt",
    "is_locked",
    "reset_after_success",
    # Parolni tiklash kodi (R3.1, R3.4, R3.5, R3.6, R3.7)
    "RESET_CODE_LENGTH",
    "RESET_CODE_TTL_MINUTES",
    "MAX_RESET_CODE_ATTEMPTS",
    "ResetCodeStatus",
    "ResetCodeCheck",
    "is_reset_code_format_valid",
    "compute_reset_code_expiry",
    "is_reset_code_expired",
    "is_new_password_acceptable",
    "register_failed_code_attempt",
    "is_reset_code_invalidated",
    "check_reset_code",
]
