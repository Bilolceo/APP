import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/auth_models.dart';
import '../state/app_providers.dart';
import '../state/auth_state.dart';
import 'app_routes.dart';
import 'validators.dart';
import 'widgets/error_banner.dart';
import 'widgets/loading_button.dart';

/// Ro'yxatdan o'tish ekrani (R1.1).
///
/// Backend `RegisterRequest` maydonlariga mos: majburiy `phone`, `password`,
/// `full_name`, `role` hamda ixtiyoriy profil maydonlari (lavozim, ish staji,
/// ta'lim darajasi, tashkilot/hudud ID). Mijoz tomonida format/uzunlik
/// tekshiriladi; muvaffaqiyatda `AuthNotifier.register` avtomatik kirishni ham
/// bajaradi va `AuthGate` home'ga o'tkazadi.
class RegisterScreen extends ConsumerStatefulWidget {
  /// Konstruktor.
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _phoneController = TextEditingController(text: kPhonePrefix);
  final _passwordController = TextEditingController();
  final _fullNameController = TextEditingController();
  final _positionController = TextEditingController();
  final _experienceController = TextEditingController();
  final _educationController = TextEditingController();
  final _organizationIdController = TextEditingController();
  final _regionIdController = TextEditingController();

  String _role = kValidRoles.first;
  bool _obscurePassword = true;

  @override
  void dispose() {
    _phoneController.dispose();
    _passwordController.dispose();
    _fullNameController.dispose();
    _positionController.dispose();
    _experienceController.dispose();
    _educationController.dispose();
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
    final request = RegisterRequest(
      phone: _phoneController.text.trim(),
      password: _passwordController.text,
      fullName: _fullNameController.text.trim(),
      role: _role,
      organizationId: _intOrNull(_organizationIdController),
      regionId: _intOrNull(_regionIdController),
      position: _trimmedOrNull(_positionController),
      experienceYears: _intOrNull(_experienceController),
      educationLevel: _trimmedOrNull(_educationController),
    );
    final ok = await ref.read(authStateProvider.notifier).register(request);
    if (!mounted || !ok) {
      return;
    }
    Navigator.of(context).pushNamedAndRemoveUntil(
      AppRoutes.home,
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authStateProvider);
    final isLoading = authState.isLoading;

    return Scaffold(
      appBar: AppBar(title: const Text('Ro\'yxatdan o\'tish')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 8),
                ErrorBanner(message: authState.errorMessage),
                TextFormField(
                  controller: _phoneController,
                  keyboardType: TextInputType.phone,
                  enabled: !isLoading,
                  decoration: const InputDecoration(
                    labelText: 'Telefon raqami *',
                    hintText: '+998901234567',
                    prefixIcon: Icon(Icons.phone_outlined),
                    border: OutlineInputBorder(),
                  ),
                  validator: Validators.phone,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _passwordController,
                  obscureText: _obscurePassword,
                  enabled: !isLoading,
                  decoration: InputDecoration(
                    labelText: 'Parol *',
                    helperText: 'Parol $kPasswordMinLength–$kPasswordMaxLength belgi',
                    prefixIcon: const Icon(Icons.lock_outline),
                    border: const OutlineInputBorder(),
                    suffixIcon: IconButton(
                      icon: Icon(_obscurePassword
                          ? Icons.visibility_outlined
                          : Icons.visibility_off_outlined),
                      onPressed: () => setState(
                        () => _obscurePassword = !_obscurePassword,
                      ),
                    ),
                  ),
                  validator: Validators.password,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _fullNameController,
                  enabled: !isLoading,
                  decoration: const InputDecoration(
                    labelText: 'To\'liq ism *',
                    prefixIcon: Icon(Icons.person_outline),
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) =>
                      Validators.requiredText(v, label: 'To\'liq ism'),
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  value: _role,
                  decoration: const InputDecoration(
                    labelText: 'Rol *',
                    prefixIcon: Icon(Icons.badge_outlined),
                    border: OutlineInputBorder(),
                  ),
                  items: kValidRoles
                      .map((role) => DropdownMenuItem<String>(
                            value: role,
                            child: Text(role),
                          ))
                      .toList(),
                  onChanged: isLoading
                      ? null
                      : (value) {
                          if (value != null) {
                            setState(() => _role = value);
                          }
                        },
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _positionController,
                  enabled: !isLoading,
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
                  enabled: !isLoading,
                  decoration: const InputDecoration(
                    labelText: 'Ish staji (yil)',
                    prefixIcon: Icon(Icons.timelapse_outlined),
                    border: OutlineInputBorder(),
                  ),
                  validator: Validators.optionalExperienceYears,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _educationController,
                  enabled: !isLoading,
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
                  controller: _organizationIdController,
                  keyboardType: TextInputType.number,
                  enabled: !isLoading,
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
                  enabled: !isLoading,
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
                const SizedBox(height: 24),
                LoadingButton(
                  label: 'Ro\'yxatdan o\'tish',
                  isLoading: isLoading,
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
