import 'package:flutter/material.dart';

/// Yuklanish holatini ko'rsatuvchi qayta ishlatiluvchi tugma (20.1).
///
/// [isLoading] `true` bo'lganda matn o'rniga aylanuvchi indikator ko'rsatiladi
/// va tugma bosilmaydigan (disabled) bo'ladi — bu login/register kabi async
/// amallar davomida ikki marta yuborishni oldini oladi.
class LoadingButton extends StatelessWidget {
  /// Tugma matni.
  final String label;

  /// Yuklanish indikatori faolligi.
  final bool isLoading;

  /// Bosilganda chaqiriladigan callback (yuklanishda `null` bo'lib disable bo'ladi).
  final VoidCallback? onPressed;

  /// Tugmani yaratadi.
  const LoadingButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.isLoading = false,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: FilledButton(
        onPressed: isLoading ? null : onPressed,
        child: isLoading
            ? const SizedBox(
                height: 20,
                width: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : Text(label),
      ),
    );
  }
}
