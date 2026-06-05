/// Ilova bo'ylab ishlatiladigan o'zgarmas (constant) qiymatlar.
///
/// Bu yerda API manzili, ilova nomi va boshqa global sozlamalar saqlanadi.
/// Haqiqiy qiymatlar (masalan, prod API URL) keyinchalik muhit (env) orqali
/// almashtirilishi mumkin.

/// Ilovaning markaziy konstantalari.
class AppConstants {
  const AppConstants._();

  /// Ilova nomi (o'zbekcha) — AppBar va boshqa joylarda ko'rsatiladi.
  static const String appName = 'MTT Menejer Diagnostika';

  /// Backend REST API'ning bazaviy manzili.
  ///
  /// `API_BASE_URL` `--dart-define` orqali berilsa o'sha qiymat ishlatiladi.
  /// Berilmasa Android emulator uchun standart `10.0.2.2` qoldiriladi.
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  /// REST API versiya prefiksi (backend bilan mos: `/api/v1`).
  static const String apiVersionPrefix = '/api/v1';

  /// To'liq API ildiz manzili.
  static String get apiRoot => '$apiBaseUrl$apiVersionPrefix';

  /// Xavfsiz xotirada access token uchun kalit (TODO 19.2).
  static const String accessTokenKey = 'access_token';

  /// Xavfsiz xotirada refresh token uchun kalit (TODO 19.2).
  static const String refreshTokenKey = 'refresh_token';

  /// So'rovlar uchun standart taym-aut (millisekund).
  static const int requestTimeoutMs = 30000;

  /// Property-based testlar uchun minimal iteratsiyalar soni (>=100).
  static const int pbtMinIterations = 100;
}
