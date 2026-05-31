"""Autentifikatsiya_Moduli — AuthService (R1, R2, R3, R17.1, R17.2).

Ushbu servis ro'yxatdan o'tish, kirish (login), token yangilash, logout va
parolni tiklash oqimlarini biznes-mantiq darajasida birlashtiradi. U sof domen
yordamchilari (``app.domain.auth_validation``, ``app.domain.auth_lockout``),
kripto yordamchilari (``app.core.security``, ``app.core.tokens``) va repository
qatlami (``app.repositories``) ustida ishlaydi — ya'ni o'zi validatsiya, xeshlash
yoki token kripto mantig'ini qayta yozmaydi, balki ularni ulaydi.

Servis **framework'dan mustaqil**: FastAPI/HTTP haqida hech narsa bilmaydi va
xatoliklarni ``app.services.errors`` dagi semantik istisnolar bilan bildiradi
(router keyinchalik ularni HTTP holatlariga keltiradi).

Bog'liq talablar (design.md — "Autentifikatsiya_Moduli"):
- R1.1–R1.7: ro'yxatdan o'tish validatsiyasi, takroriy telefon, parol xeshlash.
- R2.1, R2.2, R2.3, R2.4, R2.6, R2.7: login (oshkor qilmaydigan xato), token
  yangilash, logout, login bloklash.
- R3.1, R3.2, R3.3, R3.4, R3.5, R3.6, R3.7: parolni tiklash (mavjudlikni oshkor
  qilmaydigan umumiy javob, kod formati/muddati/urinishlari, parol yangilash).

Tranzaksiya boshqaruvi: holatni o'zgartiruvchi har bir amal servis ichida
``commit`` qilinadi. Bu, ayniqsa, login bloklash hisoblagichi uchun muhim
(R2.7): muvaffaqiyatsiz urinish hisoblagichi xato ko'tarilishidan **oldin**
saqlanadi, shunda tashqi tranzaksiya rollback qilsa ham bloklash hisobi
yo'qolmaydi.
"""

from __future__ import annotations

import hmac
import secrets
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.core.tokens import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    ExpiredTokenError,
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    extract_expiry,
    extract_jti,
    extract_subject,
    hash_token,
)
from app.domain.auth_lockout import (
    check_reset_code,
    compute_reset_code_expiry,
    is_locked,
    is_new_password_acceptable,
    is_reset_code_format_valid,
    register_failed_attempt,
)
from app.domain.auth_validation import (
    validate_password,
    validate_phone,
    validate_required,
    validate_role,
)
from app.models.user import User
from app.repositories import RoleRepository, TokenRepository, UserRepository
from app.services.errors import (
    AuthError,
    ConflictError,
    NotFoundError,
    ValidationError,
)

# To'liq ism uchun maksimal uzunlik (R1.1 — 1–200 belgi). DB ustuni String(200)
# bo'lgani uchun bu yerda toza validatsiya xatosi beriladi (DB xatosidan oldin).
_FULL_NAME_MAX_LENGTH = 200

# Login va parolni tiklash uchun **umumiy** (oshkor qilmaydigan) xabarlar
# (R2.2, R3.2, R3.4). Qaysi maydon xato ekani yoki hisob mavjudligi bildirilmaydi.
_GENERIC_LOGIN_ERROR = "Telefon raqami yoki parol noto'g'ri"
_ACCOUNT_LOCKED_ERROR = (
    "Hisob ketma-ket noto'g'ri urinishlar tufayli vaqtincha bloklangan. "
    "Iltimos, keyinroq qayta urinib ko'ring"
)
_GENERIC_RESET_REQUEST_MESSAGE = (
    "Agar ushbu telefon raqami ro'yxatdan o'tgan bo'lsa, "
    "tasdiqlash kodi yuborildi"
)
_INVALID_RESET_CODE_ERROR = "Tasdiqlash kodi yaroqsiz yoki muddati o'tgan"

# ``check_reset_code`` kutilgan kod bilan **aniq tenglik** asosida ishlaydi va
# kiritilgan kod 6 raqamli formatda bo'lishini talab qiladi. Kod DB'da
# **xeshlangan** holda saqlangani uchun tenglik xesh ustida (konstanta-vaqtli)
# tekshiriladi; kutilgan qiymat sifatida esa quyidagilardan biri uzatiladi:
#   - kod to'g'ri (xesh mos) bo'lsa — kiritilgan xom kodning o'zi (tenglik VALID);
#   - aks holda — kiritilgan xom kodga hech qachon teng bo'lmaydigan sentinel
#     (format to'g'ri bo'lsa MISMATCH, urinish hisoblanadi).
# Format/muddat/urinishlar/ishlatilganlik tekshiruvi to'liq ``check_reset_code``
# zimmasida qoladi (R3.4, R3.5, R3.7).
_NON_MATCHING_SENTINEL = "\x00\x00not-a-code\x00\x00"


def _field(payload: Mapping[str, Any] | Any, key: str) -> Any:
    """``payload`` dan maydon qiymatini oladi (Mapping yoki obyekt atributi).

    Router Pydantic modelini ``dict`` ga aylantirib uzatishi mumkin, ammo
    servis obyekt atributli payloadni ham qabul qiladi.
    """
    if isinstance(payload, Mapping):
        return payload.get(key)
    return getattr(payload, key, None)


class AuthService:
    """Autentifikatsiya biznes-mantiq servisi (R1, R2, R3).

    Args:
        session: faol SQLAlchemy ``Session``. Servis o'z yozuvlarini ushbu
            sessiyada ``commit`` qiladi.
        now_provider: joriy UTC vaqtni qaytaruvchi funksiya (deterministik
            testlar uchun in'ektsiya qilinadi). ``None`` bo'lsa
            ``datetime.now(timezone.utc)``.
        code_generator: 6 raqamli parolni tiklash kodini yaratuvchi funksiya
            (testlar uchun in'ektsiya qilinadi). ``None`` bo'lsa kriptografik
            tasodifiy 6 raqamli kod.
    """

    def __init__(
        self,
        session: Session,
        *,
        now_provider: Callable[[], datetime] | None = None,
        code_generator: Callable[[], str] | None = None,
    ) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.tokens = TokenRepository(session)
        self._now_provider = now_provider or self._default_now
        self._code_generator = code_generator or self._default_reset_code

    # ------------------------------------------------------------------
    # Yordamchilar
    # ------------------------------------------------------------------

    @staticmethod
    def _default_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _default_reset_code() -> str:
        """Kriptografik tasodifiy 6 raqamli tasdiqlash kodi (R3.1)."""
        return f"{secrets.randbelow(1_000_000):06d}"

    def _now(self) -> datetime:
        return self._now_provider()

    # ------------------------------------------------------------------
    # R1 — Ro'yxatdan o'tish
    # ------------------------------------------------------------------

    def register(self, payload: Mapping[str, Any] | Any) -> User:
        """Yangi hisob yaratadi (R1.1–R1.7).

        Validatsiya tartibi: majburiy maydonlar (R1.3) -> telefon formati (R1.6)
        -> parol uzunligi (R1.5) -> rol whitelisti (R1.7) -> takroriy telefon
        (R1.2). Muvaffaqiyatda parol xeshlanadi (R1.4) va foydalanuvchi
        saqlanadi (R1.1).

        Args:
            payload: ``phone``, ``password``, ``full_name``, ``role`` (majburiy)
                hamda ixtiyoriy profil maydonlari (``organization_id``,
                ``region_id``, ``position``, ``experience_years``,
                ``education_level``, ``qualification_courses``, ``certificates``,
                ``org_type``).

        Returns:
            Yaratilgan ``User``.

        Raises:
            ValidationError: majburiy maydon yo'q yoki maydon yaroqsiz (R1.3,
                R1.5, R1.6, R1.7).
            ConflictError: telefon raqami allaqachon ro'yxatdan o'tgan (R1.2).
        """
        phone = _field(payload, "phone")
        password = _field(payload, "password")
        full_name = _field(payload, "full_name")
        role = _field(payload, "role")

        # R1.3 — majburiy maydonlar (bo'sh/whitespace rad etiladi).
        if not validate_required(phone):
            raise ValidationError("Telefon raqami majburiy", field="phone")
        if not validate_required(password):
            raise ValidationError("Parol majburiy", field="password")
        if not validate_required(full_name):
            raise ValidationError("To'liq ism majburiy", field="full_name")
        if not validate_required(role):
            raise ValidationError("Rol majburiy", field="role")

        # R1.6 — telefon formati (+998, jami 13 belgi).
        if not validate_phone(phone):
            raise ValidationError(
                "Telefon raqami formati noto'g'ri (+998 bilan boshlanib, 13 belgi)",
                field="phone",
            )
        # R1.5 — parol uzunligi 8–64.
        if not validate_password(password):
            raise ValidationError(
                "Parol uzunligi 8–64 belgi oralig'ida bo'lishi kerak",
                field="password",
            )
        # R1.7 — rol whitelisti.
        if not validate_role(role):
            raise ValidationError(
                "Rol yaroqsiz (Rahbar, Ekspert yoki Administrator)",
                field="role",
            )
        # R1.1 — to'liq ism 1–200 belgi.
        if len(full_name) > _FULL_NAME_MAX_LENGTH:
            raise ValidationError(
                "To'liq ism 200 belgidan oshmasligi kerak",
                field="full_name",
            )

        # R1.2 — takroriy telefon.
        if self.users.phone_exists(phone):
            raise ConflictError(
                "Bu telefon raqami allaqachon ro'yxatdan o'tgan",
                field="phone",
                code="phone_already_registered",
            )

        role_row = self.roles.get_by_name(role)
        if role_row is None:
            # Rol whitelistdan o'tdi, ammo ma'lumotnomada (seed) topilmadi.
            raise ValidationError(
                "Rol tizimda sozlanmagan",
                field="role",
                code="role_not_configured",
            )

        # R1.4 — parolni xeshlab saqlash.
        password_hash = hash_password(password)

        user = self.users.create(
            full_name=full_name,
            phone=phone,
            password_hash=password_hash,
            role_id=role_row.id,
            organization_id=_field(payload, "organization_id"),
            region_id=_field(payload, "region_id"),
            position=_field(payload, "position"),
            experience_years=_field(payload, "experience_years"),
            education_level=_field(payload, "education_level"),
            qualification_courses=_field(payload, "qualification_courses"),
            certificates=_field(payload, "certificates"),
            org_type=_field(payload, "org_type"),
        )
        self.session.commit()
        return user

    # ------------------------------------------------------------------
    # R2 — Kirish (login) va token boshqaruvi
    # ------------------------------------------------------------------

    def login(self, phone: str, password: str) -> dict[str, Any]:
        """Telefon va parol bilan kirish; token juftligini qaytaradi (R2.1).

        - Muvaffaqiyatda: 15 daqiqalik access va 30 kunlik refresh token
          chiqariladi, refresh xeshi saqlanadi, bloklash hisobi nolga tushadi
          (R2.1, R2.7).
        - Muvaffaqiyatsizlikda: noto'g'ri urinish hisoblanadi va 5 urinishdan
          keyin hisob 15 daqiqaga bloklanadi (R2.7). Xato xabari qaysi maydon
          (telefon yoki parol) noto'g'ri ekanini oshkor qilmaydi (R2.2).
        - Hisob hozir bloklangan bo'lsa, kirish rad etiladi (R2.7).

        Args:
            phone: telefon raqami (hisob identifikatori).
            password: ochiq parol.

        Returns:
            ``{access_token, refresh_token, token_type, expires_in}``.

        Raises:
            AuthError: ma'lumot noto'g'ri yoki hisob bloklangan (R2.2, R2.7).
        """
        now = self._now()
        user = self.users.get_by_phone(phone) if isinstance(phone, str) else None

        # Mavjud bo'lmagan hisob — mavjudlikni oshkor qilmaslik uchun bir xil
        # umumiy xato (R2.2). Bloklash hisobi faqat mavjud hisob uchun yuritiladi.
        if user is None:
            raise AuthError(_GENERIC_LOGIN_ERROR, code="invalid_credentials")

        # R2.7 — hozir bloklangan bo'lsa, parolni tekshirmasdan rad etiladi.
        if is_locked(user.locked_until, now):
            raise AuthError(_ACCOUNT_LOCKED_ERROR, code="account_locked")

        if not verify_password(password, user.password_hash):
            # R2.7 — noto'g'ri urinishni hisobga olish; chegaraga yetganda blok.
            state = register_failed_attempt(user.failed_login_count or 0, now)
            if state.locked_until is not None:
                self.users.set_lockout(
                    user,
                    locked_until=state.locked_until,
                    failed_login_count=state.failed_count,
                )
            else:
                self.users.increment_failed_login(user)
            # Hisoblagichni xato ko'tarilishidan OLDIN saqlash (R2.7).
            self.session.commit()
            raise AuthError(_GENERIC_LOGIN_ERROR, code="invalid_credentials")

        # Muvaffaqiyat — bloklash hisobini nolga tushirish (R2.7).
        role_name = user.role.name
        self.users.reset_lockout(user)
        tokens = self._issue_token_pair(user_id=user.id, role=role_name, now=now)
        self.session.commit()
        return tokens

    def refresh(self, refresh_token: str) -> dict[str, Any]:
        """Yaroqli refresh token asosida yangi access token chiqaradi (R2.3, R2.6).

        Token imzosi/muddati/turi tekshiriladi, so'ng DB'dagi refresh xeshi
        mavjud va bekor qilinmaganligi tekshiriladi. Aks holda qaytadan kirishni
        talab qiluvchi xato qaytariladi (R2.6).

        Args:
            refresh_token: mijozdagi xom refresh token.

        Returns:
            ``{access_token, token_type, expires_in}``.

        Raises:
            AuthError: token yaroqsiz, muddati o'tgan yoki bekor qilingan (R2.6).
        """
        now = self._now()
        try:
            claims = decode_token(refresh_token, expected_type=REFRESH_TOKEN_TYPE)
        except (ExpiredTokenError, InvalidTokenError) as exc:
            raise AuthError(
                "Yangilash tokeni yaroqsiz yoki muddati o'tgan. Qaytadan kiring",
                code="invalid_refresh_token",
            ) from exc

        stored = self.tokens.get_refresh_by_hash(hash_token(refresh_token))
        if stored is None or stored.revoked:
            raise AuthError(
                "Yangilash tokeni bekor qilingan. Qaytadan kiring",
                code="invalid_refresh_token",
            )

        user = self.users.get_by_id(int(extract_subject(claims)))
        if user is None:
            raise AuthError(
                "Yangilash tokeni yaroqsiz. Qaytadan kiring",
                code="invalid_refresh_token",
            )

        access = create_access_token(
            user_id=user.id, role=user.role.name, now=now
        )
        return {
            "access_token": access.token,
            "token_type": "bearer",
            "expires_in": int((access.expires_at - now).total_seconds()),
        }

    def logout(
        self, access_token: str, refresh_token: str | None = None
    ) -> None:
        """Joriy tokenlarni bekor qiladi (R2.4).

        Access token ``jti`` si qora ro'yxatga qo'shiladi va (berilgan bo'lsa)
        refresh token bekor qilinadi. Amal idempotent va bardoshli: yaroqsiz
        access token bo'lsa ham refresh tokenni bekor qilishga harakat qiladi.

        Args:
            access_token: bekor qilinadigan access token.
            refresh_token: (ixtiyoriy) bekor qilinadigan refresh token.
        """
        # Access token jti'sini blacklistga qo'shish (muddat tekshirilmaydi —
        # logout muddati yaqin tokenni ham bekor qila olishi kerak).
        try:
            claims = decode_token(
                access_token, expected_type=ACCESS_TOKEN_TYPE, verify_exp=False
            )
            self.tokens.blacklist_jti(extract_jti(claims), extract_expiry(claims))
        except (ExpiredTokenError, InvalidTokenError):
            # Access token yaroqsiz — baribir refresh tokenni bekor qilishga o'tamiz.
            pass

        if refresh_token:
            stored = self.tokens.get_refresh_by_hash(hash_token(refresh_token))
            if stored is not None and not stored.revoked:
                self.tokens.revoke_refresh(stored)

        self.session.commit()

    # ------------------------------------------------------------------
    # R3 — Parolni tiklash
    # ------------------------------------------------------------------

    def request_password_reset(self, phone: str) -> dict[str, str]:
        """Parolni tiklashni boshlaydi; har doim umumiy javob qaytaradi (R3.1, R3.2).

        Hisob mavjud bo'lsa, 6 raqamli kod yaratiladi, **xeshlangan** holda
        15 daqiqalik amal muddati bilan saqlanadi (R3.1). Hisob mavjud bo'lmasa
        ham, javob aynan bir xil bo'ladi va hisob mavjudligini oshkor qilmaydi
        (R3.2).

        Args:
            phone: parolni tiklash so'ralgan telefon raqami.

        Returns:
            Umumiy muvaffaqiyat xabari (mavjudlikdan qat'i nazar bir xil).
        """
        generic_response = {"message": _GENERIC_RESET_REQUEST_MESSAGE}
        now = self._now()

        user = self.users.get_by_phone(phone) if isinstance(phone, str) else None
        if user is None:
            # R3.2 — mavjud bo'lmagan raqam uchun ham bir xil javob.
            return generic_response

        code = self._code_generator()
        # Kod DB'da xeshlangan (deterministik) holda saqlanadi — xom kod emas.
        self.tokens.create_reset_code(
            user_id=user.id,
            code_hash=hash_token(code),
            expires_at=compute_reset_code_expiry(now),
        )
        self.session.commit()
        # Eslatma: xom kod foydalanuvchiga tashqi kanal (SMS) orqali yetkaziladi
        # — bu servis doirasidan tashqarida. Kod javobda hech qachon oshkor
        # qilinmaydi (R3.2).
        return generic_response

    def confirm_password_reset(
        self, phone: str, code: str, new_password: str
    ) -> dict[str, str]:
        """Tasdiqlash kodi bilan parolni yangilaydi (R3.3–R3.7).

        ``check_reset_code`` orqali format (R3.5), amal muddati (R3.4) va
        urinishlar (R3.7) tekshiriladi; yangi parol uzunligi >= 8 talab qilinadi
        (R3.6). Muvaffaqiyatda parol xeshlanib yangilanadi, kod bekor (consumed)
        qilinadi (R3.3) va foydalanuvchining barcha refresh tokenlari bekor
        qilinadi (xavfsizlik).

        Args:
            phone: hisob telefon raqami.
            code: foydalanuvchi kiritgan 6 raqamli tasdiqlash kodi.
            new_password: yangi ochiq parol (>= 8 belgi).

        Returns:
            Muvaffaqiyat xabari.

        Raises:
            ValidationError: kod yaroqsiz/muddati o'tgan/urinishlar oshib ketgan
                yoki yangi parol talabga javob bermaydi (R3.4, R3.5, R3.6, R3.7).
        """
        now = self._now()

        # R3.6 — yangi parol kamida 8 belgidan iborat bo'lishi kerak.
        if not is_new_password_acceptable(new_password):
            raise ValidationError(
                "Yangi parol kamida 8 belgidan iborat bo'lishi kerak",
                field="new_password",
                code="weak_password",
            )

        user = self.users.get_by_phone(phone) if isinstance(phone, str) else None
        reset = self.tokens.get_active_reset_code(user.id) if user else None
        if user is None or reset is None:
            raise ValidationError(
                _INVALID_RESET_CODE_ERROR,
                field="code",
                code="invalid_reset_code",
            )

        # Kod xeshlangan saqlanadi; tenglik xesh ustida konstanta-vaqtli
        # tekshiriladi. ``check_reset_code`` format/muddat/urinish mantig'ini
        # bajaradi (R3.4, R3.5, R3.7).
        code_matches = is_reset_code_format_valid(code) and hmac.compare_digest(
            hash_token(code), reset.code_hash
        )
        expected_for_check = code if code_matches else _NON_MATCHING_SENTINEL

        check = check_reset_code(
            entered_code=code,
            expected_code=expected_for_check,
            expires_at=reset.expires_at,
            now=now,
            attempts=reset.attempts or 0,
            consumed=reset.consumed,
        )

        if not check.is_valid:
            # Urinishlar hisobini saqlash; kerak bo'lsa kodni bekor qilish (R3.7).
            reset.attempts = check.attempts
            if check.invalidated:
                self.tokens.consume_reset_code(reset)
            else:
                self.session.flush()
            self.session.commit()
            raise ValidationError(
                _INVALID_RESET_CODE_ERROR,
                field="code",
                code="invalid_reset_code",
            )

        # R3.3 — parolni xeshlab yangilash va kodni bir martalik qilib bekor qilish.
        user.password_hash = hash_password(new_password)
        self.session.flush()
        self.tokens.consume_reset_code(reset)
        # Xavfsizlik: parol o'zgargach barcha faol refresh tokenlar bekor qilinadi.
        self.tokens.revoke_all_for_user(user.id)
        self.session.commit()
        return {"message": "Parol muvaffaqiyatli yangilandi"}

    # ------------------------------------------------------------------
    # Ichki yordamchilar
    # ------------------------------------------------------------------

    def _issue_token_pair(
        self, *, user_id: int, role: str, now: datetime
    ) -> dict[str, Any]:
        """Access + refresh juftligini chiqaradi va refresh xeshini saqlaydi (R2.1)."""
        access = create_access_token(user_id=user_id, role=role, now=now)
        refresh = create_refresh_token(user_id=user_id, now=now)
        self.tokens.store_refresh(
            user_id=user_id,
            token_hash=hash_token(refresh.token),
            expires_at=refresh.expires_at,
        )
        return {
            "access_token": access.token,
            "refresh_token": refresh.token,
            "token_type": "bearer",
            "expires_in": int((access.expires_at - now).total_seconds()),
        }


__all__ = ["AuthService"]
