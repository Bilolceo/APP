/// Offline topshirilgan natijalar uchun sinxronizatsiya navbati (R19.4).
///
/// `SyncQueue` — internet uzilganda topshirilgan test natijalarini
/// `idempotencyKey` bilan navbatga oladi; ulanish tiklanganda navbatdagi
/// elementlarni Backend'ga yuboradi va MUVAFFAQIYATda navbatdan o'chiradi.
///
/// DEKUPLING (19.2 dan mustaqillik): konkret `ApiClient` import QILINMAYDI.
/// Yuborish mas'uliyati [SubmissionSender] funksiya-tipi orqali tashqaridan
/// in'ektsiya qilinadi. Bu modul testlanuvchan bo'lib qoladi va modellar/HTTP
/// qatlamiga bog'lanmaydi.
///
/// ULANISH TIKLANISHI (connectivity-restore):
///   `flush` ni qachon chaqirish — taqdimot/holat qatlamining (20.x)
///   mas'uliyati. U yerda `connectivity_plus` (yoki shunga o'xshash) listener
///   ulanish tiklanganini aniqlab, `syncQueue.flush(sender)` ni chaqiradi.
///   TODO(20.x): connectivity listener'ni ulang va `flush` ni triggerlang.
///
/// MUHIM: implementatsiya [AppDatabase] (Drift) ga tayanadi. Ishlatishdan oldin
///   dart run build_runner build --delete-conflicting-outputs
/// buyrug'ini ishga tushiring (`app_database.g.dart` generatsiyasi).

import 'dart:convert';

import 'package:drift/drift.dart';

import '../local_cache/app_database.dart';

/// Navbatga olinadigan bitta offline topshiriq (domen modeli).
class QueuedSubmission {
  /// Takroriy yuborishni xavfsiz qiluvchi idempotentlik kaliti (UNIQUE).
  final String idempotencyKey;

  /// Tegishli test sessiyasi identifikatori.
  final String sessionId;

  /// Yuboriladigan natija ma'lumotlari (JSON ko'rinishida).
  final Map<String, dynamic> payload;

  /// Navbat elementini yaratadi.
  const QueuedSubmission({
    required this.idempotencyKey,
    required this.sessionId,
    required this.payload,
  });
}

/// Navbatdagi bitta topshiriqni Backend'ga yuboruvchi funksiya abstraksiyasi.
///
/// Implementatsiya (20.x/repository qatlamida) `ApiClient` orqali
/// `POST /tests/{id}/submit` ni `idempotencyKey` bilan chaqiradi.
///  - Muvaffaqiyatda (200, yoki 409 idempotent takror) — `true` qaytaradi
///    (element navbatdan o'chiriladi).
///  - Tarmoq/server xatosida — `false` qaytaradi yoki exception tashlaydi
///    (element navbatda qoladi, keyin qayta urinish uchun).
typedef SubmissionSender = Future<bool> Function(QueuedSubmission submission);

/// Offline sinxronizatsiya navbati ustidagi amallar shartnomasi (R19.4).
///
/// Konkret implementatsiya — [DriftSyncQueue].
abstract interface class SyncQueue {
  /// Offline topshirilgan natijani navbatga qo'shadi.
  ///
  /// IDEMPOTENT: bir xil [QueuedSubmission.idempotencyKey] ikkinchi marta
  /// qo'shilsa, dublikat yaratilmaydi (Property 48).
  Future<void> enqueue(QueuedSubmission submission);

  /// Navbatdagi barcha kutilayotgan elementlarni FIFO tartibida qaytaradi.
  Future<List<QueuedSubmission>> pending();

  /// Navbatni [sender] orqali Backend'ga yuboradi.
  ///
  /// Har bir element uchun [sender] chaqiriladi; `true` qaytarsa element
  /// navbatdan O'CHIRILADI, aks holda QOLDIRILADI (keyin qayta urinish uchun).
  /// Qayta-qayta chaqirilishi xavfsiz (idempotent to'liqlik — Property 48).
  /// Yuborilgan elementlar soni qaytariladi.
  Future<int> flush(SubmissionSender sender);
}

/// `SyncQueue` ning Drift/SQLite asosidagi implementatsiyasi (R19.4).
class DriftSyncQueue implements SyncQueue {
  /// Ichki Drift bazasi.
  final AppDatabase _db;

  /// Berilgan [AppDatabase] bilan navbat repozitoriysini yaratadi.
  ///
  /// Testlarda xotiradagi baza uzatiladi:
  /// `DriftSyncQueue(AppDatabase(NativeDatabase.memory()))`.
  DriftSyncQueue(this._db);

  @override
  Future<void> enqueue(QueuedSubmission submission) async {
    // `idempotencyKey` UNIQUE bo'lgani uchun `insertOrIgnore` bir xil kalitni
    // ikkinchi marta yozmaydi — bu idempotentlikni ta'minlaydi (Property 48).
    await _db.into(_db.syncQueueEntries).insert(
          SyncQueueEntriesCompanion.insert(
            idempotencyKey: submission.idempotencyKey,
            sessionId: submission.sessionId,
            payload: jsonEncode(submission.payload),
            createdAt: DateTime.now().toUtc(),
          ),
          mode: InsertMode.insertOrIgnore,
        );
  }

  @override
  Future<List<QueuedSubmission>> pending() async {
    final query = _db.select(_db.syncQueueEntries)
      ..orderBy([(e) => OrderingTerm(expression: e.createdAt)]);
    final rows = await query.get();
    return rows.map(_toSubmission).toList();
  }

  @override
  Future<int> flush(SubmissionSender sender) async {
    final entries = await (_db.select(_db.syncQueueEntries)
          ..orderBy([(e) => OrderingTerm(expression: e.createdAt)]))
        .get();

    var sentCount = 0;
    for (final entry in entries) {
      final submission = _toSubmission(entry);
      var success = false;
      try {
        success = await sender(submission);
      } catch (_) {
        // Tarmoq/server xatosi — element navbatda qoladi, urinishlar sonini
        // oshiramiz (exponential backoff uchun — TODO 20.x).
        success = false;
      }

      if (success) {
        // Faqat muvaffaqiyatli yuborilgan elementni o'chiramiz.
        await (_db.delete(_db.syncQueueEntries)
              ..where((e) => e.id.equals(entry.id)))
            .go();
        sentCount++;
      } else {
        await (_db.update(_db.syncQueueEntries)
              ..where((e) => e.id.equals(entry.id)))
            .write(
          SyncQueueEntriesCompanion(
            attemptCount: Value(entry.attemptCount + 1),
          ),
        );
      }
    }
    return sentCount;
  }

  /// Drift satr (data) klassini domen modeliga aylantiradi.
  QueuedSubmission _toSubmission(SyncQueueEntry entry) {
    return QueuedSubmission(
      idempotencyKey: entry.idempotencyKey,
      sessionId: entry.sessionId,
      payload: Map<String, dynamic>.from(jsonDecode(entry.payload) as Map),
    );
  }
}
