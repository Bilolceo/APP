import 'json_utils.dart';

/// Qurilma tokeni (push) DTO modellari (R16).
///
/// Maydon nomlari backend `app/api/schemas/device.py` bilan aniq mos keladi.

/// Qurilma tokenini ro'yxatdan o'tkazish so'rovi (R16.1).
///
/// Backend: `DeviceTokenRegisterRequest`.
class DeviceTokenRequest {
  /// FCM qurilma tokeni.
  final String token;

  /// Platforma (masalan 'android').
  final String? platform;

  /// So'rovni yaratadi.
  const DeviceTokenRequest({required this.token, this.platform});

  /// So'rov tanasi uchun JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'token': token,
        if (platform != null) 'platform': platform,
      };
}

/// Qurilma tokenini bekor qilish so'rovi (R16.6).
///
/// Backend: `DeviceTokenInvalidateRequest`.
class DeviceTokenInvalidateRequest {
  /// Bekor qilinadigan FCM qurilma tokeni.
  final String token;

  /// So'rovni yaratadi.
  const DeviceTokenInvalidateRequest({required this.token});

  /// So'rov tanasi uchun JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {'token': token};
}

/// Qurilma tokeni javobi (R16.1).
///
/// Backend: `DeviceTokenResponse`.
class DeviceTokenResponse {
  /// Qurilma tokeni yozuvi ID.
  final int id;

  /// Egasi (foydalanuvchi) ID.
  final int userId;

  /// Platforma.
  final String? platform;

  /// Token yaroqliligi.
  final bool isValid;

  /// Modelni yaratadi.
  const DeviceTokenResponse({
    required this.id,
    required this.userId,
    this.platform,
    required this.isValid,
  });

  /// JSON xaritadan yaratadi.
  factory DeviceTokenResponse.fromJson(Map<String, dynamic> json) {
    return DeviceTokenResponse(
      id: JsonParse.asInt(json['id']),
      userId: JsonParse.asInt(json['user_id']),
      platform: JsonParse.asStringOrNull(json['platform']),
      isValid: JsonParse.asBool(json['is_valid']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': userId,
        'platform': platform,
        'is_valid': isValid,
      };
}
