// =============================================================================
// AppDatabase — Drift/SQLite offline kesh va sinxronizatsiya navbati (R19.3, R19.4)
// =============================================================================
// MUHIM (kod generatsiyasi):
//   Ushbu fayl Drift `part` direktivasiga tayanadi. `app_database.g.dart`
//   fayli QO'LDA yozilmaydi — u quyidagi buyruq orqali generatsiya qilinadi:
//
//       dart run build_runner build --delete-conflicting-outputs
//
//   Generatsiya qilinmaguncha `_$AppDatabase`, `*Companion` va satr (data)
//   klasslari (`CachedTest`, `CachedQuestion`, `SyncQueueEntry`) mavjud bo'lmaydi
//   va analizator "part file not found / undefined" xatolarini ko'rsatadi.
//   Bu xatolar KUTILGAN bo'lib, faqat SDK + build_runner ishga tushgach yo'qoladi.
//
// Arxitektura (design.md): bu past darajadagi ma'lumotlar manbasi `LocalCache`
// va `SyncQueue` repozitoriylari tomonidan o'raladi. ApiClient/DTO modellariga
// bog'liqlik YO'Q — oldinga moslik (forward-compatibility) uchun har bir yozuv
// to'liq JSON payload ko'rinishida saqlanadi, qidiruv uchun esa bir nechta
// skalyar ustun ajratilgan.
// =============================================================================

import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

part 'app_database.g.dart';

/// Yuklab olingan (keshlangan) testlar jadvali (R19.3).
///
/// `payload` — testning to'liq JSON ko'rinishi (oldinga moslik uchun); qolgan
/// ustunlar offline ro'yxatni tez render qilish va saralash uchun.
@DataClassName('CachedTest')
class CachedTests extends Table {
  /// Test identifikatori (Backend `id`).
  TextColumn get id => text()();

  /// Test sarlavhasi (offline ro'yxatda ko'rsatiladi).
  TextColumn get title => text()();

  /// Kompetensiya/kategoriya kodi (ixtiyoriy).
  TextColumn get category => text().nullable()();

  /// Test davomiyligi (daqiqa, ixtiyoriy).
  IntColumn get durationMinutes => integer().nullable()();

  /// Testning to'liq JSON payload'i (round-trip uchun — Property 47).
  TextColumn get payload => text()();

  /// Keshga saqlangan vaqt (saralash/eskirishni aniqlash uchun).
  DateTimeColumn get cachedAt => dateTime()();

  @override
  Set<Column<Object>> get primaryKey => {id};
}

/// Keshlangan test savollari jadvali (R19.3).
///
/// `testId` bo'yicha indekslangan; `orderIndex` savollar tartibini saqlaydi.
@DataClassName('CachedQuestion')
class CachedQuestions extends Table {
  /// Savol identifikatori (Backend `id`).
  TextColumn get id => text()();

  /// Tegishli test identifikatori (`CachedTests.id` bilan bog'liq).
  TextColumn get testId => text()();

  /// Savolning test ichidagi tartib raqami.
  IntColumn get orderIndex => integer()();

  /// Savolning to'liq JSON payload'i (variantlar bilan birga — round-trip).
  TextColumn get payload => text()();

  @override
  Set<Column<Object>> get primaryKey => {id};
}

/// Offline topshirilgan natijalar uchun sinxronizatsiya navbati jadvali (R19.4).
///
/// `idempotencyKey` UNIQUE bo'lib, bir xil natijani ikki marta navbatga olishni
/// bloklaydi (idempotent enqueue — Property 48). Generatsiya qilinadigan satr
/// (data) klassi `QueuedSubmission` domen modeli bilan to'qnashmasligi uchun
/// `@DataClassName('SyncQueueEntry')` ishlatilgan.
@DataClassName('SyncQueueEntry')
class SyncQueueEntries extends Table {
  /// Avtomatik o'suvchi ichki kalit (birlamchi kalit).
  IntColumn get id => integer().autoIncrement()();

  /// Takroriy yuborishni xavfsiz qiluvchi idempotentlik kaliti (UNIQUE).
  TextColumn get idempotencyKey => text().unique()();

  /// Tegishli test sessiyasi identifikatori.
  TextColumn get sessionId => text()();

  /// Yuboriladigan natijaning to'liq JSON payload'i.
  TextColumn get payload => text()();

  /// Navbat holati: `pending` (kutilmoqda) yoki `sending` (yuborilmoqda).
  TextColumn get status => text().withDefault(const Constant('pending'))();

  /// Muvaffaqiyatsiz urinishlar soni (exponential backoff uchun — TODO 20.x).
  IntColumn get attemptCount => integer().withDefault(const Constant(0))();

  /// Navbatga qo'shilgan vaqt (FIFO saralash uchun).
  DateTimeColumn get createdAt => dateTime()();
}

/// Ilovaning yagona Drift/SQLite ma'lumotlar bazasi (offline kesh + sync navbati).
///
/// Generatsiya qilingach `_$AppDatabase` quyidagi getter'larni beradi:
/// `cachedTests`, `cachedQuestions`, `syncQueueEntries`.
@DriftDatabase(tables: [CachedTests, CachedQuestions, SyncQueueEntries])
class AppDatabase extends _$AppDatabase {
  /// Standart (fayl asosidagi) yoki berilgan [executor] bilan bazani ochadi.
  ///
  /// Testlarda `NativeDatabase.memory()` uzatish orqali xotiradagi baza
  /// ishlatiladi (disk yozuvisiz, tez va izolyatsiyalangan).
  AppDatabase([QueryExecutor? executor]) : super(executor ?? _openConnection());

  @override
  int get schemaVersion => 1;

  /// Ilova hujjatlari papkasida SQLite faylini lazy (kerak bo'lganda) ochadi.
  static QueryExecutor _openConnection() {
    return LazyDatabase(() async {
      final dir = await getApplicationDocumentsDirectory();
      final file = File(p.join(dir.path, 'mtt_cache.sqlite'));
      return NativeDatabase.createInBackground(file);
    });
  }
}
