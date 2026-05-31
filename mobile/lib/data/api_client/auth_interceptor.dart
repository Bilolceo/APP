import 'dart:async';

import 'package:dio/dio.dart';

import '../models/auth_models.dart';
import 'auth_events.dart';
import 'token_store.dart';

/// JWT autentifikatsiya interseptori (R2.3, R2.5, R20.x).
///
/// Mas'uliyatlari:
///  1. Har bir so'rovga `Authorization: Bearer <access_token>` qo'shadi (token
///     mavjud bo'lsa). Auth oqimining ochiq endpointlari (login/register/
///     refresh/forgot/reset) bundan mustasno — ularga token qo'shilmaydi.
///  2. 401 javobida refresh oqimini bajaradi: `POST /auth/refresh` orqali yangi
///     access token oladi, saqlaydi va asl so'rovni **bir marta** qayta yuboradi
///     (R2.3).
///  3. Refresh muvaffaqiyatsiz bo'lsa (yoki refresh token yo'q) — tokenlarni
///     tozalaydi va [AuthEvents] orqali "login'ga yo'naltirish" hodisasini
///     e'lon qiladi (R2.6). Prezentatsiya qatlami bu hodisani tinglaydi.
///
/// Bir vaqtda kelgan bir nechta 401 uchun refresh **bitta marta** bajariladi:
/// davom etayotgan refresh `Future` bo'lsa, qolgan so'rovlar uni kutadi
/// (refresh "bo'roni" oldini olinadi).
class AuthInterceptor extends Interceptor {
  /// Tokenlarni o'qish/saqlash uchun xotira abstraksiyasi.
  final TokenStore tokenStore;

  /// Login'ga yo'naltirish hodisalarini e'lon qiluvchi kanal.
  final AuthEvents authEvents;

  /// Refresh so'rovini yuborish uchun interseptorsiz Dio (rekursiyani oldini oladi).
  final Dio _refreshDio;

  /// Asl so'rovni qayta yuborish uchun asosiy Dio (interseptorli).
  final Dio _retryDio;

  /// Belgilangan so'rov interseptordan o'tib ketganini bildiruvchi ekstra kalit.
  static const String _retriedKey = '__auth_retried__';

  /// Refresh oqimi davom etayotganini ifodalovchi `Future` (lock vazifasi).
  Future<bool>? _refreshing;

  /// Interseptorni yaratadi.
  ///
  /// [refreshDio] — refresh so'rovi uchun mustaqil (interseptorsiz) mijoz;
  /// [retryDio] — 401 dan keyin asl so'rovni qayta yuboruvchi asosiy mijoz.
  AuthInterceptor({
    required this.tokenStore,
    required this.authEvents,
    required Dio refreshDio,
    required Dio retryDio,
  })  : _refreshDio = refreshDio,
        _retryDio = retryDio;

  /// Token qo'shilmaydigan ochiq (auth) endpointlar.
  static const Set<String> _publicPaths = {
    '/auth/login',
    '/auth/register',
    '/auth/refresh',
    '/auth/forgot-password',
    '/auth/reset-password',
  };

  bool _isPublicPath(String path) {
    return _publicPaths.any((p) => path.endsWith(p));
  }

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    // Ochiq endpointlarga token qo'shilmaydi (login/register/refresh va h.k.).
    if (!_isPublicPath(options.path)) {
      final accessToken = await tokenStore.readAccessToken();
      if (accessToken != null && accessToken.isNotEmpty) {
        options.headers['Authorization'] = 'Bearer $accessToken';
      }
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final response = err.response;
    final requestOptions = err.requestOptions;

    final isUnauthorized = response?.statusCode == 401;
    final alreadyRetried = requestOptions.extra[_retriedKey] == true;
    final isPublic = _isPublicPath(requestOptions.path);

    // Faqat 401, faqat himoyalangan endpoint va faqat bir marta qayta urinamiz.
    if (!isUnauthorized || alreadyRetried || isPublic) {
      handler.next(err);
      return;
    }

    final refreshed = await _ensureRefreshed();
    if (!refreshed) {
      // Refresh muvaffaqiyatsiz — tokenlar tozalandi va login hodisasi e'lon
      // qilindi (_ensureRefreshed ichida). Asl xatoni tarqatamiz.
      handler.next(err);
      return;
    }

    // Yangi access token bilan asl so'rovni bir marta qayta yuboramiz (R2.3).
    try {
      final newAccessToken = await tokenStore.readAccessToken();
      final retryOptions = _cloneForRetry(requestOptions, newAccessToken);
      final retryResponse = await _retryDio.fetch<dynamic>(retryOptions);
      handler.resolve(retryResponse);
    } on DioException catch (retryError) {
      handler.next(retryError);
    }
  }

  /// Asl so'rov opsiyalarini qayta yuborish uchun nusxalaydi (yangi token bilan).
  RequestOptions _cloneForRetry(RequestOptions original, String? accessToken) {
    final headers = Map<String, dynamic>.from(original.headers);
    if (accessToken != null && accessToken.isNotEmpty) {
      headers['Authorization'] = 'Bearer $accessToken';
    }
    final extra = Map<String, dynamic>.from(original.extra)
      ..[_retriedKey] = true;
    original.headers
      ..clear()
      ..addAll(headers);
    original.extra
      ..clear()
      ..addAll(extra);
    return original;
  }

  /// Refresh oqimini (kerak bo'lsa) bajaradi va natijani qaytaradi.
  ///
  /// Bir vaqtda kelgan so'rovlar yagona davom etayotgan refresh `Future` ni
  /// kutadi — shu tarzda refresh faqat bir marta amalga oshiriladi.
  Future<bool> _ensureRefreshed() {
    final inFlight = _refreshing;
    if (inFlight != null) return inFlight;

    final future = _performRefresh();
    _refreshing = future;
    // Tugagach lockni bo'shatamiz.
    return future.whenComplete(() => _refreshing = null);
  }

  /// Refresh tokeni bilan yangi access token oladi va saqlaydi (R2.3).
  ///
  /// Muvaffaqiyatda `true`; refresh token yo'q yoki yangilash rad etilsa,
  /// tokenlarni tozalaydi, login hodisasini e'lon qiladi va `false` qaytaradi.
  Future<bool> _performRefresh() async {
    final refreshToken = await tokenStore.readRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) {
      await _failAndSignal();
      return false;
    }

    try {
      final response = await _refreshDio.post<dynamic>(
        '/auth/refresh',
        data: RefreshRequest(refreshToken: refreshToken).toJson(),
      );
      final data = response.data;
      if (data is! Map) {
        await _failAndSignal();
        return false;
      }
      final tokenResponse =
          AccessTokenResponse.fromJson(Map<String, dynamic>.from(data));
      if (tokenResponse.accessToken.isEmpty) {
        await _failAndSignal();
        return false;
      }
      // Backend refresh javobida faqat yangi access token qaytaradi (R2.3) —
      // refresh token o'zgarmaydi, shuning uchun faqat access yangilanadi.
      await tokenStore.updateAccessToken(tokenResponse.accessToken);
      return true;
    } on DioException {
      await _failAndSignal();
      return false;
    }
  }

  /// Tokenlarni tozalaydi va login'ga yo'naltirish hodisasini e'lon qiladi.
  Future<void> _failAndSignal() async {
    await tokenStore.clear();
    authEvents.emitUnauthorized();
  }
}
