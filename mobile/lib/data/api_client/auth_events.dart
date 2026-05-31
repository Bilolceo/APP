import 'dart:async';

/// Autentifikatsiya hodisalari (R2.3, R2.5).
///
/// `ApiClient` ma'lumot qatlamida joylashgan va prezentatsiya (UI) qatlamiga
/// to'g'ridan-to'g'ri bog'lanmasligi kerak. Token yangilash muvaffaqiyatsiz
/// bo'lganda (refresh ishlamadi yoki refresh token yo'q) mijoz "login'ga
/// yo'naltirish" hodisasini shu yerda e'lon qiladi; prezentatsiya qatlami
/// ([stream]ni tinglab) login ekraniga o'tadi.
///
/// Bu yo'l ma'lumot qatlamini mustaqil (UI'dan xabarsiz) saqlaydi — bog'lanish
/// faqat oddiy `Stream` orqali (teskari bog'liqlik yo'q).
class AuthEvents {
  final StreamController<AuthEvent> _controller =
      StreamController<AuthEvent>.broadcast();

  /// Autentifikatsiya hodisalari oqimi (UI shu yerni tinglaydi).
  Stream<AuthEvent> get stream => _controller.stream;

  /// "Login'ga yo'naltirish" hodisasini e'lon qiladi (R2.3 muvaffaqiyatsiz).
  void emitUnauthorized() {
    if (!_controller.isClosed) {
      _controller.add(AuthEvent.unauthorized);
    }
  }

  /// Resurslarni bo'shatadi (ilova yopilganda).
  Future<void> dispose() => _controller.close();
}

/// Autentifikatsiya hodisasi turlari.
enum AuthEvent {
  /// Sessiya yaroqsiz — foydalanuvchini qayta login qilishga yo'naltirish kerak.
  unauthorized,
}
