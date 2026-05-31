import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../core/app_constants.dart';
import '../models/auth_models.dart';

/// Tokenlarni saqlash uchun abstraksiya (R17 — JWT/refresh xavfsiz saqlash).
///
/// Bu interfeys `ApiClient` ni konkret xotira tafsilotidan (masalan
/// `flutter_secure_storage`) ajratadi — shu sababli mijoz testlarda osongina
/// soxta (in-memory) implementatsiya bilan sinaladi. Konseptual jihatdan
/// implementatsiya tokenlarni xavfsiz saqlovga (Keystore/Keychain) yozadi.
abstract interface class TokenStore {
  /// Joriy access tokenni qaytaradi (yo'q bo'lsa `null`).
  Future<String?> readAccessToken();

  /// Joriy refresh tokenni qaytaradi (yo'q bo'lsa `null`).
  Future<String?> readRefreshToken();

  /// Access va refresh tokenlarni saqlaydi.
  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  });

  /// Faqat access tokenni yangilaydi (refresh oqimidan keyin).
  Future<void> updateAccessToken(String accessToken);

  /// Saqlangan barcha tokenlarni o'chiradi (logout / refresh muvaffaqiyatsiz).
  Future<void> clear();
}

/// [TokenStore] uchun qulay kengaytmalar.
extension TokenStoreX on TokenStore {
  /// [AuthTokens] obyektini bir martada saqlaydi.
  Future<void> saveAuthTokens(AuthTokens tokens) {
    return saveTokens(
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
    );
  }
}

/// `flutter_secure_storage` ga tayanuvchi standart [TokenStore].
///
/// Tokenlar platforma xavfsiz saqlovida (Android Keystore) saqlanadi.
class SecureTokenStore implements TokenStore {
  final FlutterSecureStorage _storage;

  /// Berilgan (yoki standart) [FlutterSecureStorage] bilan yaratadi.
  SecureTokenStore({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  @override
  Future<String?> readAccessToken() {
    return _storage.read(key: AppConstants.accessTokenKey);
  }

  @override
  Future<String?> readRefreshToken() {
    return _storage.read(key: AppConstants.refreshTokenKey);
  }

  @override
  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _storage.write(key: AppConstants.accessTokenKey, value: accessToken);
    await _storage.write(
      key: AppConstants.refreshTokenKey,
      value: refreshToken,
    );
  }

  @override
  Future<void> updateAccessToken(String accessToken) {
    return _storage.write(key: AppConstants.accessTokenKey, value: accessToken);
  }

  @override
  Future<void> clear() async {
    await _storage.delete(key: AppConstants.accessTokenKey);
    await _storage.delete(key: AppConstants.refreshTokenKey);
  }
}

/// Test uchun oddiy in-memory [TokenStore] (xotira ichida saqlovchi).
///
/// Bu implementatsiya `flutter_secure_storage` ga bog'liq emas; shu sababli
/// `ApiClient` ni soxta token holati bilan birlik testlarida sinash mumkin.
class InMemoryTokenStore implements TokenStore {
  String? _accessToken;
  String? _refreshToken;

  /// Boshlang'ich tokenlar bilan yaratadi (ixtiyoriy).
  InMemoryTokenStore({String? accessToken, String? refreshToken})
      : _accessToken = accessToken,
        _refreshToken = refreshToken;

  @override
  Future<String?> readAccessToken() async => _accessToken;

  @override
  Future<String?> readRefreshToken() async => _refreshToken;

  @override
  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    _accessToken = accessToken;
    _refreshToken = refreshToken;
  }

  @override
  Future<void> updateAccessToken(String accessToken) async {
    _accessToken = accessToken;
  }

  @override
  Future<void> clear() async {
    _accessToken = null;
    _refreshToken = null;
  }
}
