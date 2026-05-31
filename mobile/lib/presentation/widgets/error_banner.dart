import 'package:flutter/material.dart';

/// Forma/ekran xatosini ko'rsatuvchi qayta ishlatiluvchi banner (20.1).
///
/// [message] `null` yoki bo'sh bo'lsa hech narsa ko'rsatilmaydi (`SizedBox`).
/// Aks holda xato rang sxemasida (errorContainer) qisqa xabar chiqaradi.
class ErrorBanner extends StatelessWidget {
  /// Ko'rsatiladigan xato matni (yo'q bo'lsa banner ko'rinmaydi).
  final String? message;

  /// Bannerni yaratadi.
  const ErrorBanner({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    final msg = message;
    if (msg == null || msg.isEmpty) {
      return const SizedBox.shrink();
    }
    final scheme = Theme.of(context).colorScheme;
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: scheme.errorContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(Icons.error_outline, color: scheme.onErrorContainer, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              msg,
              style: TextStyle(color: scheme.onErrorContainer),
            ),
          ),
        ],
      ),
    );
  }
}
