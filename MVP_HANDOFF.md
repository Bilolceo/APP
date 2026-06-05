# MTT Menejer Diagnostika — MVP Handoff

Ushbu hujjat MVP'ni ishga tushirish, demo login bilan sinash va APK'ni
foydalanuvchiga berish uchun qisqa yo'riqnoma.

## Holat

- Backend: FastAPI + PostgreSQL Docker orqali ishlaydi.
- Mobile: Flutter Android debug APK build qilingan.
- Demo data: role, kompetensiyalar, tavsiyalar, demo user va faol demo test
  Alembic migration orqali seed qilinadi.
- Tarmoq: real telefon uchun API manzil `http://172.16.240.124:8010`.

## Demo Login

```text
Telefon: +998901112236
Parol: secret123
```

## Backendni Ishga Tushirish

```bash
cd backend
docker compose up -d --build
docker compose exec -T backend alembic upgrade head
```

Tekshirish:

```bash
curl http://172.16.240.124:8010/health
```

Kutilgan javob:

```json
{"status":"ok","service":"MTT Menejer Diagnostika API"}
```

## APK

Yangi APK:

```text
mobile/build/app/outputs/flutter-apk/app-debug.apk
```

Build komandasi:

```bash
cd mobile
flutter build apk --debug --dart-define=API_BASE_URL=http://172.16.240.124:8010
```

Telefonda eski APK bo'lsa avval uninstall qiling, keyin yangi APK'ni o'rnating.
Telefon va Mac bir Wi-Fi tarmog'ida bo'lishi kerak.

## MVP Smoke Checklist

- Login ishlaydi.
- Register muvaffaqiyatdan keyin Home'ga o'tadi.
- Home bo'limlari ochiladi.
- Diagnostika testlari ro'yxatida `MVP diagnostika demo testi` chiqadi.
- Test tafsilotida 6 ta savol bor.
- Test topshirilgandan keyin natija yaratiladi.
- Mening natijalarim bo'limida natija ko'rinadi.
- Analitika natijadan keyin grafik/progress ma'lumotlarini ko'rsatadi.
- Logout foydalanuvchini login ekraniga qaytaradi.

## Oxirgi Tekshiruv

2026-06-05 kuni quyidagilar tekshirildi:

- `GET /health` ishladi.
- Demo login ishladi.
- `GET /tests` 1 ta faol demo test qaytardi.
- `GET /tests/{id}` 6 ta savol qaytardi.
- `POST /tests/{id}/start` sessiya yaratdi.
- `POST /tests/{id}/submit` natija yaratdi.
- `GET /tests/results/{id}` natija tafsilotini qaytardi.
- `GET /analytics/me` `has_results=true` qaytardi.

