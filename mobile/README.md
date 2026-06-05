# MTT Menejer Diagnostika — Mobil ilova (Flutter)

MTT (Maktabgacha Ta'lim Tashkiloti) rahbarlari kompetensiyalarini raqamli
diagnostika qiluvchi **Android** mobil ilovasi.

- **Platforma:** Android 8.0+ (`minSdk = 26`) — R19.1
- **UI:** Material Design 3 — R19.2
- **State management:** Riverpod
- **Texnologiyalar:** Dio (API), Drift/SQLite (offline kesh), FCM (push),
  fl_chart (analitika diagrammalari)

> ✅ **Holat:** Mobil loyiha MVP bosqichiga keltirilgan. 19.1–19.3 va 20.1–20.4
> vazifalari bajarilgan; ayrim kod joylarida keyingi iteratsiyalar uchun
> `TODO(<vazifa>)` izohlari qoldirilgan.

## Papka tuzilmasi

```
mobile/
├── lib/
│   ├── main.dart                 # ProviderScope + MaterialApp (Material 3)
│   ├── core/                     # konstantalar, mavzu (theme)
│   ├── presentation/             # ekranlar (Material Design) — TODO 20.x
│   ├── state/                    # Riverpod provider'lari
│   ├── repository/               # API + kesh manbalarini birlashtiradi
│   └── data/
│       ├── api_client/           # Dio + JWT interceptor — TODO 19.2
│       ├── local_cache/          # Drift/SQLite — TODO 19.3
│       ├── sync_queue/           # offline natija navbati — TODO 19.3
│       └── models/               # DTO modellar — TODO 19.2
├── test/                         # widget + PBT (glados) testlari
└── android/                      # Android konfiguratsiyasi (minSdk=26)
```

Qatlamlar (design.md): **Presentation → State (Riverpod) → Repository →
data manbalari (ApiClient / LocalCache / SyncQueue)**.

## Ishga tushirish (hydration) qadamlari

Flutter SDK o'rnatilgan muhitda quyidagilarni bajaring:

```bash
# 1) Bog'liqliklarni o'rnatish
flutter pub get

# 2) (Birinchi marta) Native qobiqni hidratsiya qilish — agar android/ios
#    platformasi to'liq bo'lmasa, mavjud fayllarni saqlagan holda to'ldiradi:
#    flutter create .

# 3) Drift (SQLite) kod generatsiyasi
dart run build_runner build

# 4) Testlarni ishga tushirish (widget + property-based)
flutter test

# 5) Ilovani qurilma/emulyatorda ishga tushirish
flutter run

# 5.1) Real telefonda backendga ulash (tarmoq xatosi bo'lsa):
#      <LAN_IP> o'rniga backend ishlayotgan kompyuter IP'sini yozing.
flutter run --dart-define=API_BASE_URL=http://<LAN_IP>:8010

# 6) MVP smoke (analyze + test + android debug build)
./scripts/mvp_smoke.sh

# 7) APK build (real telefon uchun API manzil bilan)
flutter build apk --debug --dart-define=API_BASE_URL=http://<LAN_IP>:8010
```

Joriy MVP backend shu Mac'da ishlaganda build:

```bash
flutter build apk --debug --dart-define=API_BASE_URL=http://172.16.240.124:8010
```

APK manzili:

```text
mobile/build/app/outputs/flutter-apk/app-debug.apk
```

Demo login:

```text
Telefon: +998901112236
Parol: secret123
```

## Property-Based Testing (PBT)

- Kutubxona: **`glados`** — Dart uchun PBT freymvorki (`fast_check` ekvivalenti).
- Har bir korrektlik xususiyati **AYNAN bitta** PBT bilan amalga oshiriladi.
- Har bir PBT **kamida 100 iteratsiya** bilan ishlaydi
  (`ExploreConfig(numRuns: 100)`).
- Tag formati: `Feature: mtt-menejer-diagnostika, Property {N}: {matn}`.
- Mobil property'lar: **47** (offline kesh round-trip, R19.3) va **48**
  (sinxronizatsiya to'liqligi/idempotentligi, R19.4) — TODO 19.4/19.5.

Namuna konfiguratsiya: `test/pbt_config_test.dart`.

## Firebase (FCM)

Push bildirishnomalar (R16) uchun Firebase loyihasi sozlanishi va
`android/app/google-services.json` fayli qo'shilishi kerak (TODO 20.3).
Bu fayl maxfiy bo'lgani uchun `.gitignore` ga kiritilgan.

Ilova ishga tushganda Firebase init best-effort tarzda bajariladi; foydalanuvchi
autentifikatsiyadan o'tgach FCM token `POST /devices/token` orqali backendga
ro'yxatdan o'tkaziladi, token yangilanganda esa qayta yuboriladi.

## Build/test holati

2026-06-05 holatiga ko'ra quyidagilar muvaffaqiyatli tekshirildi:

- `flutter pub get`
- `flutter test`
- `flutter build apk --debug --dart-define=API_BASE_URL=http://172.16.240.124:8010`
- `./scripts/mvp_smoke.sh` (doctor + pub get + drift codegen + analyze + test + build)

Eslatma: `flutter doctor` iOS/Xcode bo'yicha ogohlantirish berishi mumkin, bu
Android MVP build oqimiga ta'sir qilmaydi.
