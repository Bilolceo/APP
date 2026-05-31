// =============================================================================
// SyncQueue (Drift) — namunaviy unit testlar (R19.4)
// =============================================================================
// Xotiradagi Drift baza (`NativeDatabase.memory()`) ishlatiladi; yuborish
// funksiyasi ([SubmissionSender]) test ichida soxta (stub) sifatida beriladi —
// shu sabab test ApiClient/HTTP qatlamiga bog'lanmaydi (dekupling).
//
// MUHIM: bu testlar Drift kod generatsiyasiga tayanadi. Ishga tushirishdan oldin
//   dart run build_runner build --delete-conflicting-outputs
// buyrug'ini bajaring. SDK o'rnatilmagan muhitda ishga tushmaydi, lekin valid
// Dart kodidir.
//
// Eslatma: PBT Property 48 (Sinxronizatsiya to'liqligi va idempotentligi,
// Validates: Requirements 19.4) keyinchalik 19.5 vazifasida (ixtiyoriy)
// rasmiylashtiriladi; bu yerda namunaviy misollar berilgan.
// =============================================================================

import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mtt_menejer_diagnostika/data/local_cache/app_database.dart';
import 'package:mtt_menejer_diagnostika/data/sync_queue/sync_queue.dart';

void main() {
  late AppDatabase db;
  late DriftSyncQueue queue;

  setUp(() {
    db = AppDatabase(NativeDatabase.memory());
    queue = DriftSyncQueue(db);
  });

  tearDown(() async {
    await db.close();
  });

  QueuedSubmission sub(String key, {String session = 's1'}) {
    return QueuedSubmission(
      idempotencyKey: key,
      sessionId: session,
      payload: {'session_id': session, 'answers': [], 'key': key},
    );
  }

  group('enqueue idempotentligi', () {
    test('bir xil idempotencyKey ikki marta qo\'shilsa dublikat yaratmaydi',
        () async {
      await queue.enqueue(sub('idem-1'));
      await queue.enqueue(sub('idem-1'));

      final pending = await queue.pending();
      expect(pending.length, 1);
      expect(pending.single.idempotencyKey, 'idem-1');
    });

    test('turli kalitlar alohida elementlar sifatida saqlanadi', () async {
      await queue.enqueue(sub('idem-1'));
      await queue.enqueue(sub('idem-2'));

      final pending = await queue.pending();
      expect(pending.map((e) => e.idempotencyKey).toSet(), {'idem-1', 'idem-2'});
    });
  });

  group('flush', () {
    test('muvaffaqiyatli yuborilgan barcha elementlarni navbatdan o\'chiradi',
        () async {
      await queue.enqueue(sub('idem-1'));
      await queue.enqueue(sub('idem-2'));

      final sent = <String>[];
      final count = await queue.flush((s) async {
        sent.add(s.idempotencyKey);
        return true; // har doim muvaffaqiyat
      });

      expect(count, 2);
      expect(sent.toSet(), {'idem-1', 'idem-2'});
      expect(await queue.pending(), isEmpty);
    });

    test('faqat muvaffaqiyatli elementlarni o\'chiradi, xatolarni qoldiradi',
        () async {
      await queue.enqueue(sub('ok'));
      await queue.enqueue(sub('fail'));

      final count = await queue.flush((s) async {
        return s.idempotencyKey == 'ok'; // faqat "ok" muvaffaqiyatli
      });

      expect(count, 1);
      final pending = await queue.pending();
      expect(pending.length, 1);
      expect(pending.single.idempotencyKey, 'fail');
    });

    test('sender exception tashlasa element navbatda qoladi', () async {
      await queue.enqueue(sub('boom'));

      final count = await queue.flush((s) async {
        throw Exception('tarmoq xatosi');
      });

      expect(count, 0);
      expect((await queue.pending()).length, 1);
    });

    test('qayta flush qilish xavfsiz (idempotent to\'liqlik)', () async {
      await queue.enqueue(sub('idem-1'));

      // Birinchi flush muvaffaqiyatsiz (offline).
      await queue.flush((s) async => false);
      expect((await queue.pending()).length, 1);

      // Ikkinchi flush muvaffaqiyatli (ulanish tiklandi).
      final count = await queue.flush((s) async => true);
      expect(count, 1);
      expect(await queue.pending(), isEmpty);
    });
  });
}
