import 'package:flutter/material.dart';

/// Ilovaning Material Design 3 mavzusi (R19.2).
///
/// Material 3 (Material You) yoqilgan; rang sxemasi asosiy rangdan
/// (`seedColor`) avtomatik generatsiya qilinadi.
class AppTheme {
  const AppTheme._();

  /// Asosiy brend rangi (placeholder — TODO 20.x dizaynga moslang).
  static const Color _seedColor = Color(0xFF1565C0);

  /// Yorug' (light) mavzu.
  static ThemeData get light => ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: _seedColor,
          brightness: Brightness.light,
        ),
        appBarTheme: const AppBarTheme(centerTitle: true),
      );

  /// Qorong'i (dark) mavzu.
  static ThemeData get dark => ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: _seedColor,
          brightness: Brightness.dark,
        ),
        appBarTheme: const AppBarTheme(centerTitle: true),
      );
}
