import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/api_client.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/auth_events.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/token_store.dart';

/// Soxta HTTP adapter — Dio so'rovlarini tarmoqsiz (in-memory) javoblar bilan
/// qondiradi. Har bir so'rov uchun [responder] funksiyasi javob qaytaradi.
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

ApiClient _clientWithAdapter({
  required InMemoryTokenStore store,
  required AuthEvents events,
  required _FakeAdapter adapter,
}) {
  final refreshDio = Dio(BaseOptions(baseUrl: 'http://localhost/api/v1'));
  refreshDio.httpClientAdapter = adapter;
  final client = ApiClient(
    tokenStore: store,
    authEvents: events,
    baseUrl: 'http://localhost/api/v1',
    refreshDio: refreshDio,
  );
  client.dio.httpClientAdapter = adapter;
  return client;
}

void main() {
  group('AuthInterceptor — Bearer qo\'shish', () {
    test('himoyalangan so\'rovga access tokenni qo\'shadi', () async {
      final store = InMemoryTokenStore(
        accessToken: 'acc-1',
        refreshToken: 'ref-1',
      );
      final adapter = _FakeAdapter((options) {
        return _json({'id': 1, 'full_name': 'X', 'phone': '+998900000000'}, 200);
      });
      final client = _clientWithAdapter(
        store: store,
        events: AuthEvents(),
        adapter: adapter,
      );

      await client.getJson('/users/me', parse: (data) => data);

      expect(adapter.requests.single.headers['Authorization'], 'Bearer acc-1');
    });

    test('login (ochiq) endpointga token qo\'shmaydi', () async {
      final store = InMemoryTokenStore(accessToken: 'acc-1');
      final adapter = _FakeAdapter((options) {
        return _json({
          'access_token': 'a',
          'refresh_token': 'b',
          'token_type': 'bearer',
          'expires_in': 900,
        }, 200);
      });
      final client = _clientWithAdapter(
        store: store,
        events: AuthEvents(),
        adapter: adapter,
      );

      await client.postJson('/auth/login', parse: (data) => data);

      expect(adapter.requests.single.headers.containsKey('Authorization'),
          isFalse);
    });
  });

  group('AuthInterceptor — 401 refresh oqimi (R2.3)', () {
    test('401 da refresh qiladi, yangi token bilan qayta yuboradi', () async {
      final store = InMemoryTokenStore(
        accessToken: 'old-acc',
        refreshToken: 'ref-1',
      );
      var protectedCalls = 0;
      final adapter = _FakeAdapter((options) {
        if (options.path.endsWith('/auth/refresh')) {
          return _json({
            'access_token': 'new-acc',
            'token_type': 'bearer',
            'expires_in': 900,
          }, 200);
        }
        // Himoyalangan endpoint: birinchi chaqiruvda 401, ikkinchisida 200.
        protectedCalls++;
        if (options.headers['Authorization'] == 'Bearer new-acc') {
          return _json({'ok': true}, 200);
        }
        return _json({
          'error': {'code': 'authentication_error', 'message': '401'}
        }, 401);
      });
      final client = _clientWithAdapter(
        store: store,
        events: AuthEvents(),
        adapter: adapter,
      );

      final result = await client.getJson('/users/me', parse: (data) => data);

      expect((result as Map)['ok'], isTrue);
      expect(protectedCalls, 2, reason: '401 dan keyin bir marta qayta urinish');
      expect(await store.readAccessToken(), 'new-acc');
    });

    test('refresh muvaffaqiyatsiz bo\'lsa login hodisasi e\'lon qilinadi',
        () async {
      final store = InMemoryTokenStore(
        accessToken: 'old-acc',
        refreshToken: 'ref-1',
      );
      final events = AuthEvents();
      final adapter = _FakeAdapter((options) {
        if (options.path.endsWith('/auth/refresh')) {
          return _json({
            'error': {'code': 'authentication_error', 'message': 'refresh rad'}
          }, 401);
        }
        return _json({
          'error': {'code': 'authentication_error', 'message': '401'}
        }, 401);
      });
      final client = _clientWithAdapter(
        store: store,
        events: events,
        adapter: adapter,
      );

      final eventFuture = events.stream.first;

      await expectLater(
        client.getJson('/users/me', parse: (data) => data),
        throwsA(isA<Object>()),
      );

      expect(await eventFuture, AuthEvent.unauthorized);
      expect(await store.readAccessToken(), isNull,
          reason: 'muvaffaqiyatsiz refreshda tokenlar tozalanadi');
    });

    test('refresh token yo\'q bo\'lsa darhol login hodisasi e\'lon qilinadi',
        () async {
      final store = InMemoryTokenStore(accessToken: 'old-acc');
      final events = AuthEvents();
      final adapter = _FakeAdapter((options) {
        return _json({
          'error': {'code': 'authentication_error', 'message': '401'}
        }, 401);
      });
      final client = _clientWithAdapter(
        store: store,
        events: events,
        adapter: adapter,
      );

      final eventFuture = events.stream.first;

      await expectLater(
        client.getJson('/users/me', parse: (data) => data),
        throwsA(isA<Object>()),
      );

      expect(await eventFuture, AuthEvent.unauthorized);
    });
  });
}
