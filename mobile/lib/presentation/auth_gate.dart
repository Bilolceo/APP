import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/app_providers.dart';
import '../state/auth_state.dart';
import 'home_screen.dart';
import 'onboarding_screen.dart';
import 'splash_screen.dart';

/// Ildiz "darvoza" widgeti — global auth holatiga qarab ekranni tanlaydi (20.1).
///
/// Oqim:
///  - [AuthStatus.unknown] → [SplashScreen] (startda bootstrap chaqiriladi).
///  - [AuthStatus.unauthenticated] → [OnboardingScreen] (uning oxiri login'ga
///    olib boradi).
///  - [AuthStatus.authenticated] → [HomeScreen].
///
/// `AuthEvent.unauthorized` (R2.3) holat `unauthenticated` ga o'tganda shu
/// widget avtomatik login oqimiga qaytadi — alohida navigatsiya kodi shart emas.
class AuthGate extends ConsumerStatefulWidget {
  /// Konstruktor.
  const AuthGate({super.key});

  @override
  ConsumerState<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends ConsumerState<AuthGate> {
  @override
  void initState() {
    super.initState();
    // Birinchi freymdan keyin saqlangan sessiyani tiklaymiz (R2.1).
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(authStateProvider.notifier).bootstrap();
    });
  }

  @override
  Widget build(BuildContext context) {
    final status = ref.watch(authStateProvider.select((s) => s.status));

    switch (status) {
      case AuthStatus.unknown:
        return const SplashScreen();
      case AuthStatus.authenticated:
        return const HomeScreen();
      case AuthStatus.unauthenticated:
        return const OnboardingScreen();
    }
  }
}
