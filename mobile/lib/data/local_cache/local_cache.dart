/// Offline lokal kesh repozitoriysi (Drift/SQLite) (R19.3).
///
/// `LocalCache` — [AppDatabase] ustidagi yuqori darajadagi o'ram (wrapper).
/// Yuklab olingan testlar va savollarni keshlaydi hamda offline rejimda
/// qaytaradi. ApiClient/DTO modellariga bog'liqlik YO'Q: ma'lumotlar
/// `Map<String, dynamic>` (JSON) ko'rinishida uzatiladi va saqlanadi, shu sabab
/// bu modul 19.2 (modellar) vazifasidan mustaqil bo'lib qoladi.
///
/// MUHIM: [AppDatabase] Drift kod generatsiyasiga tayanadi. Ishlatishdan oldin
///   dart run build_runner build --delete-conflicting-outputs
/// buyrug'ini ishga tushiring (`app_database.g.dart` generatsiyasi).

import 'dart:convert';

import 'package:drift/drift.dart';

import 'app_database.dart';

export 'app_database.dart';

/// Offline kesh ustidagi amallarni belgilovchi shartnoma (R19.3).
///
/// Konkret implementatsiya — [DriftLocalCache].
abstract interface class LocalCache {
  /// Yuklab olingan testlar to'plamini keshga saqlaydi (mavjudlarini almashtiradi).
  Future<void> cacheTests(List<Map<String, dynamic>> tests);

  /// Keshlangan testlarni JSON xaritalar ro'yxati sifatida qaytaradi.
  Future<List<Map<String, dynamic>>> getCachedTests();

  /// Berilgan [testId] uchun savollarni keshga saqlaydi (mavjudlarini almashtiradi).
  Future<void> cacheQuestions(String testId, List<Map<String, dynamic>> questions);

  /// Berilgan [testId] bo'yicha keshlangan savollarni tartibida qaytaradi.
  Future<List<Map<String, dynamic>>> getCachedQuestions(String testId);

  /// Keshni to'liq tozalaydi (masalan, logout vaqtida).
  Future<void> clear();
}

/// `LocalCache` ning Drift/SQLite asosidagi implementatsiyasi (R19.3).
class DriftLocalCache implements LocalCache {
  /// Ichki Drift bazasi.
  final AppDatabase _db;

  /// Berilgan [AppDatabase] bilan kesh repozitoriysini yaratadi.
  ///
  /// Testlarda xotiradagi baza uzatiladi:
  /// `DriftLocalCache(AppDatabase(NativeDatabase.memory()))`.
  DriftLocalCache(this._db);

  @override
  Future<void> cacheTests(List<Map<String, dynamic>> tests) async {
    await _db.transaction(() async {
      // Eski keshni almashtiramiz (idempotent: bir xil to'plam takror yozilsa
      // yakuniy holat o'zgarmaydi).
      await _db.delete(_db.cachedTests).go();
      for (final test in tests) {
        await _db.into(_db.cachedTests).insert(
              CachedTestsCompanion.insert(
                id: _asString(test['id']),
                title: _asString(test['title']),
                category: Value(_asNullableString(test['category'])),
                durationMinutes: Value(_asNullableInt(test['duration_minutes'])),
                payload: jsonEncode(test),
                cachedAt: DateTime.now().toUtc(),
              ),
              mode: InsertMode.insertOrReplace,
            );
      }
    });
  }

  @override
  Future<List<Map<String, dynamic>>> getCachedTests() async {
    final query = _db.select(_db.cachedTests)
      ..orderBy([(t) => OrderingTerm(expression: t.cachedAt)]);
    final rows = await query.get();
    return rows.map((row) => _decodePayload(row.payload)).toList();
  }

  @override
  Future<void> cacheQuestions(
    String testId,
    List<Map<String, dynamic>> questions,
  ) async {
    await _db.transaction(() async {
      // Shu testga tegishli eski savollarni almashtiramiz.
      await (_db.delete(_db.cachedQuestions)
            ..where((q) => q.testId.equals(testId)))
          .go();
      var index = 0;
      for (final question in questions) {
        await _db.into(_db.cachedQuestions).insert(
              CachedQuestionsCompanion.insert(
                id: _asString(question['id']),
                testId: testId,
                orderIndex: _asNullableInt(question['order_index']) ?? index,
                payload: jsonEncode(question),
              ),
              mode: InsertMode.insertOrReplace,
            );
        index++;
      }
    });
  }

  @override
  Future<List<Map<String, dynamic>>> getCachedQuestions(String testId) async {
    final query = _db.select(_db.cachedQuestions)
      ..where((q) => q.testId.equals(testId))
      ..orderBy([(q) => OrderingTerm(expression: q.orderIndex)]);
    final rows = await query.get();
    return rows.map((row) => _decodePayload(row.payload)).toList();
  }

  @override
  Future<void> clear() async {
    await _db.transaction(() async {
      await _db.delete(_db.cachedQuestions).go();
      await _db.delete(_db.cachedTests).go();
    });
  }

  // --- Yordamchi (private) konvertorlar ------------------------------------

  /// JSON payload satrini xaritaga aylantiradi (round-trip — Property 47).
  Map<String, dynamic> _decodePayload(String payload) {
    final decoded = jsonDecode(payload);
    return Map<String, dynamic>.from(decoded as Map);
  }

  String _asString(Object? value) => value?.toString() ?? '';

  String? _asNullableString(Object? value) => value?.toString();

  int? _asNullableInt(Object? value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value);
    return null;
  }
}
