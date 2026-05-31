import '../models/auth_models.dart';
import '../models/device_models.dart';
import '../models/json_utils.dart';
import 'api_client.dart';
import 'endpoints.dart';

/// Qurilma tokeni (push) domeni API mijozi (R16).
class DevicesApi {
  final ApiClient _client;

  /// Domen mijozini yaratadi.
  const DevicesApi(this._client);

  /// FCM qurilma tokenini joriy foydalanuvchiga bog'lab ro'yxatga oladi (R16.1).
  Future<DeviceTokenResponse> registerToken(DeviceTokenRequest request) {
    return _client.postJson(
      Endpoints.deviceToken,
      data: request.toJson(),
      parse: (data) => DeviceTokenResponse.fromJson(JsonParse.asMap(data)),
    );
  }

  /// Qurilma tokenini yaroqsiz deb belgilaydi (R16.6).
  Future<MessageResponse> invalidateToken(
    DeviceTokenInvalidateRequest request,
  ) {
    return _client.deleteJson(
      Endpoints.deviceToken,
      data: request.toJson(),
      parse: (data) => MessageResponse.fromJson(JsonParse.asMap(data)),
    );
  }
}
