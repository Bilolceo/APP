"""Pytest + Hypothesis umumiy konfiguratsiyasi.

Hypothesis profillari ro'yxatdan o'tkaziladi. Loyiha qoidasiga ko'ra har bir
property-based test kamida 100 iteratsiya bilan ishlashi shart (design.md —
"Property-based testing konfiguratsiyasi"). Shu sababli standart sifatida
`max_examples=100` bo'lgan profil yuklanadi.

Profilni muhit o'zgaruvchisi orqali tanlash mumkin:
    HYPOTHESIS_PROFILE=ci pytest      # tezroq CI uchun
    HYPOTHESIS_PROFILE=dev pytest     # standart, >=100 iteratsiya
    HYPOTHESIS_PROFILE=thorough pytest
"""

from __future__ import annotations

import os

from hypothesis import HealthCheck, settings

# --- "dev" profili: loyiha minimumi — kamida 100 iteratsiya ---
settings.register_profile(
    "dev",
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

# --- "ci" profili: CI uchun ham kamida 100 iteratsiya (talab minimumi) ---
settings.register_profile(
    "ci",
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

# --- "thorough" profili: chuqurroq tekshiruv uchun ---
settings.register_profile(
    "thorough",
    max_examples=500,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

# Tanlangan profilni yuklash (standart: dev — >=100 iteratsiya).
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))
