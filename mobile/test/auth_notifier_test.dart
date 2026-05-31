import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/api_client.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/auth_api.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/auth_events.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/token_store.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/users_api.dart';
import 'package:mtt_menejer_diagnostika/state/auth_state.dart';

/// Soxta HTTP adapter — Dio so'rovlarini tarmoqsiz (in-memory) javoblar bilan
/// qondiradi. `data/auth_interceptor_test.dart` dagi naqsh bilan bir xil.
class _FakeAdapter implements HttpClientAdapter {
  final ResponseBody Function(RequestOptions options) responder;
  final List<RequestOptions> requests = [];

  _FakeAdapter(this.responder);

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    return responder(options);
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody _json(Map<String, dynamic> body, int statusCode) {
  return ResponseBody.fromString(
    jsonEncode(body),
    statusCode,
    headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType],
    },
  );
}

/// `role` da'vosiga ega soxta (imzosiz) JWT access token quradi.
String _fakeJwt(String role) {
  final header = base64Url.encode(utf8.encode('{"alg":"HS256","typ":"JWT"}'));
  final payload =
      base64Url.encode(utf8.encode(jsonEncode({'sub': '1', 'role': role})));
  return '$header.$payload.signature';
}

Map<String, dynamic> _profileJson({String fullName = 'Ali Valiyev'}) {
  return {
    'id': 1,
    'full_name': fullName,
    'phone': '+998901234567',
    'position': 'Direktor',
    'experience_years': 5,
    'notifications_enabled': true,
  };
}

/// Berilgan [responder] bilan to'liq AuthNotifier muhitini quradi.
({
  AuthNotifier notifier,
  InMemoryTokenStore store,
  AuthEvents events,
  _FakeAdapter adapter,
}) _buildNotifier(
  ResponseBody Function(RequestOptions options) responder, {
  InMemoryTokenStore? store,
}) {
  final tokenStore = store ?? InMemoryTokenStore();
  final events = AuthEvents();
  final client = ApiClient(
    tokenStore: tokenStore,
    authEvents: events,
    baseUrl: 'http://localhost/api/v1',
  );
  final adapter = _FakeAdapter(responder);
  client.dio.httpClientAdapter = adapter;

  final notifier = AuthNotifier(
    authApi: AuthApi(client),
    usersApi: UsersApi(client),
    tokenStore: tokenStore,
    authEvents: events,
  );
  return (notifier: notifier, store: tokenStore, events: events, adapter: adapter);
}

void main() {
  group('AuthNotifier — boshlang\'ich holat', () {
    test('boshida status unknown bo\'ladi', () {
      final env = _buildNotifier((_) => _json({}, 200));
      addTearDown(env.notifier.dispose);
      addTearDown(env.events.dispose);

      expect(env.notifier.state.status, AuthStatus.unknown);
      expect(env.notifier.state.isAuthenticated, isFalse);
    });
  });

  group('AuthNotifier — bootstrap (R2.1)', () {
    test('saqlangan token bo\'lsa authenticated holatga o\'tadi', () async {
      final store = InMemoryTokenStore(
        accessToken: _fakeJwt('Rahbar'),
        refreshToken: 'ref-1',
      );
      final env = _buildNotifier(
        (options) {
          if (options.path.endsWith('/users/me')) {
            return _json(_profileJson(), 200);
          }
          return _json({}, 404);
        },
        store: store,
      );
      addTearDown(env.notifier.dispose);
      addTearDown(env.events.dispose);

      await env.notifier.bootstrap();

      expect(env.notifier.state.status, AuthStatus.authenticated);
      expect(env.notifier.state.profile?.fullName, 'Ali Valiyev');
      expect(env.notifier.state.role, 'Rahbar');
    });

    test('token yo\'q bo\'lsa unauthenticated holatga o\'tadi', () async {
      final env = _buildNotifier((_) => _json({}, 200));
      addTearDown(env.notifier.dispose);
      addTearDown(env.events.dispose);

      await env.notifier.bootstrap();

      expect(env.notifier.state.status, AuthStatus.unauthenticated);
    });

    test('token yaroqsiz bo\'lsa (getMe 401) tokenlar tozalanadi', () async {
      final store = InMemoryTokenStore(
        accessToken: _fakeJwt('Rahbar'),
        refreshToken: 'ref-1',
      );
      // getMe 401 → interseptor refresh urinadi; refresh ham 401 → tozalash.
      final env = _buildNotifier(
        (options) => _json({
          'error': {'code': 'authentication_error', 'message': '401'}
        }, 401),
        store: store,
      );
      addTearDown(env.notifier.dispose);
      addTearDown(env.events.dispose);

      await env.notifier.bootstrap();

      expect(env.notifier.state.status, AuthStatus.unauthenticated);
      expect(await store.readAccessToken(), isNull);
    });
  });

  group('AuthNotifier — login (R2.1, R2.2)', () {
    test('to\'g\'ri kredensiallar bilan authenticated bo\'ladi', () async {
      final env = _buildNotifier((options) {
        if (options.path.endsWith('/auth/login')) {
          return _json({
            'access_token': _fakeJwt('Ekspert'),
            'refresh_token': 'ref-1',
            'token_type': 'bearer',
            'expires_in': 900,
          }, 200);
        }
        if (options.path.endsWith('/users/me')) {
          return _json(_profileJson(), 200);
        }
        return _json({}, 404);
      });
      addTearDown(env.notifier.dispose);
      addTearDown(env.events.dispose);

      final ok = await env.notifier.login(
        phone: '+998901234567',
        password: 'secret123',
      );

      expect(ok, isTrue);
      expect(env.notifier.state.status, AuthStatus.authenticated);
      expect(env.notifier.state.role, 'Ekspert');
      expect(env.notifier.state.errorMessage, isNull);
      expect(await env.store.readAccessToken(), isNotNull);
    });

    test('noto\'g\'ri kredensiallarda xato xabari o\'rnatiladi', () async {
      final env = _buildNotifier((options) {
        return _json({
          'error': {
            'code': 'authentication_error',
            'message': 'Telefon raqami yoki parol noto\'g\'ri'
          }
        }, 401);
      });
      addTearDown(env.notifier.dispose);
      addTearDown(env.events.dispose);

      final ok = await env.notifier.login(
        phone: '+998901234567',
        password: 'wrong-pass',
      );

      expect(ok, isFalse);
      expect(env.notifier.state.status, AuthStatus.unauthenticated);
      expect(env.notifier.state.errorMessage,
          'Telefon raqami yoki parol noto\'g\'ri');
    });
  });

  group('AuthNotifier — logout (R2.4)', () {
    test('logout tokenlarni tozalaydi va unauthenticated qiladi', () async {
      final store = InMemoryTokenStore(
        accessToken: _fakeJwt('Rahbar'),
        refreshToken: 'ref-1',
      );
      final env = _buildNotifier(
        (options) {
          if (options.path.endsWith('/auth/logout')) {
            return _json({'message': 'Tizimdan chiqdingiz'}, 200);
          }
          if (options.path.endsWith('/users/me')) {
            return _json(_profileJson(), 200);
          }
          return _json({}, 404);
        },
        store: store,
      );
      addTearDown(env.notifier.dispose);
      addTearDown(env.events.dispose);

      await env.notifier.bootstrap();
      expect(env.notifier.state.status, AuthStatus.authenticated);

      await env.notifier.logout();

      expect(env.notifier.state.status, AuthStatus.unauthenticated);
      expect(await store.readAccessToken(), isNull);
    });
  });

  group('AuthNotifier — unauthorized hodisasi (R2.3)', () {
    test('AuthEvent.unauthorized kelganda unauthenticated bo\'ladi', () async {
      final store = InMemoryTokenStore(
        accessToken: _fakeJwt('Rahbar'),
        refreshToken: 'ref-1',
      );
      final env = _buildNotifier(
        (options) {
          if (options.path.endsWith('/users/me')) {
            return _json(_profileJson(), 200);
          }
          return _json({}, 404);
        },
        store: store,
      );
      addTearDown(env.notifier.dispose);
      addTearDown(env.events.dispose);

      await env.notifier.bootstrap();
      expect(env.notifier.state.status, AuthStatus.authenticated);

      // Ma'lumot qatlami sessiya yaroqsizligini signal qiladi.
      env.events.emitUnauthorized();
      // Broadcast stream hodisasi keyingi mikrotaskda yetkaziladi.
      await Future<void>.delayed(Duration.zero);

      expect(env.notifier.state.status, AuthStatus.unauthenticated);
      expect(env.notifier.state.errorMessage, isNotNull);
    });
  });
}
