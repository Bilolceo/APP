import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/app_providers.dart';

/// Vaqtinchalik bosh ekran (placeholder).
///
/// TODO(20.x): Haqiqiy ekranlar shu `presentation/` qatlamida quriladi:
/// splash, onboarding, login, register, home dashboard, tests list,
/// test-taking, result, analytics, portfolio, profile (design.md).
///
/// Bu ekran skeleton bosqichida Material Design ilova ishga tushishini
/// tasdiqlash uchun xizmat qiladi.
class PlaceholderScreen extends ConsumerWidget {
  /// Konstruktor.
  const PlaceholderScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appName = ref.watch(appNameProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(appName),
      ),
      body: const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.analytics_outlined, size: 72),
              SizedBox(height: 16),
              Text(
                'Ilova skeletoni tayyor.',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
              SizedBox(height: 8),
              Text(
                'Ekranlar keyingi vazifalarda (20.x) qo\'shiladi.',
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
