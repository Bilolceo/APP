import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/api_error.dart';
import '../data/models/user_models.dart';
import '../state/app_providers.dart';
import '../state/auth_state.dart';
import 'validators.dart';
import 'widgets/error_banner.dart';
import 'widgets/loading_button.dart';

/// Profilni tahrirlash ekrani (R5.2, R5.3, R5.4).
///
/// Faqat tahrirlanadigan maydonlarni ko'rsatadi (to'liq ism, lavozim, ish
/// staji 0–60, ta'lim darajasi, malaka kurslari, sertifikatlar, tashkilot/hudud
/// ID, tashkilot turi). Telefon o'zgarmas hisob identifikatori — disable
/// qilingan va so'rovga qo'shilmaydi (R5.4). Saqlash `AuthNotifier.updateProfile`
/// orqali `usersApiProvider.updateMe(...)` ni chaqiradi va global holatni
/// yangilaydi.
class ProfileEditScreen extends ConsumerStatefulWidget {
  /// Konstruktor.
  const ProfileEditScreen({super.key});

  @override
  ConsumerState<ProfileEditScreen> createState() => _ProfileEditScreenState();
}

class _ProfileEditScreenState extends ConsumerState<ProfileEditScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _fullNameController;
  late final TextEditingController _positionController;
  late final TextEditingController _experienceController;
  late final TextEditingController _educationController;
  late final TextEditingController _coursesController;
  late final TextEditingController _certificatesController;
  late final TextEditingController _orgTypeController;
  late final TextEditingController _organizationIdController;
  late final TextEditingController _regionIdController;
  bool _notificationsEnabled = true;

  bool _isLoading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final profile = ref.read(authStateProvider).profile;
    _fullNameController = TextEditingController(text: profile?.fullName ?? '');
    _positionController = TextEditingController(text: profile?.position ?? '');
    _experienceController = TextEditingController(
      text: profile?.experienceYears?.toString() ?? '',
    );
    _educationController =
        TextEditingController(text: profile?.educationLevel ?? '');
    _coursesController =
        TextEditingController(text: profile?.qualificationCourses ?? '');
    _certificatesController =
        TextEditingController(text: profile?.certificates ?? '');
    _orgTypeController = TextEditingController(text: profile?.orgType ?? '');
    _organizationIdController = TextEditingController(
      text: profile?.organizationId?.toString() ?? '',
    );
    _regionIdController = TextEditingController(
      text: profile?.regionId?.toString() ?? '',
    );
    _notificationsEnabled = profile?.notificationsEnabled ?? true;
  }

  @override
  void dispose() {
    _fullNameController.dispose();
    _positionController.dispose();
    _experienceController.dispose();
    _educationController.dispose();
    _coursesController.dispose();
    _certificatesController.dispose();
    _orgTypeController.dispose();
    _organizationIdController.dispose();
    _regionIdController.dispose();
    super.dispose();
  }

  String? _trimmedOrNull(TextEditingController controller) {
    final value = controller.text.trim();
    return value.isEmpty ? null : value;
  }

  int? _intOrNull(TextEditingController controller) {
    final value = controller.text.trim();
    return value.isEmpty ? null : int.tryParse(value);
  }

  Future<void> _submit() async {
    FocusScope.of(context).unfocus();
    if (!_formKey.currentState!.validate()) {
      return;
    }
    setState(() {
      _isLoading = true;
      _error = null;
    });
    final request = ProfileUpdateRequest(
      fullName: _trimmedOrNull(_fullNameController),
      position: _trimmedOrNull(_positionController),
      experienceYears: _intOrNull(_experienceController),
      educationLevel: _trimmedOrNull(_educationController),
      qualificationCourses: _trimmedOrNull(_coursesController),
      certificates: _trimmedOrNull(_certificatesController),
      orgType: _trimmedOrNull(_orgTypeController),
      organizationId: _intOrNull(_organizationIdController),
      regionId: _intOrNull(_regionIdController),
      notificationsEnabled: _notificationsEnabled,
    );
    try {
      await ref.read(authStateProvider.notifier).updateProfile(request);
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Profil yangilandi')),
      );
      Navigator.of(context).pop();
    } on ApiException catch (e) {
      if (!mounted) {
        return;
      }
      setState(() => _error = authErrorMessage(e));
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final profile = ref.watch(authStateProvider).profile;

    return Scaffold(
      appBar: AppBar(title: const Text('Profilni tahrirlash')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 8),
                ErrorBanner(message: _error),
                // Telefon o'zgarmas (R5.4) — faqat ko'rsatiladi, disable.
                TextFormField(
                  initialValue: profile?.phone ?? '',
                  enabled: false,
                  decoration: const InputDecoration(
                    labelText: 'Telefon (o\'zgartirib bo\'lmaydi)',
                    prefixIcon: Icon(Icons.phone_outlined),
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _fullNameController,
                  enabled: !_isLoading,
                  decoration: const InputDecoration(
                    labelText: 'To\'liq ism',
                    prefixIcon: Icon(Icons.person_outline),
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) =>
                      Validators.requiredText(v, label: 'To\'liq ism'),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _positionController,
                  enabled: !_isLoading,
                  decoration: const InputDecoration(
                    labelText: 'Lavozim',
                    prefixIcon: Icon(Icons.work_outline),
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) =>
                      Validators.optionalText(v, label: 'Lavozim'),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _experienceController,
                  keyboardType: TextInputType.number,
                  enabled: !_isLoading,
                  decoration: const InputDecoration(
                    labelText: 'Ish staji (yil)',
                    helperText: 'Butun son, $kExperienceMin–$kExperienceMax',
                    prefixIcon: Icon(Icons.timelapse_outlined),
                    border: OutlineInputBorder(),
                  ),
                  validator: Validators.optionalExperienceYears,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _educationController,
                  enabled: !_isLoading,
                  decoration: const InputDecoration(
                    labelText: 'Ta\'lim darajasi',
                    prefixIcon: Icon(Icons.school_outlined),
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) =>
                      Validators.optionalText(v, label: 'Ta\'lim darajasi'),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _coursesController,
                  enabled: !_isLoading,
                  maxLines: 2,
                  decoration: const InputDecoration(
                    labelText: 'Malaka oshirish kurslari',
                    prefixIcon: Icon(Icons.menu_book_outlined),
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) => Validators.optionalText(
                    v,
                    label: 'Malaka oshirish kurslari',
                  ),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _certificatesController,
                  enabled: !_isLoading,
                  maxLines: 2,
                  decoration: const InputDecoration(
                    labelText: 'Sertifikatlar',
                    prefixIcon: Icon(Icons.verified_outlined),
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) =>
                      Validators.optionalText(v, label: 'Sertifikatlar'),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _orgTypeController,
                  enabled: !_isLoading,
                  decoration: const InputDecoration(
                    labelText: 'Tashkilot turi',
                    prefixIcon: Icon(Icons.category_outlined),
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) =>
                      Validators.optionalText(v, label: 'Tashkilot turi'),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _organizationIdController,
                  keyboardType: TextInputType.number,
                  enabled: !_isLoading,
                  decoration: const InputDecoration(
                    labelText: 'Tashkilot ID',
                    prefixIcon: Icon(Icons.business_outlined),
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) {
                    final value = v?.trim() ?? '';
                    if (value.isNotEmpty && int.tryParse(value) == null) {
                      return 'Tashkilot ID butun son bo\'lishi kerak';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _regionIdController,
                  keyboardType: TextInputType.number,
                  enabled: !_isLoading,
                  decoration: const InputDecoration(
                    labelText: 'Hudud ID',
                    prefixIcon: Icon(Icons.map_outlined),
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) {
                    final value = v?.trim() ?? '';
                    if (value.isNotEmpty && int.tryParse(value) == null) {
                      return 'Hudud ID butun son bo\'lishi kerak';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                SwitchListTile.adaptive(
                  value: _notificationsEnabled,
                  onChanged: _isLoading
                      ? null
                      : (value) {
                          setState(() => _notificationsEnabled = value);
                        },
                  title: const Text('Push bildirishnomalar'),
                  subtitle: const Text('Yangi xabarlar va eslatmalarni olish'),
                  secondary: const Icon(Icons.notifications_active_outlined),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 4),
                ),
                const SizedBox(height: 24),
                LoadingButton(
                  label: 'Saqlash',
                  isLoading: _isLoading,
                  onPressed: _submit,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
