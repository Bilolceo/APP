import 'package:dio/dio.dart';

import '../../core/app_constants.dart';
import '../models/api_error.dart';
import 'auth_events.dart';
import 'auth_interceptor.dart';
import 'token_store.dart';

/// REST API bilan ishlovchi HTTP mijoz (Dio asosida) — R2.3, R20.1–R20.4.
///
/// `ApiClient` ma'lumot qatlamining markaziy HTTP nuqtasi:
///  - `baseUrl` = backend bazasi + `/api/v1` ([AppConstants.apiRoot]).
///  - [AuthInterceptor] orqali har so'rovga `Authorization: Bearer` qo'shadi va
///    401'da refresh -> qayta urinish -> (muvaffaqiyatsizda) login'ga
///    yo'naltirish oqimini boshqaradi (R2.3).
///  - Backendning yagona tuzilgan xato formatini (`{"error": {...}}`) tipli
///    [ApiException] ga keltiradi (R20.6), shunda chaqiruvchilar xatoni tipli
///    boshqaradi.
///
/// Mijoz prezentatsiya qatlamiga bog'lanmaydi: login'ga yo'naltirish faqat
/// [authEvents] oqimi orqali signal qilinadi (teskari bog'liqlik yo'q).
class ApiClient {
  /// Ichki Dio instansiyasi (interseptorlar bilan).
  final Dio _dio;

  /// Login'ga yo'naltirish hodisalari kanali (UI shu yerni tinglaydi).
  final AuthEvents authEvents;

  /// Tokenlarni o'qish/saqlash abstraksiyasi.
  final TokenStore tokenStore;

  ApiClient._({
    required Dio dio,
    required this.authEvents,
    required this.tokenStore,
  }) : _dio = dio;

  /// Standart konfiguratsiyali `ApiClient` quradi.
  ///
  /// [tokenStore] — token xotirasi (standart: [SecureTokenStore]).
  /// [authEvents] — login hodisalari kanali (standart: yangi [AuthEvents]).
  /// [baseUrl] — API ildiz manzili (standart: [AppConstants.apiRoot]).
  factory ApiClient({
    TokenStore? tokenStore,
    AuthEvents? authEvents,
    String? baseUrl,
    Dio? refreshDio,
  }) {
    final store = tokenStore ?? SecureTokenStore();
    final events = authEvents ?? AuthEvents();
    final resolvedBaseUrl = baseUrl ?? AppConstants.apiRoot;

    final options = BaseOptions(
      baseUrl: resolvedBaseUrl,
      connectTimeout:
          const Duration(milliseconds: AppConstants.requestTimeoutMs),
      receiveTimeout:
          const Duration(milliseconds: AppConstants.requestTimeoutMs),
      sendTimeout: const Duration(milliseconds: AppConstants.requestTimeoutMs),
      headers: const {'Content-Type': 'application/json'},
      // Status kodlarini o'zimiz (interseptorda/keltirishda) boshqaramiz.
      responseType: ResponseType.json,
    );

    final dio = Dio(options);
    // Refresh so'rovi uchun mustaqil (interseptorsiz) mijoz — rekursiyani
    // oldini oladi (refresh ham 401 bersa, qayta refresh boshlanmaydi).
    final internalRefreshDio = refreshDio ?? Dio(options);

    dio.interceptors.add(
      AuthInterceptor(
        tokenStore: store,
        authEvents: events,
        refreshDio: internalRefreshDio,
        retryDio: dio,
      ),
    );

    return ApiClient._(dio: dio, authEvents: events, tokenStore: store);
  }

  /// Test/maxsus holatlar uchun tashqaridan tayyorlangan [dio] bilan quradi.
  factory ApiClient.withDio({
    required Dio dio,
    required TokenStore tokenStore,
    required AuthEvents authEvents,
  }) {
    return ApiClient._(dio: dio, authEvents: authEvents, tokenStore: tokenStore);
  }

  /// Tashqi qatlamlar uchun ochiq Dio instansiyasi (domen mijozlari ishlatadi).
  Dio get dio => _dio;

  // -------------------------------------------------------------------------
  // Umumiy so'rov yordamchilari — xatolarni ApiException ga keltiradi (R20.6).
  // -------------------------------------------------------------------------

  /// GET so'rovini yuboradi va javob tanasini [parse] orqali `T` ga keltiradi.
  Future<T> getJson<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    required T Function(dynamic data) parse,
  }) {
    return _request<T>(
      () => _dio.get<dynamic>(path, queryParameters: queryParameters),
      parse,
    );
  }

  /// POST so'rovini yuboradi va javob tanasini [parse] orqali `T` ga keltiradi.
  Future<T> postJson<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
    required T Function(dynamic data) parse,
  }) {
    return _request<T>(
      () => _dio.post<dynamic>(
        path,
        data: data,
        queryParameters: queryParameters,
      ),
      parse,
    );
  }

  /// PATCH so'rovini yuboradi va javob tanasini [parse] orqali `T` ga keltiradi.
  Future<T> patchJson<T>(
    String path, {
    Object? data,
    required T Function(dynamic data) parse,
  }) {
    return _request<T>(
      () => _dio.patch<dynamic>(path, data: data),
      parse,
    );
  }

  /// DELETE so'rovini yuboradi va javob tanasini [parse] orqali `T` ga keltiradi.
  Future<T> deleteJson<T>(
    String path, {
    Object? data,
    required T Function(dynamic data) parse,
  }) {
    return _request<T>(
      () => _dio.delete<dynamic>(path, data: data),
      parse,
    );
  }

  /// Multipart (fayl yuklash) POST so'rovini yuboradi (R11.2).
  Future<T> postMultipart<T>(
    String path, {
    required FormData formData,
    required T Function(dynamic data) parse,
  }) {
    return _request<T>(
      () => _dio.post<dynamic>(
        path,
        data: formData,
        options: Options(contentType: 'multipart/form-data'),
      ),
      parse,
    );
  }

  /// So'rovni bajaradi, javobni [parse] qiladi va xatolarni [ApiException] ga
  /// keltiradi (R20.6).
  Future<T> _request<T>(
    Future<Response<dynamic>> Function() send,
    T Function(dynamic data) parse,
  ) async {
    try {
      final response = await send();
      return parse(response.data);
    } on DioException catch (e) {
      throw mapDioException(e);
    }
  }

  /// `DioException` ni tipli [ApiException] ga keltiradi (R20.6).
  ///
  /// Backendning tuzilgan xato tanasi (`{"error": {...}}`) bo'lsa undan
  /// `code`/`message`/`details` olinadi; aks holda tarmoq/noma'lum xatoga
  /// keltiriladi.
  static ApiException mapDioException(DioException e) {
    final response = e.response;
    final statusCode = response?.statusCode;
    final data = response?.data;

    if (data is Map && data['error'] is Map) {
      final apiError = ApiError.fromJson(Map<String, dynamic>.from(data));
      return ApiException.fromApiError(apiError, statusCode: statusCode);
    }

    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.connectionError:
        return ApiException.network();
      case DioExceptionType.badResponse:
        if (statusCode == 401) {
          return ApiException.unauthorized();
        }
        return ApiException.unknown(
          message: 'Server xatosi (HTTP $statusCode)',
          statusCode: statusCode,
        );
      case DioExceptionType.cancel:
        return const ApiException(
          code: 'cancelled',
          message: 'So\'rov bekor qilindi',
        );
      case DioExceptionType.badCertificate:
        return const ApiException(
          code: 'bad_certificate',
          message: 'Xavfsizlik sertifikati yaroqsiz',
        );
      case DioExceptionType.unknown:
        return ApiException.unknown(message: e.message, statusCode: statusCode);
    }
  }
}
