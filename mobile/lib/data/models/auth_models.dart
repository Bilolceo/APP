import 'json_utils.dart';

/// Autentifikatsiya so'rov/javob DTO modellari (R1, R2, R3).
///
/// Maydon nomlari va JSON kalitlari backend `app/api/schemas/auth.py` bilan
/// aniq mos keladi (snake_case JSON <-> camelCase Dart).

/// Login javobi — access + refresh token juftligi (R2.1).
///
/// Backend: `TokenPairResponse` (`access_token`, `refresh_token`,
/// `token_type`, `expires_in`).
class AuthTokens {
  /// Qisqa muddatli kirish tokeni (access, ~15 daqiqa).
  final String accessToken;

  /// Uzoq muddatli yangilash tokeni (refresh, ~30 kun).
  final String refreshToken;

  /// Token turi (odatda `bearer`).
  final String tokenType;

  /// Access token amal muddati (soniya).
  final int expiresIn;

  /// Token juftligini yaratadi.
  const AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    this.tokenType = 'bearer',
    this.expiresIn = 0,
  });

  /// JSON xaritadan [AuthTokens] yaratadi.
  factory AuthTokens.fromJson(Map<String, dynamic> json) {
    return AuthTokens(
      accessToken: JsonParse.asString(json['access_token']),
      refreshToken: JsonParse.asString(json['refresh_token']),
      tokenType: JsonParse.asString(json['token_type'], fallback: 'bearer'),
      expiresIn: JsonParse.asInt(json['expires_in']),
    );
  }

  /// [AuthTokens] ni JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'access_token': accessToken,
        'refresh_token': refreshToken,
        'token_type': tokenType,
        'expires_in': expiresIn,
      };

  /// Berilgan maydonlar bilan nusxa qaytaradi.
  AuthTokens copyWith({
    String? accessToken,
    String? refreshToken,
    String? tokenType,
    int? expiresIn,
  }) {
    return AuthTokens(
      accessToken: accessToken ?? this.accessToken,
      refreshToken: refreshToken ?? this.refreshToken,
      tokenType: tokenType ?? this.tokenType,
      expiresIn: expiresIn ?? this.expiresIn,
    );
  }
}

/// Refresh javobi — faqat yangi access token (R2.3).
///
/// Backend: `AccessTokenResponse` (`access_token`, `token_type`, `expires_in`).
class AccessTokenResponse {
  /// Yangi JWT kirish tokeni.
  final String accessToken;

  /// Token turi (odatda `bearer`).
  final String tokenType;

  /// Access token amal muddati (soniya).
  final int expiresIn;

  /// Modelni yaratadi.
  const AccessTokenResponse({
    required this.accessToken,
    this.tokenType = 'bearer',
    this.expiresIn = 0,
  });

  /// JSON xaritadan yaratadi.
  factory AccessTokenResponse.fromJson(Map<String, dynamic> json) {
    return AccessTokenResponse(
      accessToken: JsonParse.asString(json['access_token']),
      tokenType: JsonParse.asString(json['token_type'], fallback: 'bearer'),
      expiresIn: JsonParse.asInt(json['expires_in']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'access_token': accessToken,
        'token_type': tokenType,
        'expires_in': expiresIn,
      };
}

/// Ro'yxatdan o'tish so'rovi (R1.1).
///
/// Backend: `RegisterRequest`.
class RegisterRequest {
  /// Telefon raqami (+998, 13 belgi).
  final String phone;

  /// Parol (8–64 belgi).
  final String password;

  /// To'liq ism (1–200 belgi).
  final String fullName;

  /// Rol: Rahbar, Ekspert yoki Administrator.
  final String role;

  /// Tashkilot ID (ixtiyoriy).
  final int? organizationId;

  /// Hudud ID (ixtiyoriy).
  final int? regionId;

  /// Lavozim (ixtiyoriy).
  final String? position;

  /// Ish staji, yil (ixtiyoriy, 0–60).
  final int? experienceYears;

  /// Ta'lim darajasi (ixtiyoriy).
  final String? educationLevel;

  /// Malaka oshirish kurslari (ixtiyoriy).
  final String? qualificationCourses;

  /// Sertifikatlar (ixtiyoriy).
  final String? certificates;

  /// Tashkilot turi (ixtiyoriy).
  final String? orgType;

  /// Ro'yxatdan o'tish so'rovini yaratadi.
  const RegisterRequest({
    required this.phone,
    required this.password,
    required this.fullName,
    required this.role,
    this.organizationId,
    this.regionId,
    this.position,
    this.experienceYears,
    this.educationLevel,
    this.qualificationCourses,
    this.certificates,
    this.orgType,
  });

  /// So'rov tanasi uchun JSON xaritaga aylantiradi.
  ///
  /// `null` ixtiyoriy maydonlar tashlab yuboriladi, shunda backend faqat
  /// berilgan qiymatlarni qabul qiladi.
  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{
      'phone': phone,
      'password': password,
      'full_name': fullName,
      'role': role,
    };
    if (organizationId != null) map['organization_id'] = organizationId;
    if (regionId != null) map['region_id'] = regionId;
    if (position != null) map['position'] = position;
    if (experienceYears != null) map['experience_years'] = experienceYears;
    if (educationLevel != null) map['education_level'] = educationLevel;
    if (qualificationCourses != null) {
      map['qualification_courses'] = qualificationCourses;
    }
    if (certificates != null) map['certificates'] = certificates;
    if (orgType != null) map['org_type'] = orgType;
    return map;
  }
}

/// Tizimga kirish so'rovi (R2.1).
///
/// Backend: `LoginRequest`.
class LoginRequest {
  /// Telefon raqami.
  final String phone;

  /// Parol.
  final String password;

  /// Login so'rovini yaratadi.
  const LoginRequest({required this.phone, required this.password});

  /// So'rov tanasi uchun JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {'phone': phone, 'password': password};
}

/// Token yangilash so'rovi (R2.3).
///
/// Backend: `RefreshRequest`.
class RefreshRequest {
  /// Yangilash (refresh) tokeni.
  final String refreshToken;

  /// Refresh so'rovini yaratadi.
  const RefreshRequest({required this.refreshToken});

  /// So'rov tanasi uchun JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {'refresh_token': refreshToken};
}

/// Tizimdan chiqish so'rovi (R2.4).
///
/// Backend: `LogoutRequest` (`refresh_token` ixtiyoriy).
class LogoutRequest {
  /// Bekor qilinadigan yangilash tokeni (ixtiyoriy).
  final String? refreshToken;

  /// Logout so'rovini yaratadi.
  const LogoutRequest({this.refreshToken});

  /// So'rov tanasi uchun JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        if (refreshToken != null) 'refresh_token': refreshToken,
      };
}

/// Parolni tiklashni boshlash so'rovi (R3.1, R3.2).
///
/// Backend: `ForgotPasswordRequest`.
class ForgotPasswordRequest {
  /// Ro'yxatdan o'tgan telefon raqami.
  final String phone;

  /// So'rovni yaratadi.
  const ForgotPasswordRequest({required this.phone});

  /// So'rov tanasi uchun JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {'phone': phone};
}

/// Tasdiqlash kodi bilan parolni yangilash so'rovi (R3.3–R3.7).
///
/// Backend: `ResetPasswordRequest`.
class ResetPasswordRequest {
  /// Telefon raqami.
  final String phone;

  /// 6 raqamli tasdiqlash kodi.
  final String code;

  /// Yangi parol (>= 8 belgi).
  final String newPassword;

  /// So'rovni yaratadi.
  const ResetPasswordRequest({
    required this.phone,
    required this.code,
    required this.newPassword,
  });

  /// So'rov tanasi uchun JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'phone': phone,
        'code': code,
        'new_password': newPassword,
      };
}

/// Oddiy matnli muvaffaqiyat javobi (logout, parolni tiklash oqimlari).
///
/// Backend: `MessageResponse` (`message`).
class MessageResponse {
  /// Foydalanuvchiga ko'rsatiladigan xabar.
  final String message;

  /// Modelni yaratadi.
  const MessageResponse({required this.message});

  /// JSON xaritadan yaratadi.
  factory MessageResponse.fromJson(Map<String, dynamic> json) {
    return MessageResponse(message: JsonParse.asString(json['message']));
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {'message': message};
}
