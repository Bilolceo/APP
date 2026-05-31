import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/user_models.dart';
import '../state/app_providers.dart';
import '../state/auth_state.dart';
import 'app_routes.dart';

/// Profil ko'rish ekrani (R5.1).
///
/// Global `authStateProvider` dagi profilni ko'rsatadi: to'liq ism, telefon,
/// ish joyi, lavozim, ish staji, ta'lim darajasi, malaka oshirish kurslari,
/// sertifikatlar, hudud va tashkilot turi. Tahrirlash ekraniga o'tish tugmasi
/// mavjud (telefon o'zgarmas — R5.4).
class ProfileScreen extends ConsumerWidget {
  /// Konstruktor.
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authStateProvider);
    final profile = authState.profile;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Profil'),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit_outlined),
            tooltip: 'Tahrirlash',
            onPressed: profile == null
                ? null
                : () =>
                    Navigator.of(context).pushNamed(AppRoutes.profileEdit),
          ),
        ],
      ),
      body: profile == null
          ? const Center(child: Text('Profil ma\'lumoti mavjud emas'))
          : _ProfileBody(profile: profile, role: authState.role),
    );
  }
}

class _ProfileBody extends StatelessWidget {
  final UserProfile profile;
  final String? role;

  const _ProfileBody({required this.profile, required this.role});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Center(
          child: CircleAvatar(
            radius: 44,
            backgroundColor: scheme.primaryContainer,
            child: Text(
              _initials(profile.fullName),
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    color: scheme.onPrimaryContainer,
                  ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        Center(
          child: Text(
            profile.fullName,
            style: Theme.of(context).textTheme.titleLarge,
            textAlign: TextAlign.center,
          ),
        ),
        if (role != null)
          Center(
            child: Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Chip(label: Text(role!)),
            ),
          ),
        const SizedBox(height: 24),
        _InfoTile(
          icon: Icons.phone_outlined,
          label: 'Telefon',
          value: profile.phone,
        ),
        _InfoTile(
          icon: Icons.notifications_outlined,
          label: 'Bildirishnomalar',
          value: profile.notificationsEnabled ? 'Yoqilgan' : 'O\'chirilgan',
        ),
        _InfoTile(
          icon: Icons.work_outline,
          label: 'Lavozim',
          value: profile.position,
        ),
        _InfoTile(
          icon: Icons.timelapse_outlined,
          label: 'Ish staji (yil)',
          value: profile.experienceYears?.toString(),
        ),
        _InfoTile(
          icon: Icons.school_outlined,
          label: 'Ta\'lim darajasi',
          value: profile.educationLevel,
        ),
        _InfoTile(
          icon: Icons.menu_book_outlined,
          label: 'Malaka oshirish kurslari',
          value: profile.qualificationCourses,
        ),
        _InfoTile(
          icon: Icons.verified_outlined,
          label: 'Sertifikatlar',
          value: profile.certificates,
        ),
        _InfoTile(
          icon: Icons.business_outlined,
          label: 'Tashkilot ID',
          value: profile.organizationId?.toString(),
        ),
        _InfoTile(
          icon: Icons.category_outlined,
          label: 'Tashkilot turi',
          value: profile.orgType,
        ),
        _InfoTile(
          icon: Icons.map_outlined,
          label: 'Hudud ID',
          value: profile.regionId?.toString(),
        ),
        const SizedBox(height: 16),
        FilledButton.tonalIcon(
          onPressed: () =>
              Navigator.of(context).pushNamed(AppRoutes.profileEdit),
          icon: const Icon(Icons.edit_outlined),
          label: const Text('Profilni tahrirlash'),
        ),
      ],
    );
  }

  static String _initials(String fullName) {
    final parts = fullName.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts.first.isEmpty) {
      return '?';
    }
    if (parts.length == 1) {
      return parts.first.characters.first.toUpperCase();
    }
    return (parts.first.characters.first + parts[1].characters.first)
        .toUpperCase();
  }
}

class _InfoTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String? value;

  const _InfoTile({required this.icon, required this.label, this.value});

  @override
  Widget build(BuildContext context) {
    final display = (value == null || value!.trim().isEmpty) ? '—' : value!;
    return ListTile(
      leading: Icon(icon),
      title: Text(label),
      subtitle: Text(display),
      dense: true,
    );
  }
}
