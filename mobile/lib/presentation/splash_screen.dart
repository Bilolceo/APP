import 'package:flutter/material.dart';

import '../core/app_constants.dart';

/// Splash ekrani — sessiya tiklanayotganda (bootstrap) ko'rsatiladi (20.1).
///
/// `authStateProvider` holati [AuthStatus.unknown] bo'lganda `AuthGate` shu
/// ekranni ko'rsatadi. Bu ekran o'zi mantiqqa ega emas — faqat ilova nomi va
/// yuklanish indikatorini chiqaradi.
class SplashScreen extends StatelessWidget {
  /// Konstruktor.
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.analytics_outlined, size: 88, color: scheme.primary),
            const SizedBox(height: 24),
            Text(
              AppConstants.appName,
              style: Theme.of(context).textTheme.titleLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),
            const CircularProgressIndicator(),
          ],
        ),
      ),
    );
  }
}
