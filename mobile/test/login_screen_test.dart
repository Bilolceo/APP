import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/token_store.dart';
import 'package:mtt_menejer_diagnostika/presentation/login_screen.dart';
import 'package:mtt_menejer_diagnostika/state/app_providers.dart';

void main() {
  /// Login ekrani uchun test muhitini quradi.
  ///
  /// `tokenStoreProvider` in-memory bilan override qilinadi — shunda haqiqiy
  /// `flutter_secure_storage` (platforma kanali) talab qilinmaydi.
  Widget buildSubject() {
    return ProviderScope(
      overrides: [
        tokenStoreProvider.overrideWithValue(InMemoryTokenStore()),
      ],
      child: const MaterialApp(home: LoginScreen()),
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
}
