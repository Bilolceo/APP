import 'dart:async';

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import '../data/api_client/devices_api.dart';
import '../data/models/device_models.dart';

/// Push bildirishnomalar xizmati (FCM) — 20.3.
///
/// Mas'uliyatlar:
/// - FCM ruxsatini so'rash va joriy tokenni olish.
/// - Tokenni backendga `POST /devices/token` orqali ro'yxatdan o'tkazish.
/// - `onTokenRefresh` oqimini tinglab, yangilangan tokenni qayta yuborish.
/// - Chiqishda tokenni `DELETE /devices/token` orqali yaroqsiz deb belgilash.
class PushNotificationsService {
  final FirebaseMessaging? _messagingOverride;
  final DevicesApi _devicesApi;

  StreamSubscription<String>? _refreshSub;
  bool _initialized = false;
  String? _registeredToken;

  /// Standart konstruktor.
  PushNotificationsService({
    required DevicesApi devicesApi,
    FirebaseMessaging? messaging,
  })  : _devicesApi = devicesApi,
        _messagingOverride = messaging;

  /// Authenticated sessiyada pushni faollashtiradi.
  Future<void> onAuthenticated() async {
    final ready = await _ensureInitialized();
    if (!ready) {
      return;
    }

    final token = await _safeGetToken();
    if (token == null || token.isEmpty) {
      return;
    }

    await _registerTokenIfNeeded(token);
  }

  /// Logout holatida tokenni backendda yaroqsiz deb belgilashga urinadi.
  Future<void> onSignedOut() async {
    final token = _registeredToken ?? await _safeGetToken();
    if (token == null || token.isEmpty) {
      _registeredToken = null;
      return;
    }

    try {
      await _devicesApi.invalidateToken(
        DeviceTokenInvalidateRequest(token: token),
      );
    } catch (_) {
      // Best-effort: logout oqimini to'xtatmaymiz.
    } finally {
      _registeredToken = null;
    }
  }

  /// Resurslarni tozalaydi.
  Future<void> dispose() async {
    await _refreshSub?.cancel();
  }

  Future<bool> _ensureInitialized() async {
    if (_initialized) {
      return true;
    }

    try {
      final messaging = _resolveMessaging();
      if (messaging == null) {
        return false;
      }

      await messaging.requestPermission();

      _refreshSub = messaging.onTokenRefresh.listen((token) {
        unawaited(_registerTokenIfNeeded(token));
      });

      _initialized = true;
      return true;
    } on MissingPluginException {
      // Widget test / plugin mavjud bo'lmagan muhit.
      return false;
    } catch (_) {
      return false;
    }
  }

  Future<String?> _safeGetToken() async {
    try {
      final messaging = _resolveMessaging();
      if (messaging == null) {
        return null;
      }
      return await messaging.getToken();
    } on MissingPluginException {
      return null;
    } catch (_) {
      return null;
    }
  }

  FirebaseMessaging? _resolveMessaging() {
    if (_messagingOverride != null) {
      return _messagingOverride;
    }
    try {
      return FirebaseMessaging.instance;
    } catch (_) {
      return null;
    }
  }

  Future<void> _registerTokenIfNeeded(String token) async {
    if (token.isEmpty || token == _registeredToken) {
      return;
    }

    try {
      await _devicesApi.registerToken(
        DeviceTokenRequest(
          token: token,
          platform: _platformName(),
        ),
      );
      _registeredToken = token;
    } catch (_) {
      // Best-effort: xatoda ilovani to'xtatmaymiz.
    }
  }

  static String _platformName() {
    if (kIsWeb) {
      return 'web';
    }
    return defaultTargetPlatform.name;
  }
}
