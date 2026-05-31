/// Ilova marshrut (route) nomlari (20.1).
///
/// Nomli marshrutlar `Navigator` orqali ishlatiladi. Ildiz oqimi (splash →
/// login/onboarding → home) `authStateProvider` holatiga qarab `AuthGate`
/// tomonidan boshqariladi; bu yerdagi nomlar esa oqim ichidagi ekranlar uchun
/// (login ↔ register ↔ forgot/reset, profil ko'rish/tahrirlash, 20.2
/// test/natija/analitika/portfolio).
class AppRoutes {
  const AppRoutes._();

  /// Login ekrani.
  static const String login = '/login';

  /// Ro'yxatdan o'tish ekrani.
  static const String register = '/register';

  /// Parolni unutish (kod so'rash) ekrani.
  static const String forgotPassword = '/forgot-password';

  /// Parolni tiklash (kod + yangi parol) ekrani.
  static const String resetPassword = '/reset-password';

  /// Bosh ekran (dashboard).
  static const String home = '/home';

  /// Profilni ko'rish ekrani.
  static const String profile = '/profile';

  /// Profilni tahrirlash ekrani.
  static const String profileEdit = '/profile/edit';

  /// Testlar ro'yxati ekrani.
  static const String tests = '/tests';

  /// Test topshirish ekrani (`arguments`: `int testId`).
  static const String testTaking = '/tests/taking';

  /// Foydalanuvchi natijalari ro'yxati ekrani.
  static const String results = '/results';

  /// Natija tafsiloti ekrani (`arguments`: `int resultId`).
  static const String resultDetail = '/results/detail';

  /// Analitika ekrani.
  static const String analytics = '/analytics';

  /// Portfolio ekrani.
  static const String portfolio = '/portfolio';
}
