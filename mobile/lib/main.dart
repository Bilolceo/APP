import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/app_constants.dart';
import 'core/app_theme.dart';
import 'presentation/app_routes.dart';
import 'presentation/auth_gate.dart';
import 'presentation/forgot_password_screen.dart';
import 'presentation/home_screen.dart';
import 'presentation/login_screen.dart';
import 'presentation/portfolio_screen.dart';
import 'presentation/profile_edit_screen.dart';
import 'presentation/profile_screen.dart';
import 'presentation/register_screen.dart';
import 'presentation/result_detail_screen.dart';
import 'presentation/results_screen.dart';
import 'presentation/reset_password_screen.dart';
import 'presentation/test_taking_screen.dart';
import 'presentation/tests_list_screen.dart';
import 'presentation/analytics_screen.dart';
import 'state/app_providers.dart';
import 'state/auth_state.dart';

/// Ilovaning kirish nuqtasi.
///
/// Butun ilova `ProviderScope` (Riverpod) bilan o'raladi, shunda state
/// management butun widget daraxti bo'ylab ishlaydi (R19.2).
Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await _initializeFirebaseSafely();
  runApp(
    const ProviderScope(
      child: MttMenejerDiagnostikaApp(),
    ),
  );
}

Future<void> _initializeFirebaseSafely() async {
  try {
    await Firebase.initializeApp();
  } catch (_) {
    // Firebase sozlanmagan muhitlarda (masalan test/dev) ilovani to'xtatmaymiz.
  }
}

/// Ildiz Material Design ilovasi (R19.2).
class MttMenejerDiagnostikaApp extends ConsumerStatefulWidget {
  /// Konstruktor.
  const MttMenejerDiagnostikaApp({super.key});

  @override
  ConsumerState<MttMenejerDiagnostikaApp> createState() =>
      _MttMenejerDiagnostikaAppState();
}

class _MttMenejerDiagnostikaAppState
    extends ConsumerState<MttMenejerDiagnostikaApp> {
  @override
  Widget build(BuildContext context) {
    ref.listen<AuthStatus>(
      authStateProvider.select((s) => s.status),
      (previous, next) {
        final push = ref.read(pushNotificationsServiceProvider);
        if (next == AuthStatus.authenticated) {
          unawaited(push.onAuthenticated());
        } else if (previous == AuthStatus.authenticated &&
            next != AuthStatus.authenticated) {
          unawaited(push.onSignedOut());
        }
      },
    );

    return MaterialApp(
      title: AppConstants.appName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      // Ildiz ekran — global auth holatiga qarab splash/onboarding/home (20.1).
      home: const AuthGate(),
      // Auth oqimi, profil va 20.2 modul ekranlari uchun nomli marshrutlar.
      onGenerateRoute: _onGenerateRoute,
    );
  }

  /// Nomli marshrutlarni yaratadi (argument uzatish uchun `onGenerateRoute`).
  static Route<dynamic>? _onGenerateRoute(RouteSettings settings) {
    switch (settings.name) {
      case AppRoutes.login:
        return MaterialPageRoute<void>(
          builder: (_) => const LoginScreen(),
          settings: settings,
        );
      case AppRoutes.register:
        return MaterialPageRoute<void>(
          builder: (_) => const RegisterScreen(),
          settings: settings,
        );
      case AppRoutes.forgotPassword:
        return MaterialPageRoute<void>(
          builder: (_) => const ForgotPasswordScreen(),
          settings: settings,
        );
      case AppRoutes.resetPassword:
        final phone = settings.arguments is String
            ? settings.arguments as String
            : null;
        return MaterialPageRoute<void>(
          builder: (_) => ResetPasswordScreen(phone: phone),
          settings: settings,
        );
      case AppRoutes.home:
        return MaterialPageRoute<void>(
          builder: (_) => const HomeScreen(),
          settings: settings,
        );
      case AppRoutes.profile:
        return MaterialPageRoute<void>(
          builder: (_) => const ProfileScreen(),
          settings: settings,
        );
      case AppRoutes.profileEdit:
        return MaterialPageRoute<void>(
          builder: (_) => const ProfileEditScreen(),
          settings: settings,
        );
      case AppRoutes.tests:
        return MaterialPageRoute<void>(
          builder: (_) => const TestsListScreen(),
          settings: settings,
        );
      case AppRoutes.testTaking:
        final testId = settings.arguments is int ? settings.arguments as int : 0;
        if (testId <= 0) {
          return null;
        }
        return MaterialPageRoute<void>(
          builder: (_) => TestTakingScreen(testId: testId),
          settings: settings,
        );
      case AppRoutes.results:
        return MaterialPageRoute<void>(
          builder: (_) => const ResultsScreen(),
          settings: settings,
        );
      case AppRoutes.resultDetail:
        final resultId =
            settings.arguments is int ? settings.arguments as int : 0;
        if (resultId <= 0) {
          return null;
        }
        return MaterialPageRoute<void>(
          builder: (_) => ResultDetailScreen(resultId: resultId),
          settings: settings,
        );
      case AppRoutes.analytics:
        return MaterialPageRoute<void>(
          builder: (_) => const AnalyticsScreen(),
          settings: settings,
        );
      case AppRoutes.portfolio:
        return MaterialPageRoute<void>(
          builder: (_) => const PortfolioScreen(),
          settings: settings,
        );
      default:
        return null;
    }
  }
}
