import '../models/auth_models.dart';
import '../models/json_utils.dart';
import '../models/user_models.dart';
import 'api_client.dart';
import 'endpoints.dart';
import 'token_store.dart';

/// Autentifikatsiya domeni API mijozi (R1, R2, R3).
///
/// `ApiClient` ustidagi yupqa qatlam: so'rovlarni yuboradi va backend
/// javoblarini DTO'larga keltiradi. Xatolar tipli [ApiException] sifatida
/// tarqaladi. Login/refresh muvaffaqiyatida tokenlar [TokenStore] ga saqlanadi.
class AuthApi {
  final ApiClient _client;

  /// Domen mijozini yaratadi.
  const AuthApi(this._client);

  /// Yangi hisob yaratadi (R1.1). Backend yangi profilni qaytaradi.
  Future<UserProfile> register(RegisterRequest request) {
    return _client.postJson(
      Endpoints.register,
      data: request.toJson(),
      parse: (data) => UserProfile.fromJson(JsonParse.asMap(data)),
    );
  }

  /// Telefon va parol bilan kirib token juftligini oladi (R2.1).
  ///
  /// Muvaffaqiyatda tokenlar [TokenStore] ga saqlanadi.
  Future<AuthTokens> login(LoginRequest request) async {
    final tokens = await _client.postJson(
      Endpoints.login,
      data: request.toJson(),
      parse: (data) => AuthTokens.fromJson(JsonParse.asMap(data)),
    );
    await _client.tokenStore.saveAuthTokens(tokens);
    return tokens;
  }

  /// Refresh token bilan yangi access token oladi (R2.3).
  ///
  /// Muvaffaqiyatda yangi access token [TokenStore] da yangilanadi. Odatda bu
  /// oqim [AuthInterceptor] tomonidan avtomatik bajariladi; metod qo'lda
  /// yangilash uchun ham mavjud.
  Future<AccessTokenResponse> refresh(RefreshRequest request) async {
    final response = await _client.postJson(
      Endpoints.refresh,
      data: request.toJson(),
      parse: (data) => AccessTokenResponse.fromJson(JsonParse.asMap(data)),
    );
    if (response.accessToken.isNotEmpty) {
      await _client.tokenStore.updateAccessToken(response.accessToken);
    }
    return response;
  }

  /// Tizimdan chiqadi va tokenlarni bekor qiladi (R2.4).
  ///
  /// Refresh token (mavjud bo'lsa) so'rov tanasida yuboriladi; mahalliy
  /// tokenlar har holda tozalanadi.
  Future<MessageResponse> logout() async {
    final refreshToken = await _client.tokenStore.readRefreshToken();
    try {
      return await _client.postJson(
        Endpoints.logout,
        data: LogoutRequest(refreshToken: refreshToken).toJson(),
        parse: (data) => MessageResponse.fromJson(JsonParse.asMap(data)),
      );
    } finally {
      await _client.tokenStore.clear();
    }
  }

  /// Parolni tiklash kodini so'raydi (R3.1, R3.2).
  Future<MessageResponse> forgotPassword(ForgotPasswordRequest request) {
    return _client.postJson(
      Endpoints.forgotPassword,
      data: request.toJson(),
      parse: (data) => MessageResponse.fromJson(JsonParse.asMap(data)),
    );
  }

  /// Tasdiqlash kodi bilan parolni yangilaydi (R3.3–R3.7).
  Future<MessageResponse> resetPassword(ResetPasswordRequest request) {
    return _client.postJson(
      Endpoints.resetPassword,
      data: request.toJson(),
      parse: (data) => MessageResponse.fromJson(JsonParse.asMap(data)),
    );
  }
}
