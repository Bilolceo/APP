# Implementation Plan: MTT Menejer Diagnostika

## Overview

_Umumiy ko'rinish_

Ushbu reja tasdiqlangan `requirements.md` va `design.md` hujjatlari asosida MVP
ni inkremental tarzda qurish bo'yicha kodlash vazifalarini belgilaydi. Tartib:
loyiha skeletoni va domen asoslari → ma'lumotlar bazasi modeli, migratsiyalar va
repository → sof domen mantig'i (ball hisoblash, reyting, analitika, tavsiya) va
ularning property-based testlari → servis qatlami → REST API routerlari hamda
middleware (auth/RBAC/rate-limit/logging) → Flutter mobil ilova qatlamlari →
yakuniy integratsiya va ulash.

**Texnologik stek:**
- Backend: FastAPI (Python 3.11+), SQLAlchemy 2.x + Alembic, PostgreSQL 15+,
  JWT (PyJWT) + bcrypt/argon2, Docker.
- Mobil: Flutter (Dart), Drift/SQLite (offline kesh), Dio (API), FCM (push).
- Property-based testing: Hypothesis (backend Python), fast_check yoki shunga
  o'xshash generativ kutubxona (mobil Dart).

**Property-based testlar bo'yicha qoidalar (design'ga muvofiq):**
- Har bir korrektlik xususiyati (Property 1–48) AYNAN bitta PBT bilan amalga
  oshiriladi.
- Har bir PBT kamida **100 iteratsiya** bilan ishlaydi.
- Har bir PBT quyidagi tag bilan belgilanadi:
  **Feature: mtt-menejer-diagnostika, Property {raqam}: {xususiyat matni}**
- Domen mantiqi (Baholash_Moduli/scoring, Reyting_Moduli/rating, ekspert
  o'rtacha, daraja aniqlash) sof funksiyalar bo'lib, ular PBT uchun asosiy
  nishon hisoblanadi.

## Tasks

- [ ] 1. Loyiha skeletoni va domen asoslari
  - [x] 1.1 Backend FastAPI loyiha skeletonini sozlash
    - `app/` paket tuzilmasi (api, services, domain, repositories, models, core),
      `pyproject.toml`/`requirements.txt` (fastapi, uvicorn, sqlalchemy, alembic,
      psycopg, pyjwt, passlib[bcrypt]/argon2, pydantic, pytest, hypothesis)
    - Konfiguratsiya (`core/config.py`, muhit o'zgaruvchilari), `Dockerfile` va
      `docker-compose.yml` (backend + PostgreSQL), pytest + Hypothesis profili
      (kamida 100 iteratsiya)
    - _Requirements: 20.5, 18.2_
  - [x] 1.2 Domen tiplari va abstraksiyalarni aniqlash
    - Sof domen dataclasslari: `AnsweredQuestion`, `ScoreInput`, `ScoreResult`,
      `CompetencyResult`, `RatingRecord`, `RankedEntry`; `Level` enum
      (Past/O'rta/Yaxshi/Yuqori)
    - `FileStorageBackend` abstrakt interfeysi (save/get/delete) — keyinchalik
      `LocalFileStorage` va `S3FileStorage` uchun
    - _Requirements: 8.4, 12.1, 18.2_

- [ ] 2. Ma'lumotlar bazasi modeli, migratsiyalar va repository
  - [x] 2.1 SQLAlchemy ORM modellarini yozish
    - Barcha jadvallar: users, roles, regions, organizations, competencies,
      tests, questions, answers, test_sessions, session_answers, test_results,
      competency_results, recommendations, result_recommendations, portfolios,
      files, expert_reviews, refresh_tokens, token_blacklist,
      password_reset_codes, device_tokens, feedbacks (kelajak uchun)
    - _Requirements: 1.1, 5.1, 6.1, 7.1, 8.6, 10.1, 11.1, 13.1, 16.1, 18.1_
  - [x] 2.2 Alembic migratsiyalari va cheklovlar
    - CHECK cheklovlari (experience_years 0..60, percentage 0..100,
      questions.score 0.01..1000, tests.duration 1..600, expert_reviews 1..5),
      `phone` UNIQUE, `test_results.session_id` UNIQUE, `test_sessions` uchun
      `UNIQUE (user_id, test_id) WHERE status='in_progress'`, FK referensial
      cheklovlar
    - _Requirements: 1.2, 5.3, 7.7, 7.10, 8.1, 13.1, 14.2, 14.3, 14.8_
  - [x] 2.3 Repository qatlamini yozish
    - ORM ustida repository klasslari (users, tests, questions, sessions,
      results, portfolio, expert_reviews, recommendations, tokens, devices) —
      servislar uchun ma'lumotlarga kirish nuqtasi
    - _Requirements: 8.6, 11.1, 12.1, 15.5_
  - [ ]* 2.4 DB va repository integratsion testlari
    - Migratsiyalarni qo'llash, referensial yaxlitlik cheklovlari, repository
      CRUD round-trip (sinov PostgreSQL'da)
    - _Requirements: 14.8, 8.6_

- [ ] 3. Baholash_Moduli domen yadrosi (sof funksiyalar)
  - [x] 3.1 Umumiy foiz va daraja sof funksiyalari
    - `compute_percentage(collected, max)` — `collected/max*100`, 2 kasr half-up,
      `max==0 -> 0.0`; `determine_level(percentage)` — uzluksiz oraliqlar
    - _Requirements: 8.1, 8.2, 8.8_
  - [ ]* 3.2 PBT — umumiy foiz chegaralari va nolga bo'lish
    - **Feature: mtt-menejer-diagnostika, Property 18: Umumiy foiz chegaralari va nolga bo'lish**
    - **Tekshiradi: Requirements 8.1, 8.8** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 3.3 PBT — daraja oraliqlari to'liq taqsimot tashkil qiladi
    - **Feature: mtt-menejer-diagnostika, Property 19: Daraja oraliqlari to'liq taqsimot tashkil qiladi**
    - **Tekshiradi: Requirements 8.2** — Hypothesis, kamida 100 iteratsiya
  - [x] 3.4 Kompetensiya foizlari va natija qurish
    - `compute_competency_scores(answered)` — kompetensiya bo'yicha foizlar,
      bog'lanmagan savollar chetda; `build_result(...)` — umumiy ball,
      kompetensiya ballari, kuchli/zaif tomonlar (teng qiymatda barchasi)
    - _Requirements: 8.3, 8.4, 8.5, 8.8_
  - [ ]* 3.5 PBT — kompetensiya foizi va bog'lanmagan savollar
    - **Feature: mtt-menejer-diagnostika, Property 20: Kompetensiya foizi va bog'lanmagan savollar**
    - **Tekshiradi: Requirements 8.3, 8.5, 8.8** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 3.6 PBT — kuchli va zaif kompetensiyalar
    - **Feature: mtt-menejer-diagnostika, Property 22: Kuchli va zaif kompetensiyalar (argmax/argmin teng qiymat bilan)**
    - **Tekshiradi: Requirements 8.4, 9.5, 9.6** — Hypothesis, kamida 100 iteratsiya

- [ ] 4. Reyting_Moduli domen yadrosi (sof funksiyalar)
  - [x] 4.1 Reyting saralash va o'rin berish
    - `compute_ranking(records)` — umumiy foiz bo'yicha kamayuvchi saralash,
      teng qiymatlarda bir xil rank va keyingi o'rinni o'tkazib yuborish, teng
      yozuvlarni sana bo'yicha o'suvchi tartiblash; permutatsiyaga deterministik
    - _Requirements: 12.1, 12.2, 12.3_
  - [ ]* 4.2 PBT — reytingning deterministik saralanishi va teng o'rinlar
    - **Feature: mtt-menejer-diagnostika, Property 33: Reytingning deterministik saralanishi va teng o'rinlar**
    - **Tekshiradi: Requirements 12.1, 12.2, 12.3** — Hypothesis, kamida 100 iteratsiya
  - [x] 4.3 Anonimlashtirish va natijasiz foydalanuvchini chiqarish
    - Reyting yozuvini faqat hudud, tashkilot turi, lavozim, ko'rsatkich va
      rankga qisqartirish; so'rovchining yozuvini belgilash; natijasi yo'q
      foydalanuvchini reytingdan chiqarish
    - _Requirements: 12.4, 12.5_
  - [ ]* 4.4 PBT — reyting anonimligi
    - **Feature: mtt-menejer-diagnostika, Property 34: Reyting anonimligi**
    - **Tekshiradi: Requirements 12.4** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 4.5 PBT — natijasi yo'q foydalanuvchi reytingdan tashqarida
    - **Feature: mtt-menejer-diagnostika, Property 35: Natijasi yo'q foydalanuvchi reytingdan tashqarida**
    - **Tekshiradi: Requirements 12.5** — Hypothesis, kamida 100 iteratsiya

- [ ] 5. Analitika va Hisobot domen yadrosi (sof agregatsiya funksiyalari)
  - [x] 5.1 O'sish dinamikasi va farq funksiyalari
    - `growth_dynamics(results)` — sana bo'yicha xronologik (o'suvchi) umumiy
      foizlar ketma-ketligi; `growth_diff(results)` — joriy vs bevosita oldingi
      farq va ishora; bitta natijada farq "mavjud emas"
    - _Requirements: 9.1, 9.3, 9.4, 15.5_
  - [ ]* 5.2 PBT — o'sish dinamikasi xronologik tartibi
    - **Feature: mtt-menejer-diagnostika, Property 23: O'sish dinamikasi xronologik tartibi**
    - **Tekshiradi: Requirements 9.1, 15.5** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 5.3 PBT — o'sish farqi hisoblanishi
    - **Feature: mtt-menejer-diagnostika, Property 24: O'sish farqi hisoblanishi**
    - **Tekshiradi: Requirements 9.3** — Hypothesis, kamida 100 iteratsiya
  - [x] 5.4 Jamlangan agregatsiya funksiyalari
    - `aggregate_average(results)` — umumiy foizlar arifmetik o'rtachasi (0–100,
      2 kasr); `aggregate_competencies(results)` — eng past/yuqori jamlangan
      kompetensiya(lar); `aggregate_by_section(records, key)` — hudud/tashkilot
      kesimida rahbarlar soni, topshirganlar soni, o'rtacha ball
    - _Requirements: 15.1, 15.2, 15.3, 15.4_
  - [ ]* 5.5 PBT — jamlangan o'rtacha ball chegaralari
    - **Feature: mtt-menejer-diagnostika, Property 25: Jamlangan o'rtacha ball chegaralari**
    - **Tekshiradi: Requirements 15.1** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 5.6 PBT — eng past va eng yuqori jamlangan kompetensiyalar
    - **Feature: mtt-menejer-diagnostika, Property 26: Eng past va eng yuqori jamlangan kompetensiyalar**
    - **Tekshiradi: Requirements 15.2** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 5.7 PBT — kesim bo'yicha hisobot jamlanmasi
    - **Feature: mtt-menejer-diagnostika, Property 27: Kesim bo'yicha hisobot jamlanmasi**
    - **Tekshiradi: Requirements 15.3, 15.4** — Hypothesis, kamida 100 iteratsiya

- [ ] 6. Ekspert va Tavsiya domen mantig'i (sof funksiyalar)
  - [x] 6.1 Ekspert o'rtacha bahosi va mezon validatsiyasi
    - `compute_expert_average(scores6)` — `yig'indi/6`, 1.00–5.00, 2 kasr;
      `validate_expert_scores(scores)` — har biri 1–5 butun va olti mezon to'liq
    - _Requirements: 13.1, 13.2, 13.3, 13.4_
  - [ ]* 6.2 PBT — ekspert o'rtacha bahosi
    - **Feature: mtt-menejer-diagnostika, Property 36: Ekspert o'rtacha bahosi**
    - **Tekshiradi: Requirements 13.2** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 6.3 PBT — ekspert baholash validatsiyasi
    - **Feature: mtt-menejer-diagnostika, Property 37: Ekspert baholash validatsiyasi**
    - **Tekshiradi: Requirements 13.1, 13.3, 13.4** — Hypothesis, kamida 100 iteratsiya
  - [x] 6.4 Tavsiya tanlash mantig'i
    - `select_recommendations(competency_results)` — har bir kompetensiya+daraja
      uchun tavsiya; aniq mos bo'lmasa umumiy standart tavsiya (har doim tavsiya)
    - _Requirements: 10.1, 10.4_
  - [ ]* 6.5 PBT — har bir kompetensiya+daraja uchun tavsiya tanlanadi
    - **Feature: mtt-menejer-diagnostika, Property 28: Har bir kompetensiya+daraja uchun tavsiya tanlanadi (totallik)**
    - **Tekshiradi: Requirements 10.1, 10.4** — Hypothesis, kamida 100 iteratsiya

- [x] 7. Checkpoint — domen yadrosi
  - Barcha domen testlari (Property 18–20, 22, 23–28, 33–37) o'tishiga ishonch
    hosil qiling, savol tug'ilsa foydalanuvchidan so'rang.

- [ ] 8. Autentifikatsiya domen yordamchi mantig'i va validatsiya
  - [x] 8.1 Kirish validatsiya va parol xeshlash yordamchilari
    - `validate_phone` (+998, 13 belgi), `validate_password` (8–64),
      `validate_role` (Rahbar/Ekspert/Administrator), `validate_required`
      (bo'sh/whitespace), `hash_password`/`verify_password` (bcrypt/argon2)
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6, 1.7, 17.1_
  - [ ]* 8.2 PBT — ro'yxatdan o'tish validatsiyasi yaroqsiz maydonni rad etadi
    - **Feature: mtt-menejer-diagnostika, Property 1: Ro'yxatdan o'tish validatsiyasi yaroqsiz maydonni rad etadi**
    - **Tekshiradi: Requirements 1.1, 1.3, 1.5, 1.6, 1.7** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 8.3 PBT — parol har doim xeshlangan holda saqlanadi
    - **Feature: mtt-menejer-diagnostika, Property 2: Parol har doim xeshlangan holda saqlanadi**
    - **Tekshiradi: Requirements 1.4, 17.1** — Hypothesis, kamida 100 iteratsiya
  - [x] 8.4 Login bloklash va reset-kod sof mantig'i
    - `register_failed_attempt`/`is_locked` (5 urinish -> 15 daqiqa blok,
      muvaffaqiyatda nolga tushish); reset kodni tekshirish: 6 raqam formati,
      15 daqiqa amal, 5 dan ortiq urinishda bekor qilish
    - _Requirements: 2.7, 3.1, 3.4, 3.5, 3.6, 3.7_
  - [ ]* 8.5 PBT — login bloklash chegarasi
    - **Feature: mtt-menejer-diagnostika, Property 3: Login bloklash chegarasi**
    - **Tekshiradi: Requirements 2.7** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 8.6 PBT — parolni tiklash kodi formati va amal qilish muddati
    - **Feature: mtt-menejer-diagnostika, Property 8: Parolni tiklash kodi formati va amal qilish muddati**
    - **Tekshiradi: Requirements 3.1, 3.4, 3.5** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 8.7 PBT — parolni tiklash muvaffaqiyatli yangilash va kod bir martaligi
    - **Feature: mtt-menejer-diagnostika, Property 9: Parolni tiklash — muvaffaqiyatli yangilash va kod bir martaligi**
    - **Tekshiradi: Requirements 3.3, 3.6, 3.7** — Hypothesis, kamida 100 iteratsiya

- [ ] 9. JWT token boshqaruvi va Autentifikatsiya_Moduli servisi
  - [x] 9.1 JWT token yordamchilarini yozish
    - Access token (15 daqiqa, sub/role/jti/exp) va refresh token (30 kun)
      yaratish/tekshirish (PyJWT); `token_blacklist` va `refresh_tokens`
      orqali bekor qilish/aylantirish mantig'i
    - _Requirements: 2.1, 2.3, 2.4, 2.5, 2.6, 17.2_
  - [ ]* 9.2 PBT — refresh tokenning yaroqliligi
    - **Feature: mtt-menejer-diagnostika, Property 4: Refresh tokenning yaroqliligi**
    - **Tekshiradi: Requirements 2.3, 2.6** — Hypothesis, kamida 100 iteratsiya
  - [x] 9.3 AuthService ni yozish
    - `register`, `login` (qaysi maydon xato ekanini oshkor qilmaslik),
      `refresh`, `logout`, `request_password_reset` (mavjudlikni oshkor
      qilmaydigan umumiy javob), `confirm_password_reset` — repository va domen
      mantig'idan foydalanib
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.4, 3.1, 3.2, 3.3_
  - [ ]* 9.4 PBT — noto'g'ri login ma'lumotni oshkor qilmaydi
    - **Feature: mtt-menejer-diagnostika, Property 7: Noto'g'ri login ma'lumotni oshkor qilmaydi**
    - **Tekshiradi: Requirements 2.2** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 9.5 PBT — parolni tiklash javobi hisob mavjudligini oshkor qilmaydi
    - **Feature: mtt-menejer-diagnostika, Property 10: Parolni tiklash javobi hisob mavjudligini oshkor qilmaydi**
    - **Tekshiradi: Requirements 3.2** — Hypothesis, kamida 100 iteratsiya

- [ ] 10. Profil va Diagnostika servislari
  - [x] 10.1 ProfileService ni yozish
    - `get_profile` (to'liq maydonlar); `update_profile` — tahrirlanadigan
      maydonlar, ish staji 0–60 butun va matn ≤200 validatsiyasi, telefon
      o'zgartirishni rad etish
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  - [ ]* 10.2 PBT — profilni yangilash round-trip va telefon o'zgarmasligi
    - **Feature: mtt-menejer-diagnostika, Property 11: Profilni yangilash round-trip va telefon o'zgarmasligi**
    - **Tekshiradi: Requirements 5.2, 5.3, 5.4** — Hypothesis, kamida 100 iteratsiya
  - [x] 10.3 TestService — testlar ro'yxati va tafsiloti
    - `list_tests` (faqat is_active, bo'sh bo'lsa bo'sh ro'yxat, toifalash);
      `get_test` (savollar order_index bo'yicha, mavjud/faol bo'lmasa 404)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  - [ ]* 10.4 PBT — testlar ro'yxati faqat faol testlarni qaytaradi
    - **Feature: mtt-menejer-diagnostika, Property 12: Testlar ro'yxati faqat faol testlarni qaytaradi**
    - **Tekshiradi: Requirements 6.1, 6.5** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 10.5 PBT — test tafsiloti savollarni belgilangan tartibda qaytaradi
    - **Feature: mtt-menejer-diagnostika, Property 13: Test tafsiloti savollarni belgilangan tartibda qaytaradi**
    - **Tekshiradi: Requirements 6.3** — Hypothesis, kamida 100 iteratsiya

- [ ] 11. Sessiya hayot sikli va Baholash servis integratsiyasi
  - [x] 11.1 SessionService — boshlash va avto-yakunlash
    - `start_session` (tugatilmagan bo'lmasa yangi, bo'lsa mavjudini davom
      ettirish — UNIQUE constraint bilan); `auto_finish` (muddat tugaganda
      mavjud javoblarni qabul qilish, javobsizlarni belgilash)
    - _Requirements: 7.1, 7.5, 7.10_
  - [ ]* 11.2 PBT — test boshlashning idempotentligi
    - **Feature: mtt-menejer-diagnostika, Property 14: Test boshlashning idempotentligi**
    - **Tekshiradi: Requirements 7.1, 7.10** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 11.3 PBT — muddat tugaganda avtomatik yakunlash
    - **Feature: mtt-menejer-diagnostika, Property 16: Muddat tugaganda avtomatik yakunlash**
    - **Tekshiradi: Requirements 7.5** — Hypothesis, kamida 100 iteratsiya
  - [x] 11.4 SessionService — topshirish (idempotent) va ScoringService ulanishi
    - `submit_session` — javoblarni saqlash, sessiyani yakunlash, domen scoring
      funksiyalarini chaqirish va `test_results`/`competency_results` saqlash;
      takroriy topshirish 409, javobsiz savol (muddat tugamagan) rad, begona/yo'q
      sessiya 404; natijani saqlab tavsiyalarni avto-tanlashga uzatish
    - _Requirements: 7.6, 7.7, 7.8, 7.9, 8.6_
  - [ ]* 11.5 PBT — test topshirishning idempotentligi
    - **Feature: mtt-menejer-diagnostika, Property 15: Test topshirishning idempotentligi**
    - **Tekshiradi: Requirements 7.6, 7.7** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 11.6 PBT — to'liqsiz topshirish va begona sessiya rad etiladi
    - **Feature: mtt-menejer-diagnostika, Property 17: To'liqsiz topshirish va begona sessiya rad etiladi**
    - **Tekshiradi: Requirements 7.8, 7.9** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 11.7 PBT — natija saqlanishining round-trip xususiyati
    - **Feature: mtt-menejer-diagnostika, Property 21: Natija saqlanishining round-trip xususiyati**
    - **Tekshiradi: Requirements 8.6** — Hypothesis, kamida 100 iteratsiya

- [ ] 12. Analitika, Tavsiya va Hisobot servislari
  - [x] 12.1 AnalyticsService ni yozish
    - `get_my_analytics` — umumiy ball, kompetensiya taqsimoti (radar/progress/
      line/card uchun ma'lumot), xronologik o'sish dinamikasi va farq, kuchli/
      zaif kompetensiya, natija yo'q bo'lsa muvaffaqiyatli bo'sh holat
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_
  - [x] 12.2 RecommendationService ni yozish
    - `assign_recommendations` (natija hisoblanganda avto-tanlash va bog'lash,
      text_snapshot); `get_my_recommendations` / `get_by_result` (egalik
      tekshiruvi, yo'q natija 404, natija yo'q bo'lsa bo'sh holat)
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_
  - [ ]* 12.3 PBT — tavsiyalarni so'nggi/aniq natija bo'yicha olish
    - **Feature: mtt-menejer-diagnostika, Property 29: Tavsiyalarni so'nggi/aniq natija bo'yicha olish**
    - **Tekshiradi: Requirements 10.2, 10.3** — Hypothesis, kamida 100 iteratsiya
  - [x] 12.4 ReportService ni yozish
    - `admin_report`, `report_by_region`, `report_by_organization`,
      `individual_dynamics` — domen agregatsiya funksiyalaridan foydalanib;
      ekspert uchun faqat biriktirilgan tashkilotlar; natija yo'q bo'lsa nol
      qiymatli bo'sh holat
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_

- [ ] 13. Portfolio, Ekspert va Admin servislari
  - [x] 13.1 LocalFileStorage va PortfolioService ni yozish
    - `FileStorageBackend` ning `LocalFileStorage` implementatsiyasi; `upload`
      (tur PDF/JPG/PNG/DOC/DOCX, hajm ≤10 485 760 bayt, nom 1–200; kengaytma +
      MIME tekshiruvi), `list_portfolio` (sana kamayuvchi), `delete` (egalik,
      yo'q bo'lsa 404, faylni o'chirish)
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 17.4, 18.2_
  - [ ]* 13.2 PBT — portfolio ro'yxati sana bo'yicha kamayuvchi tartibda
    - **Feature: mtt-menejer-diagnostika, Property 30: Portfolio ro'yxati sana bo'yicha kamayuvchi tartibda**
    - **Tekshiradi: Requirements 11.1** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 13.3 PBT — fayl yuklash validatsiyasi
    - **Feature: mtt-menejer-diagnostika, Property 31: Fayl yuklash validatsiyasi**
    - **Tekshiradi: Requirements 11.2, 11.3, 11.4, 17.4** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 13.4 PBT — portfolio o'chirishning round-trip va egalik xususiyati
    - **Feature: mtt-menejer-diagnostika, Property 32: Portfolio o'chirishning round-trip va egalik xususiyati**
    - **Tekshiradi: Requirements 11.5, 11.6, 11.7** — Hypothesis, kamida 100 iteratsiya
  - [x] 13.5 ExpertReviewService ni yozish
    - `submit_review` — 6 mezon validatsiyasi va o'rtacha (domen), biriktirilganlik
      tekshiruvi (biriktirilmagan 403), natijaga qo'shimcha ko'rsatkich qo'shish,
      bildirishnoma hodisasini chaqirish
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_
  - [x] 13.6 AdminService ni yozish
    - Test/savol/kompetensiya/tavsiya CRUD; test validatsiyasi (nom 1–200, toifa,
      davomiyligi 1–600), savol validatsiyasi (matn 1–1000, ≥2 variant, ball
      0.01–1000, mavjud kompetensiya); testni nofaol qilish; ishlatilayotgan
      kompetensiyani o'chirishni rad etish (referensial yaxlitlik)
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.6, 14.7, 14.8_
  - [ ]* 13.7 PBT — admin test/savol validatsiyasi
    - **Feature: mtt-menejer-diagnostika, Property 38: Admin test/savol validatsiyasi**
    - **Tekshiradi: Requirements 14.2, 14.3, 14.6** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 13.8 PBT — referensial yaxlitlik
    - **Feature: mtt-menejer-diagnostika, Property 39: Referensial yaxlitlik**
    - **Tekshiradi: Requirements 14.7, 14.8** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 13.9 PBT — testni nofaol qilish faol ro'yxatdan chiqaradi
    - **Feature: mtt-menejer-diagnostika, Property 40: Testni nofaol qilish faol ro'yxatdan chiqaradi**
    - **Tekshiradi: Requirements 14.4** — Hypothesis, kamida 100 iteratsiya

- [ ] 14. Bildirishnoma_Xizmati (FCM filtr mantig'i)
  - [x] 14.1 NotificationService va FCM mijoz abstraksiyasini yozish
    - Qabul qiluvchilarni filtrlash (notifications_enabled va yaroqli device_token);
      `notify_new_test`/`notify_retake`/`notify_deadline`/`notify_expert_review`;
      FCM yuborgich abstraksiyasi (mock qilinadigan); o'tkazib yuborish xato emas
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6_
  - [ ]* 14.2 PBT — bildirishnoma qabul qiluvchilarini filtrlash
    - **Feature: mtt-menejer-diagnostika, Property 41: Bildirishnoma qabul qiluvchilarini filtrlash**
    - **Tekshiradi: Requirements 16.5, 16.6** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 14.3 FCM dispatch integratsion testi (mock)
    - FCM mock bilan hodisalarda yuborish chaqirilishini tekshirish
    - _Requirements: 16.1, 16.2, 16.3, 16.4_

- [x] 15. Checkpoint — servis qatlami
  - Barcha servis va domen testlari (Property 1–4, 7–41 doirasidagi) o'tishiga
    ishonch hosil qiling, savol tug'ilsa foydalanuvchidan so'rang.

- [ ] 16. REST API middleware qatlami
  - [x] 16.1 AuthMiddleware va xato boshqaruvini yozish
    - JWT imzo/muddat/blacklist tekshiruvi (yaroqsiz -> 401); markazlashtirilgan
      exception handler'lar yagona tuzilgan xato formatiga (code/message/details)
      keltiradi; 404/405 mos javoblar
    - _Requirements: 2.5, 17.2, 20.6, 20.7_
  - [ ]* 16.2 PBT — token hayot sikli va bekor qilish
    - **Feature: mtt-menejer-diagnostika, Property 5: Token hayot sikli va bekor qilish**
    - **Tekshiradi: Requirements 2.4, 2.5, 17.2** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 16.3 PBT — yaroqsiz so'rov holatni o'zgartirmaydi
    - **Feature: mtt-menejer-diagnostika, Property 44: Yaroqsiz so'rov holatni o'zgartirmaydi**
    - **Tekshiradi: Requirements 20.6** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 16.4 PBT — noma'lum yo'l va qo'llab-quvvatlanmaydigan usul
    - **Feature: mtt-menejer-diagnostika, Property 45: Noma'lum yo'l va qo'llab-quvvatlanmaydigan usul**
    - **Tekshiradi: Requirements 20.7** — Hypothesis, kamida 100 iteratsiya
  - [x] 16.5 RBACGuard ni yozish
    - Ikki bosqichli RBAC: rol darajasi + egalik/biriktirilganlik; ruxsatsizda
      403 (holat o'zgarmaydi, ma'lumot oshkor bo'lmaydi); o'z natijalari filtri
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 17.6_
  - [ ]* 16.6 PBT — RBAC izolyatsiyasi va egalik
    - **Feature: mtt-menejer-diagnostika, Property 6: RBAC izolyatsiyasi va egalik**
    - **Tekshiradi: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 13.5, 14.5, 15.6, 17.6** — Hypothesis, kamida 100 iteratsiya
  - [x] 16.7 RateLimitMiddleware va LoggingMiddleware ni yozish
    - Joriy oyna bo'yicha hisoblagich (in-memory/Redis), oshsa 429; maxfiy
      maydonlarni (parol, token, telefon) jurnaldan maskalovchi allow-list logging
    - _Requirements: 17.3, 17.5_
  - [ ]* 16.8 PBT — rate limiting joriy oyna bo'yicha
    - **Feature: mtt-menejer-diagnostika, Property 42: Rate limiting joriy oyna bo'yicha**
    - **Tekshiradi: Requirements 17.3** — Hypothesis, kamida 100 iteratsiya
  - [ ]* 16.9 PBT — jurnal gigiyenasi
    - **Feature: mtt-menejer-diagnostika, Property 43: Jurnal gigiyenasi**
    - **Tekshiradi: Requirements 17.5** — Hypothesis, kamida 100 iteratsiya

- [ ] 17. REST API routerlari va OpenAPI
  - [x] 17.1 Auth va profil routerlari
    - `/auth/register|login|refresh|logout|forgot-password|reset-password`,
      `/users/me` (GET/PATCH), `/users/{id}`; Pydantic so'rov/javob sxemalari
    - _Requirements: 20.1, 20.2, 20.6_
  - [x] 17.2 Test, sessiya va natija routerlari
    - `/tests`, `/tests/{id}`, `/tests/{id}/start`, `/tests/{id}/submit`,
      `/tests/results/me`, `/tests/results/{id}` (RBAC/egalik bilan)
    - _Requirements: 20.3, 7.6, 7.7, 8.6_
  - [x] 17.3 Kontent, tavsiya, portfolio va analitika routerlari
    - `/questions` (CRUD), `/recommendations/me|by-result/{id}`,
      `/portfolio/me|upload|{id}`, `/analytics/me|organization/{id}|region/{id}`
    - _Requirements: 20.4, 9.1, 10.2, 11.1_
  - [x] 17.4 Admin, ekspert, hisobot, reyting va qurilma routerlari
    - `/admin/users|results|tests...`, `/expert/reviews|leaders`,
      `/reports/...`, `/rating?scope=...`, `/devices/token`
    - _Requirements: 20.4, 12.1, 13.1, 15.1, 16.1_
  - [x]* 17.5 OpenAPI qoplam smoke/integratsion testi
    - **Feature: mtt-menejer-diagnostika, Property 46: OpenAPI hujjati barcha endpointlarni qoplaydi**
    - **Tekshiradi: Requirements 20.5** — barcha sanab o'tilgan endpointlar
      `/openapi.json` da usul/yo'l/sxema bilan mavjudligini tekshiradi
  - [x]* 17.6 Endpoint mavjudligi va RBAC matritsasi integratsion testlari
    - Route mavjudligi smoke testlari va rol matritsasi (Rahbar/Ekspert/Admin ×
      ruxsat/rad) integratsion testlari
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 4.1, 4.2, 4.3_

- [x] 18. Checkpoint — backend yakuni
  - Barcha backend testlari (unit, PBT, integratsion) o'tishiga ishonch hosil
    qiling, savol tug'ilsa foydalanuvchidan so'rang.

- [x] 19. Mobil ilova asoslari va ma'lumot qatlami (Flutter)
  - [x] 19.1 Flutter loyiha skeletoni va qatlamlar
    - Material Design ilova skeletoni (Android minSdk=26 / 8.0+), Riverpod state
      management, papka tuzilmasi (presentation/state/repository/data), fast_check
      (yoki ekvivalent) PBT konfiguratsiyasi (kamida 100 iteratsiya)
    - _Requirements: 19.1, 19.2_
  - [x] 19.2 ApiClient (Dio) va modellar
    - Dio interceptor — `Authorization: Bearer` qo'shish, 401'da refresh oqimi,
      muvaffaqiyatsizda login'ga yo'naltirish; backend sxemalariga mos DTO modellar
    - _Requirements: 2.3, 20.1, 20.2, 20.3, 20.4_
  - [x] 19.3 LocalCache (Drift) va SyncQueue
    - Drift/SQLite kesh — yuklangan testlar va savollar; SyncQueue — offline
      topshirilgan natijalarni idempotency_key bilan navbatga olish; ulanish
      tiklanganda yuborish va muvaffaqiyatda navbatdan o'chirish
    - _Requirements: 19.3, 19.4_
  - [ ]* 19.4 PBT — offline kesh round-trip
    - **Feature: mtt-menejer-diagnostika, Property 47: Offline kesh round-trip**
    - **Tekshiradi: Requirements 19.3** — fast_check (yoki ekvivalent), kamida 100 iteratsiya
  - [ ]* 19.5 PBT — sinxronizatsiya to'liqligi va idempotentligi
    - **Feature: mtt-menejer-diagnostika, Property 48: Sinxronizatsiya to'liqligi va idempotentligi**
    - **Tekshiradi: Requirements 19.4** — fast_check (yoki ekvivalent), kamida 100 iteratsiya

- [x] 20. Mobil ilova taqdimot qatlami va integratsiya
  - [x] 20.1 Autentifikatsiya va profil ekranlari
    - Splash/onboarding, login, register, profil ko'rish/tahrirlash ekranlari;
      Repository orqali API/kesh ulanishi; global auth holati (token, rol)
    - _Requirements: 1.1, 2.1, 5.1, 5.2, 19.2_
  - [x] 20.2 Test, natija va analitika ekranlari
    - Testlar ro'yxati, test topshirish (Likert va situatsion taqdimot, qolgan
      vaqt, progress), natija va analitika diagrammalari (radar/progress/line/card),
      portfolio ekranlari
    - _Requirements: 6.1, 7.2, 7.3, 7.4, 8.4, 9.2, 11.1_
  - [x] 20.3 FCM mijozi va qurilma tokeni ro'yxatdan o'tishi
    - Push qabul qilish va device token'ni `POST /devices/token` orqali ro'yxatga
      olish; notifications_enabled sozlamasi
    - _Requirements: 16.1, 16.5_
  - [x]* 20.4 Mobil widget va build smoke testlari
    - Material Design widget testlari (test-taking, analitika) va Android
      minSdk=26 build tekshiruvi
    - _Requirements: 19.1, 19.2, 7.3, 7.4_

- [x] 21. Yakuniy integratsiya va ulash
  - [x] 21.1 Boshlang'ich ma'lumotlar (seed) va wiring
    - Rollar (Rahbar/Ekspert/Administrator), namunaviy kompetensiyalar va
      tavsiyalar seed migratsiyasi; barcha routerlar, middleware va servislarni
      FastAPI app'ga ulash; mobil ilovani backend bilan to'liq bog'lash
    - _Requirements: 1.7, 4.1, 10.4, 20.5_
  - [x]* 21.2 Uchidan-uchiga integratsion testlar
    - Ro'yxatdan o'tish → kirish → test topshirish → natija/tavsiya →
      analitika → reyting oqimini avtomatlashtirilgan integratsion testlar bilan
      tekshirish (mobil emas, backend API darajasida)
    - _Requirements: 7.6, 8.6, 10.1, 12.1_

- [~] 22. Yakuniy checkpoint — barcha testlar
  - Barcha testlar (unit, 48 ta property-based test, integratsion, smoke, widget)
    o'tishiga ishonch hosil qiling, savol tug'ilsa foydalanuvchidan so'rang.

## Notes

- `*` bilan belgilangan sub-vazifalar ixtiyoriy (test) bo'lib, tezkor MVP uchun
  o'tkazib yuborilishi mumkin, lekin korrektlik kafolati uchun tavsiya etiladi.
- Har bir vazifa kuzatuvchanlik uchun aniq talab(lar)ga ishora qiladi.
- Checkpoint'lar inkremental tekshiruvni ta'minlaydi.
- 48 ta korrektlik xususiyatining har biri AYNAN bitta property-based test bilan
  amalga oshiriladi (Hypothesis backend, fast_check/ekvivalent mobil), kamida
  100 iteratsiya va dizaynda belgilangan tag formati bilan.
- PBT uchun mos bo'lmagan kriteriyalar (R7.2–R7.4 UI, R13.6/R16.1–R16.4 push
  yuborish, R18.x, R19.1–R19.2, R20.1–R20.4) integratsion/smoke/widget testlar
  bilan qoplanadi.
- Domen mantig'i (scoring/rating/analitika/ekspert) I/O'dan mustaqil sof
  funksiyalar sifatida yoziladi va PBT uchun asosiy nishon bo'ladi.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "3.1", "4.1", "5.1", "5.4", "6.1", "6.4", "8.1", "8.4"] },
    { "id": 2, "tasks": ["2.2", "3.2", "3.3", "3.4", "4.2", "4.3", "5.2", "5.3", "5.5", "5.6", "5.7", "6.2", "6.3", "6.5", "8.2", "8.3", "8.5", "8.6", "8.7", "9.1"] },
    { "id": 3, "tasks": ["2.3", "3.5", "3.6", "4.4", "4.5", "9.2", "9.3", "14.1"] },
    { "id": 4, "tasks": ["2.4", "9.4", "9.5", "10.1", "10.3", "11.1", "12.1", "12.2", "12.4", "13.1", "13.5", "13.6", "14.2", "14.3"] },
    { "id": 5, "tasks": ["10.2", "10.4", "10.5", "11.2", "11.3", "11.4", "12.3", "13.2", "13.3", "13.4", "13.7", "13.8", "13.9"] },
    { "id": 6, "tasks": ["11.5", "11.6", "11.7"] },
    { "id": 7, "tasks": ["16.1", "16.5", "16.7"] },
    { "id": 8, "tasks": ["16.2", "16.3", "16.4", "16.6", "16.8", "16.9", "17.1", "17.2", "17.3", "17.4"] },
    { "id": 9, "tasks": ["17.5", "17.6"] },
    { "id": 10, "tasks": ["19.1"] },
    { "id": 11, "tasks": ["19.2", "19.3"] },
    { "id": 12, "tasks": ["19.4", "19.5", "20.1", "20.2", "20.3"] },
    { "id": 13, "tasks": ["20.4", "21.1"] },
    { "id": 14, "tasks": ["21.2"] }
  ]
}
```
