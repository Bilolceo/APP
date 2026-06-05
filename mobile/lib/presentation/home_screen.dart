import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/app_providers.dart';
import '../state/auth_state.dart';
import 'app_routes.dart';

/// Bosh ekran (dashboard) — kirilgan foydalanuvchiga ko'rsatiladi (20.1).
///
/// Profilga kirish nuqtasi va logout amalini ta'minlaydi. Testlar, analitika va
/// portfolio bo'limlari 20.2 vazifasiga muvofiq alohida ekranlarga ulangan.
class HomeScreen extends ConsumerWidget {
  /// Konstruktor.
  const HomeScreen({super.key});

  Future<void> _confirmLogout(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Chiqish'),
        content: const Text('Tizimdan chiqmoqchimisiz?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Bekor qilish'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Chiqish'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await ref.read(authStateProvider.notifier).logout();
      if (!context.mounted) {
        return;
      }
      Navigator.of(context).pushNamedAndRemoveUntil(
        AppRoutes.login,
        (route) => false,
      );
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authStateProvider);
    final profile = authState.profile;
    final greetingName = profile?.fullName ?? 'Foydalanuvchi';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Bosh sahifa'),
        actions: [
          IconButton(
            icon: const Icon(Icons.person_outline),
            tooltip: 'Profil',
            onPressed: () => Navigator.of(context).pushNamed(AppRoutes.profile),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Chiqish',
            onPressed: () => _confirmLogout(context, ref),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: ListTile(
              leading: const Icon(Icons.waving_hand_outlined),
              title: Text('Salom, $greetingName'),
              subtitle:
                  authState.role == null ? null : Text('Rol: ${authState.role}'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () =>
                  Navigator.of(context).pushNamed(AppRoutes.profile),
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'Bo\'limlar',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          _DashboardTile(
            icon: Icons.assignment_outlined,
            title: 'Diagnostika testlari',
            subtitle: 'Faol testlar ro\'yxati',
            enabled: true,
            onTap: () => Navigator.of(context).pushNamed(AppRoutes.tests),
          ),
          _DashboardTile(
            icon: Icons.fact_check_outlined,
            title: 'Mening natijalarim',
            subtitle: 'Test natijalari va tafsilotlari',
            enabled: true,
            onTap: () => Navigator.of(context).pushNamed(AppRoutes.results),
          ),
          _DashboardTile(
            icon: Icons.insights_outlined,
            title: 'Analitika',
            subtitle: 'Radar, line, progress va kartochkalar',
            enabled: true,
            onTap: () => Navigator.of(context).pushNamed(AppRoutes.analytics),
          ),
          _DashboardTile(
            icon: Icons.folder_outlined,
            title: 'Portfolio',
            subtitle: 'Fayllarni yuklash va boshqarish',
            enabled: true,
            onTap: () => Navigator.of(context).pushNamed(AppRoutes.portfolio),
          ),
          const SizedBox(height: 8),
          _DashboardTile(
            icon: Icons.person_outline,
            title: 'Profil',
            subtitle: 'Ma\'lumotlarni ko\'rish va tahrirlash',
            enabled: true,
            onTap: () => Navigator.of(context).pushNamed(AppRoutes.profile),
          ),
        ],
      ),
    );
  }
}

class _DashboardTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final bool enabled;
  final VoidCallback? onTap;

  const _DashboardTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.enabled,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: Icon(icon),
        title: Text(title),
        subtitle: Text(subtitle),
        trailing: enabled
            ? const Icon(Icons.chevron_right)
            : const Icon(Icons.lock_clock_outlined),
        enabled: enabled,
        onTap: enabled ? onTap : null,
      ),
    );
  }
}
