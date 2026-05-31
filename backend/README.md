# MTT Menejer Diagnostika — Backend

Maktabgacha ta'lim tashkiloti (MTT) rahbarlarini diagnostika qilish tizimining
backend xizmati. Texnologik stek: **FastAPI (Python 3.11+)**, **SQLAlchemy 2.x +
Alembic**, **PostgreSQL 15+**, **JWT (PyJWT) + bcrypt/argon2**.

> Bu — 1.1-vazifa doirasida yaratilgan loyiha skeletoni. Domen mantig'i,
> modellar, migratsiyalar va servislar keyingi vazifalarda qo'shiladi.

## Loyiha tuzilmasi

```
backend/
├── app/
│   ├── api/            # REST_API routerlari + middleware (OpenAPI)
│   ├── services/       # Biznes-mantiq modullari
│   ├── domain/         # Sof funksiyalar (scoring, rating, analytics)
│   ├── repositories/   # Ma'lumotlarga kirish (ORM ustida)
│   ├── models/         # SQLAlchemy ORM modellari
│   ├── core/           # Konfiguratsiya, xavfsizlik
│   └── main.py         # FastAPI ilova instansi + health-check
├── tests/              # pytest + Hypothesis (>=100 iteratsiya)
├── requirements.txt
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml  # backend + PostgreSQL 15
```

## Lokal ishga tushirish (virtualenv)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- Salomatlik tekshiruvi: <http://localhost:8000/health>
- OpenAPI hujjatlari (R20.5): <http://localhost:8000/docs>
- OpenAPI sxemasi: <http://localhost:8000/openapi.json>

## Docker orqali ishga tushirish

```bash
cp .env.example .env   # qiymatlarni to'ldiring
docker compose up --build
```

Bu backend (8000-port) va PostgreSQL 15 (5432-port) xizmatlarini ishga tushiradi.

## Testlar

```bash
pip install -r requirements.txt
pytest                       # standart "dev" Hypothesis profili (>=100 iteratsiya)
HYPOTHESIS_PROFILE=thorough pytest
```

Hypothesis profillari `tests/conftest.py` da ro'yxatdan o'tkazilgan va har bir
property-based test kamida **100 iteratsiya** bilan ishlaydi.

## Konfiguratsiya

Barcha sozlamalar muhit o'zgaruvchilaridan (yoki `.env`) o'qiladi — qarang
`app/core/config.py` va `.env.example`. Maxfiy qiymatlar (`JWT_SECRET_KEY`,
`DATABASE_URL`) kodga yozilmaydi.
