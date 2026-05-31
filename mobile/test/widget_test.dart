import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mtt_menejer_diagnostika/data/api_client/token_store.dart';
import 'package:mtt_menejer_diagnostika/main.dart';
import 'package:mtt_menejer_diagnostika/presentation/splash_screen.dart';
import 'package:mtt_menejer_diagnostika/state/app_providers.dart';

void main() {
  testWidgets('Ilova xatosiz quriladi va splash bilan boshlanadi (smoke test)',
      (tester) async {
    // Ilovani ProviderScope ichida quramiz. `tokenStoreProvider` ni in-memory
    // bilan override qilamiz — shunda platforma xavfsiz xotira kanali (secure
    // storage) test muhitida talab qilinmaydi.
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          tokenStoreProvider.overrideWithValue(InMemoryTokenStore()),
        ],
        child: const MttMenejerDiagnostikaApp(),
      ),
    );

    // MaterialApp mavjudligini tekshiramiz.
    expect(find.byType(MaterialApp), findsOneWidget);

    // Boshlang'ich (unknown) holatda splash ekrani ko'rinadi.
    expect(find.byType(SplashScreen), findsOneWidget);
  });
}
