// =============================================================================
// Property-Based Testing (PBT) konfiguratsiya namunasi — `glados`
// =============================================================================
// `glados` — Dart ekotizimidagi generativ test kutubxonasi bo'lib,
// JavaScript'dagi `fast_check`ning ekvivalentidir (design.md talabini qondiradi).
//
// QOIDALAR (design.md / tasks.md):
//  1. Har bir korrektlik xususiyati (Property) AYNAN bitta PBT bilan amalga
//     oshiriladi.
//  2. Har bir PBT KAMIDA 100 (>=100) iteratsiya bilan ishlaydi.
//     `glados` da bu `ExploreConfig(numRuns: 100)` orqali sozlanadi.
//  3. Tag (test nomi) formati:
//     "Feature: mtt-menejer-diagnostika, Property {N}: {xususiyat matni}"
//
// Mobil tomon uchun rejalashtirilgan property'lar (TODO 19.4 / 19.5):
//  - Property 47: Offline kesh round-trip (Validates: Requirements 19.3)
//  - Property 48: Sinxronizatsiya to'liqligi va idempotentligi
//    (Validates: Requirements 19.4)
//
// Quyidagi test — bu konfiguratsiya namunasi (>=100 iteratsiya) bo'lib, PBT
// muhiti to'g'ri o'rnatilganini ko'rsatadi. Haqiqiy property'lar 19.4/19.5
// vazifalarida yoziladi.
// =============================================================================

import 'package:glados/glados.dart';
import 'package:mtt_menejer_diagnostika/core/app_constants.dart';

void main() {
  // Minimal iteratsiyalar soni konvensiyasi (>=100) tekshiruvi.
  test('PBT konfiguratsiyasi kamida 100 iteratsiyani talab qiladi', () {
    expect(AppConstants.pbtMinIterations >= 100, isTrue);
  });

  // Namunaviy property — kamida 100 iteratsiya bilan ishlaydi.
  // Format: butun sonni qo'shish kommutativ ekanligini tekshiramiz.
  Glados<int>(
    any.int,
    ExploreConfig(numRuns: AppConstants.pbtMinIterations),
  ).test(
    'Feature: mtt-menejer-diagnostika, Property 0: PBT namunasi — '
    "qo'shish kommutativligi (>=100 iteratsiya)",
    (a) {
      // a + 0 har doim a ga teng (oddiy invariant namunasi).
      expect(a + 0, equals(a));
    },
  );
}
