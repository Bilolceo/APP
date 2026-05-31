/// Backend REST API endpoint yo'llari (R20.1–R20.4).
///
/// Barcha yo'llar `/api/v1` prefiksiga **nisbatan** (relative) — `baseUrl` da
/// prefiks allaqachon mavjud (`AppConstants.apiRoot`). Yo'llar backend
/// routerlari (`app/api/routers/*.py`) bilan aniq mos keladi.

/// API endpoint yo'llari to'plami.
class Endpoints {
  const Endpoints._();

  // Auth (R1, R2, R3) — app/api/routers/auth.py
  static const String register = '/auth/register';
  static const String login = '/auth/login';
  static const String refresh = '/auth/refresh';
  static const String logout = '/auth/logout';
  static const String forgotPassword = '/auth/forgot-password';
  static const String resetPassword = '/auth/reset-password';

  // Users / profil (R5, R4) — app/api/routers/users.py
  static const String usersMe = '/users/me';

  /// Berilgan [userId] bo'yicha foydalanuvchi profili yo'li.
  static String user(int userId) => '/users/$userId';

  // Testlar va natijalar (R6, R7, R8) — app/api/routers/tests.py
  static const String tests = '/tests';
  static const String myResults = '/tests/results/me';

  /// Test tafsiloti yo'li.
  static String test(int testId) => '/tests/$testId';

  /// Sessiya boshlash yo'li.
  static String startTest(int testId) => '/tests/$testId/start';

  /// Sessiya topshirish yo'li.
  static String submitTest(int testId) => '/tests/$testId/submit';

  /// Natija tafsiloti yo'li.
  static String result(int resultId) => '/tests/results/$resultId';

  // Tavsiyalar (R10) — app/api/routers/recommendations.py
  static const String recommendationsMe = '/recommendations/me';

  /// Natija bo'yicha tavsiyalar yo'li.
  static String recommendationsByResult(int resultId) =>
      '/recommendations/by-result/$resultId';

  // Portfolio (R11) — app/api/routers/portfolio.py
  static const String portfolioMe = '/portfolio/me';
  static const String portfolioUpload = '/portfolio/upload';

  /// Portfolio yozuvini o'chirish yo'li.
  static String portfolioItem(int portfolioId) => '/portfolio/$portfolioId';

  // Analitika (R9, R15) — app/api/routers/analytics.py
  static const String analyticsMe = '/analytics/me';

  /// Tashkilot kesimi analitikasi yo'li.
  static String analyticsOrganization(int organizationId) =>
      '/analytics/organization/$organizationId';

  /// Hudud kesimi analitikasi yo'li.
  static String analyticsRegion(int regionId) => '/analytics/region/$regionId';

  // Reyting (R12) — app/api/routers/rating.py
  static const String rating = '/rating';

  // Qurilma tokeni (R16) — app/api/routers/devices.py
  static const String deviceToken = '/devices/token';
}
