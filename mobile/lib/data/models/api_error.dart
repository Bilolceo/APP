import 'json_utils.dart';

/// Backend xato tafsilotidagi bitta yozuv: `{ "field", "reason" }`.
///
/// Backend yagona tuzilgan xato formatida `details` ro'yxatini qaytaradi
/// (R20.6): `{"field": "phone", "reason": "..."}`. Ushbu model shu yozuvni
/// ifodalaydi.
class ApiErrorDetail {
  /// Xatoga sabab bo'lgan maydon nomi (mavjud bo'lsa).
  final String? field;

  /// Inson o'qiy oladigan sabab matni.
  final String? reason;

  /// [field] va [reason] dan tafsilot yaratadi.
  const ApiErrorDetail({this.field, this.reason});

  /// JSON xaritadan [ApiErrorDetail] yaratadi.
  factory ApiErrorDetail.fromJson(Map<String, dynamic> json) {
    return ApiErrorDetail(
      field: JsonParse.asStringOrNull(json['field']),
      reason: JsonParse.asStringOrNull(json['reason']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {'field': field, 'reason': reason};

  @override
  String toString() => field == null ? '$reason' : '$field: $reason';
}

/// Backendning yagona tuzilgan xato tanasi (R20.6).
///
/// Format:
/// ```json
/// { "error": { "code": "validation_error",
///              "message": "...",
///              "details": [ { "field": "phone", "reason": "..." } ] } }
/// ```
class ApiError {
  /// Barqaror, mashina-o'qiy xato kodi (masalan `validation_error`).
  final String code;

  /// Foydalanuvchiga ko'rsatish mumkin bo'lgan xato xabari.
  final String message;

  /// Maydon-darajali tafsilotlar (bo'sh bo'lishi mumkin).
  final List<ApiErrorDetail> details;

  /// [code], [message] va [details] dan xato yaratadi.
  const ApiError({
    required this.code,
    required this.message,
    this.details = const [],
  });

  /// Backend `{"error": {...}}` tanasidan [ApiError] yaratadi.
  ///
  /// Berilgan [json] to'g'ridan-to'g'ri `error` obyekti yoki uni o'rab turgan
  /// tashqi obyekt bo'lishi mumkin — ikkala holat ham qo'llab-quvvatlanadi.
  factory ApiError.fromJson(Map<String, dynamic> json) {
    final error = json.containsKey('error')
        ? JsonParse.asMap(json['error'])
        : json;
    return ApiError(
      code: JsonParse.asString(error['code'], fallback: 'unknown_error'),
      message: JsonParse.asString(
        error['message'],
        fallback: 'Nomaʼlum xatolik yuz berdi',
      ),
      details: JsonParse.asList(error['details'], ApiErrorDetail.fromJson),
    );
  }

  /// JSON xaritaga (`{"error": {...}}`) aylantiradi.
  Map<String, dynamic> toJson() => {
        'error': {
          'code': code,
          'message': message,
          'details': details.map((d) => d.toJson()).toList(growable: false),
        }
      };

  @override
  String toString() => 'ApiError(code: $code, message: $message)';
}

/// API qatlami tomonidan ko'tariladigan tipli istisno.
///
/// `ApiClient` Dio xatolarini (`DioException`) va backendning tuzilgan xato
/// javobini shu istisnoga keltiradi, shunda chaqiruvchi qatlamlar (repository /
/// state) xatoni tipli ([code]/[message]/[details]) tarzda boshqaradi.
class ApiException implements Exception {
  /// Mashina-o'qiy xato kodi (masalan `validation_error`, `not_found`).
  final String code;

  /// Foydalanuvchiga ko'rsatish mumkin bo'lgan xabar.
  final String message;

  /// Maydon-darajali tafsilotlar.
  final List<ApiErrorDetail> details;

  /// HTTP holat kodi (mavjud bo'lsa).
  final int? statusCode;

  /// [code], [message], ixtiyoriy [details] va [statusCode] dan yaratadi.
  const ApiException({
    required this.code,
    required this.message,
    this.details = const [],
    this.statusCode,
  });

  /// [ApiError] va ixtiyoriy [statusCode] dan istisno yaratadi.
  factory ApiException.fromApiError(ApiError error, {int? statusCode}) {
    return ApiException(
      code: error.code,
      message: error.message,
      details: error.details,
      statusCode: statusCode,
    );
  }

  /// Tarmoq (ulanish/taym-aut) xatosi uchun istisno.
  factory ApiException.network({String? message}) {
    return ApiException(
      code: 'network_error',
      message: message ?? 'Tarmoq xatosi: serverga ulanib bo\'lmadi',
    );
  }

  /// Kutilmagan (noma'lum) xato uchun istisno.
  factory ApiException.unknown({String? message, int? statusCode}) {
    return ApiException(
      code: 'unknown_error',
      message: message ?? 'Nomaʼlum xatolik yuz berdi',
      statusCode: statusCode,
    );
  }

  /// Autentifikatsiya muvaffaqiyatsizligi (401, refresh ham ishlamadi).
  factory ApiException.unauthorized({String? message}) {
    return ApiException(
      code: 'authentication_error',
      message: message ?? 'Avtorizatsiya muddati tugadi, qayta kiring',
      statusCode: 401,
    );
  }

  @override
  String toString() => 'ApiException(code: $code, message: $message'
      '${statusCode != null ? ', status: $statusCode' : ''})';
}
