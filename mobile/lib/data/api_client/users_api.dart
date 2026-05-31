import '../models/json_utils.dart';
import '../models/user_models.dart';
import 'api_client.dart';
import 'endpoints.dart';

/// Foydalanuvchi / profil domeni API mijozi (R5, R4).
class UsersApi {
  final ApiClient _client;

  /// Domen mijozini yaratadi.
  const UsersApi(this._client);

  /// Joriy foydalanuvchining to'liq profilini qaytaradi (R5.1).
  Future<UserProfile> getMe() {
    return _client.getJson(
      Endpoints.usersMe,
      parse: (data) => UserProfile.fromJson(JsonParse.asMap(data)),
    );
  }

  /// Tahrirlanadigan profil maydonlarini yangilaydi (R5.2–R5.4).
  Future<UserProfile> updateMe(ProfileUpdateRequest request) {
    return _client.patchJson(
      Endpoints.usersMe,
      data: request.toJson(),
      parse: (data) => UserProfile.fromJson(JsonParse.asMap(data)),
    );
  }

  /// Berilgan [userId] bo'yicha profilni RBAC asosida qaytaradi (R4.1, R4.3).
  Future<UserProfile> getUser(int userId) {
    return _client.getJson(
      Endpoints.user(userId),
      parse: (data) => UserProfile.fromJson(JsonParse.asMap(data)),
    );
  }
}
