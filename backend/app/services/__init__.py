"""Servis qatlami — biznes-mantiq modullari (Auth, Profil, Diagnostika, ...).

Servislar sof domen mantig'ini (``app.domain``), kripto yordamchilarini
(``app.core``) va repository qatlamini (``app.repositories``) ulaydi. Ular
framework'dan mustaqil bo'lib, xatoliklarni ``app.services.errors`` dagi
semantik istisnolar orqali bildiradi (router keyinchalik HTTP holatlariga
keltiradi).

Eksport:
- ``AuthService`` — Autentifikatsiya_Moduli (R1, R2, R3).
- Xatoliklar: ``ServiceError``, ``ValidationError``, ``AuthError``,
  ``NotFoundError``, ``ConflictError``.
"""

from __future__ import annotations

from app.services.auth_service import AuthService
from app.services.errors import (
    AuthError,
    ConflictError,
    NotFoundError,
    ServiceError,
    ValidationError,
)

__all__ = [
    "AuthService",
    "ServiceError",
    "ValidationError",
    "AuthError",
    "NotFoundError",
    "ConflictError",
]
