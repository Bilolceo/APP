import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/api_client.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/auth_events.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/token_store.dart';
import 'package:mtt_menejer_diagnostika/presentation/app_routes.dart';
import 'package:mtt_menejer_diagnostika/presentation/login_screen.dart';
import 'package:mtt_menejer_diagnostika/state/app_providers.dart';

class _FakeAdapter implements HttpClientAdapter {
  final ResponseBody Function(RequestOptions options) responder;

  _FakeAdapter(this.responder);

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
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

String _fakeJwt(String role) {
  final header = base64Url.encode(utf8.encode('{"alg":"HS256","typ":"JWT"}'));
  final payload =
      base64Url.encode(utf8.encode(jsonEncode({'sub': '1', 'role': role})));
  return '$header.$payload.signature';
}

Map<String, dynamic> _profileJson() {
  return {
    'id': 1,
    'full_name': 'Demo User',
    'phone': '+998901112236',
    'notifications_enabled': true,
  };
}

void main() {
  /// Login ekrani uchun test muhitini quradi.
  ///
  /// `tokenStoreProvider` in-memory bilan override qilinadi — shunda haqiqiy
  /// `flutter_secure_storage` (platforma kanali) talab qilinmaydi.
  Widget buildSubject({
    ResponseBody Function(RequestOptions options)? responder,
  }) {
    final tokenStore = InMemoryTokenStore();
    final authEvents = AuthEvents();
    final apiClient = ApiClient(
      tokenStore: tokenStore,
      authEvents: authEvents,
      baseUrl: 'http://localhost/api/v1',
    );
    if (responder != null) {
      apiClient.dio.httpClientAdapter = _FakeAdapter(responder);
    }

    return ProviderScope(
      overrides: [
        tokenStoreProvider.overrideWithValue(tokenStore),
        authEventsProvider.overrideWithValue(authEvents),
        apiClientProvider.overrideWithValue(apiClient),
      ],
      child: MaterialApp(
        home: const LoginScreen(),
        onGenerateRoute: (settings) {
          if (settings.name == AppRoutes.home) {
            return MaterialPageRoute<void>(
              builder: (_) => const Scaffold(body: Text('HOME_OK')),
            );
          }
          return null;
        },
      ),
    );
  }

  testWidgets('Login ekrani xatosiz quriladi', (tester) async {
    await tester.pumpWidget(buildSubject());

    expect(find.text('Tizimga kirish'), findsWidgets);
    expect(find.byType(TextFormField), findsNWidgets(2));
    expect(find.text('Kirish'), findsOneWidget);
    expect(find.text('Ro\'yxatdan o\'tish'), findsOneWidget);
  });

  testWidgets('Bo\'sh parol kiritilganda validatsiya xatosi ko\'rsatiladi',
      (tester) async {
    await tester.pumpWidget(buildSubject());

    // Parolni bo'sh qoldirib "Kirish" tugmasini bosamiz.
    await tester.tap(find.text('Kirish'));
    await tester.pumpAndSettle();

    expect(find.text('Parol majburiy'), findsOneWidget);
  });

  testWidgets('Telefon raqami noto\'g\'ri formatda rad etiladi',
      (tester) async {
    await tester.pumpWidget(buildSubject());

    // Telefon maydoniga noto'g'ri (qisqa) qiymat kiritamiz.
    await tester.enterText(find.byType(TextFormField).first, '+99890');
    await tester.tap(find.text('Kirish'));
    await tester.pumpAndSettle();

    expect(
      find.text('Telefon +998 bilan boshlanib, 13 belgi bo\'lishi kerak'),
      findsOneWidget,
    );
  });

  testWidgets('Muvaffaqiyatli login home ekraniga olib o\'tadi',
      (tester) async {
    await tester.pumpWidget(buildSubject(
      responder: (options) {
        if (options.path.endsWith('/auth/login')) {
          return _json({
            'access_token': _fakeJwt('Rahbar'),
            'refresh_token': 'refresh-1',
            'token_type': 'bearer',
            'expires_in': 900,
          }, 200);
        }
        if (options.path.endsWith('/users/me')) {
          return _json(_profileJson(), 200);
        }
        return _json({}, 404);
      },
    ));

    await tester.enterText(
      find.byType(TextFormField).first,
      '+998901112236',
    );
    await tester.enterText(find.byType(TextFormField).last, 'secret123');
    await tester.tap(find.text('Kirish'));
    await tester.pumpAndSettle();

    expect(find.text('HOME_OK'), findsOneWidget);
  });
}
