# MTT Menejer Diagnostika — Backend (FastAPI) konteyner tasviri
FROM python:3.11-slim AS base

# Python xulq-atvori: .pyc fayllarsiz, buferlanmagan stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Tizim bog'liqliklari (psycopg/bcrypt build uchun minimal to'plam)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Bog'liqliklarni alohida qatlamda o'rnatamiz (kesh uchun)
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Ilova kodi
COPY . .

# Konteyner ichidagi xizmat porti
EXPOSE 8000

# Uvicorn orqali ishga tushirish
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
