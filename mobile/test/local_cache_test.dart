// =============================================================================
// LocalCache (Drift) — namunaviy unit testlar (R19.3)
// =============================================================================
// Xotiradagi Drift baza (`NativeDatabase.memory()`) ishlatiladi: disk yozuvisiz,
// tez va har bir test uchun izolyatsiyalangan.
//
// MUHIM: bu testlar Drift kod generatsiyasiga tayanadi. Ishga tushirishdan oldin
//   dart run build_runner build --delete-conflicting-outputs
// buyrug'ini bajaring (`app_database.g.dart` generatsiyasi). SDK o'rnatilmagan
// muhitda bu testlar ishga tushmaydi, lekin valid Dart kodidir.
//
// Eslatma: PBT Property 47 (Offline kesh round-trip, Validates: Requirements
// 19.3) keyinchalik 19.4 vazifasida (ixtiyoriy) rasmiylashtiriladi; bu yerda
// namunaviy round-trip misollari berilgan.
// =============================================================================

import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mtt_menejer_diagnostika/data/local_cache/app_database.dart';
import 'package:mtt_menejer_diagnostika/data/local_cache/local_cache.dart';

void main() {
  late AppDatabase db;
  late DriftLocalCache cache;

  setUp(() {
    db = AppDatabase(NativeDatabase.memory());
    cache = DriftLocalCache(db);
  });

  tearDown(() async {
    await db.close();
  });

  group('LocalCache testlar keshi', () {
    test('cacheTests/getCachedTests round-trip ma\'lumotni saqlaydi', () async {
      final tests = [
        {
          'id': 't1',
          'title': 'Liderlik testi',
          'category': 'leadership',
          'duration_minutes': 30,
          'extra': {'nested': true},
        },
        {
          'id': 't2',
          'title': 'Moliyaviy boshqaruv',
          'category': 'finance',
          'duration_minutes': 45,
        },
      ];

      await cache.cacheTests(tests);
      final result = await cache.getCachedTests();

      expect(result.length, 2);
      final ids = result.map((t) => t['id']).toSet();
      expect(ids, {'t1', 't2'});
      // To'liq payload (jumladan ichki obyekt) saqlanganini tekshiramiz.
      final t1 = result.firstWhere((t) => t['id'] == 't1');
      expect(t1['title'], 'Liderlik testi');
      expect((t1['extra'] as Map)['nested'], true);
    });

    test('cacheTests qayta chaqirilsa eski keshni almashtiradi', () async {
      await cache.cacheTests([
        {'id': 't1', 'title': 'Eski'},
      ]);
      await cache.cacheTests([
        {'id': 't2', 'title': 'Yangi'},
      ]);

      final result = await cache.getCachedTests();
      expect(result.length, 1);
      expect(result.single['id'], 't2');
    });
  });

  group('LocalCache savollar keshi', () {
    test('cacheQuestions/getCachedQuestions tartibni saqlaydi', () async {
      await cache.cacheQuestions('t1', [
        {'id': 'q1', 'order_index': 0, 'text': 'Savol 1'},
        {'id': 'q2', 'order_index': 1, 'text': 'Savol 2'},
      ]);

      final result = await cache.getCachedQuestions('t1');
      expect(result.map((q) => q['id']).toList(), ['q1', 'q2']);
    });

    test('getCachedQuestions faqat tegishli test savollarini qaytaradi',
        () async {
      await cache.cacheQuestions('t1', [
        {'id': 'q1', 'order_index': 0},
      ]);
      await cache.cacheQuestions('t2', [
        {'id': 'q2', 'order_index': 0},
      ]);

      final t1 = await cache.getCachedQuestions('t1');
      expect(t1.length, 1);
      expect(t1.single['id'], 'q1');
    });
  });

  test('clear keshni to\'liq tozalaydi', () async {
    await cache.cacheTests([
      {'id': 't1', 'title': 'Test'},
    ]);
    await cache.cacheQuestions('t1', [
      {'id': 'q1', 'order_index': 0},
    ]);

    await cache.clear();

    expect(await cache.getCachedTests(), isEmpty);
    expect(await cache.getCachedQuestions('t1'), isEmpty);
  });
}
