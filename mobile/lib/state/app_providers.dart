import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/app_constants.dart';
import '../data/api_client/analytics_api.dart';
import '../data/api_client/api_client.dart';
import '../data/api_client/auth_api.dart';
import '../data/api_client/auth_events.dart';
import '../data/api_client/devices_api.dart';
import '../data/api_client/portfolio_api.dart';
import '../data/api_client/rating_api.dart';
import '../data/api_client/recommendations_api.dart';
import '../data/api_client/tests_api.dart';
import '../data/api_client/token_store.dart';
import '../data/api_client/users_api.dart';
import '../data/local_cache/app_database.dart';
import '../data/local_cache/local_cache.dart';
import '../data/sync_queue/sync_queue.dart';
import '../services/push_notifications_service.dart';
import 'auth_state.dart';

/// Ilova bo'ylab Riverpod provider'lari (state management — R19.2).
///
/// Bu yerda ma'lumot qatlamining (ApiClient + domen mijozlari + token xotirasi)
/// provider'lari e'lon qilinadi. Ekran-darajali ViewModel/Notifier'lar
/// (auth holati, testlar va h.k.) shu provider'lar ustiga quriladi.

/// Tokenlarni xavfsiz saqlash abstraksiyasini (`TokenStore`) ta'minlaydi (R17).
///
/// Standart implementatsiya — `flutter_secure_storage` ga tayanuvchi
/// [SecureTokenStore]. Testlarda override qilib [InMemoryTokenStore] berish
/// mumkin.
final tokenStoreProvider = Provider<TokenStore>((ref) {
  return SecureTokenStore();
});

/// Login'ga yo'naltirish hodisalari kanalini (`AuthEvents`) ta'minlaydi (R2.3).
///
/// Prezentatsiya qatlami `stream` ni tinglab, sessiya yaroqsiz bo'lganda login
/// ekraniga o'tadi.
final authEventsProvider = Provider<AuthEvents>((ref) {
  final events = AuthEvents();
  ref.onDispose(events.dispose);
  return events;
});

/// Interceptor'lar bilan to'liq sozlangan `ApiClient` ni ta'minlaydi (R2.3).
final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(
    tokenStore: ref.watch(tokenStoreProvider),
    authEvents: ref.watch(authEventsProvider),
    baseUrl: AppConstants.apiRoot,
  );
});

/// Autentifikatsiya domeni mijozini ta'minlaydi (R1, R2, R3).
final authApiProvider = Provider<AuthApi>((ref) {
  return AuthApi(ref.watch(apiClientProvider));
});

/// Foydalanuvchi / profil domeni mijozini ta'minlaydi (R5, R4).
final usersApiProvider = Provider<UsersApi>((ref) {
  return UsersApi(ref.watch(apiClientProvider));
});

/// Test, sessiya va natija domeni mijozini ta'minlaydi (R6, R7, R8).
final testsApiProvider = Provider<TestsApi>((ref) {
  return TestsApi(ref.watch(apiClientProvider));
});

/// Tavsiyalar domeni mijozini ta'minlaydi (R10).
final recommendationsApiProvider = Provider<RecommendationsApi>((ref) {
  return RecommendationsApi(ref.watch(apiClientProvider));
});

/// Portfolio domeni mijozini ta'minlaydi (R11).
final portfolioApiProvider = Provider<PortfolioApi>((ref) {
  return PortfolioApi(ref.watch(apiClientProvider));
});

/// Analitika domeni mijozini ta'minlaydi (R9, R15).
final analyticsApiProvider = Provider<AnalyticsApi>((ref) {
  return AnalyticsApi(ref.watch(apiClientProvider));
});

/// Reyting domeni mijozini ta'minlaydi (R12).
final ratingApiProvider = Provider<RatingApi>((ref) {
  return RatingApi(ref.watch(apiClientProvider));
});

/// Qurilma tokeni (push) domeni mijozini ta'minlaydi (R16).
final devicesApiProvider = Provider<DevicesApi>((ref) {
  return DevicesApi(ref.watch(apiClientProvider));
});

/// Push bildirishnomalar (FCM) bilan ishlovchi servis provider'i (20.3).
///
/// Bu servis auth holati `authenticated` bo'lganda tokenni backendga
/// ro'yxatdan o'tkazish va token yangilanganda qayta yuborishni boshqaradi.
final pushNotificationsServiceProvider = Provider<PushNotificationsService>((ref) {
  final service = PushNotificationsService(
    devicesApi: ref.watch(devicesApiProvider),
  );
  ref.onDispose(() {
    // dispose Future qaytarsa ham bu yerdan kutmasdan best-effort yopamiz.
    service.dispose();
  });
  return service;
});

/// Ilova nomini ta'minlovchi oddiy namunaviy provider (skeleton namunasi).
final appNameProvider = Provider<String>((ref) {
  return AppConstants.appName;
});

// =============================================================================
// Global autentifikatsiya holati (token, rol, profil) — R1.1, R2.1, R5.1, R19.2
// =============================================================================

/// Butun ilova bo'ylab autentifikatsiya holatini boshqaruvchi provider (20.1).
///
/// [AuthNotifier] startda token mavjudligini tekshiradi (`bootstrap`), login /
/// register / logout amallarini bajaradi va `authEventsProvider` orqali kelgan
/// `AuthEvent.unauthorized` hodisasida majburiy logout qiladi (R2.3). UI shu
/// provider holatiga qarab splash → login → home oqimini ko'rsatadi.
final authStateProvider =
    StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(
    authApi: ref.watch(authApiProvider),
    usersApi: ref.watch(usersApiProvider),
    tokenStore: ref.watch(tokenStoreProvider),
    authEvents: ref.watch(authEventsProvider),
  );
});

// =============================================================================
// Offline kesh va sinxronizatsiya navbati provider'lari (R19.3, R19.4 — 19.3)
// =============================================================================
// Eslatma: bu provider'lar Drift kod generatsiyasiga tayanadi
// (`dart run build_runner build --delete-conflicting-outputs`).

/// Offline kesh + sinxronizatsiya navbati uchun yagona Drift bazasi (R19.3, R19.4).
///
/// [AppDatabase] butun ilova bo'ylab bitta nusxada yashaydi (SQLite ulanishi
/// qimmat). Provider tashlanganda (dispose) baza ulanishi yopiladi.
final appDatabaseProvider = Provider<AppDatabase>((ref) {
  final db = AppDatabase();
  ref.onDispose(db.close);
  return db;
});

/// Yuklab olingan testlar/savollarni offline keshlovchi repozitoriy (R19.3).
///
/// [DriftLocalCache] yagona [appDatabaseProvider] bazasiga tayanadi.
final localCacheProvider = Provider<LocalCache>((ref) {
  return DriftLocalCache(ref.watch(appDatabaseProvider));
});

/// Offline topshirilgan natijalar uchun sinxronizatsiya navbati (R19.4).
///
/// [DriftSyncQueue] yagona [appDatabaseProvider] bazasiga tayanadi.
/// TODO(20.x): ulanish tiklanganda (connectivity-restore) `flush` ni
/// triggerlovchi listener'ni shu provider ustiga ulang.
final syncQueueProvider = Provider<SyncQueue>((ref) {
  return DriftSyncQueue(ref.watch(appDatabaseProvider));
});
