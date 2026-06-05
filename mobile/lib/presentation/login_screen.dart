import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/app_providers.dart';
import '../state/auth_state.dart';
import 'app_routes.dart';
import 'validators.dart';
import 'widgets/error_banner.dart';
import 'widgets/loading_button.dart';

/// Tizimga kirish ekrani (R2.1).
///
/// Telefon (+998, 13 belgi) va parol (8–64) maydonlarini mijoz tomonida
/// tekshiradi, so'ng `AuthNotifier.login` ni chaqiradi. Yuklanish va xato
/// holatlarini ko'rsatadi; ro'yxatdan o'tish va parolni unutish ekranlariga
/// havola beradi. Muvaffaqiyatda yo'naltirishni `AuthGate` (global holat)
/// boshqaradi.
class LoginScreen extends ConsumerStatefulWidget {
  /// Konstruktor.
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _phoneController = TextEditingController(text: kPhonePrefix);
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;

  @override
  void dispose() {
    _phoneController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    FocusScope.of(context).unfocus();
    if (!_formKey.currentState!.validate()) {
      return;
    }
    final ok = await ref.read(authStateProvider.notifier).login(
          phone: _phoneController.text.trim(),
          password: _passwordController.text,
        );
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
      appBar: AppBar(title: const Text('Tizimga kirish')),
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
                    labelText: 'Telefon raqami',
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
                    labelText: 'Parol',
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
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(
                    onPressed: isLoading
                        ? null
                        : () => Navigator.of(context)
                            .pushNamed(AppRoutes.forgotPassword),
                    child: const Text('Parolni unutdingizmi?'),
                  ),
                ),
                const SizedBox(height: 8),
                LoadingButton(
                  label: 'Kirish',
                  isLoading: isLoading,
                  onPressed: _submit,
                ),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Text('Hisobingiz yo\'qmi?'),
                    TextButton(
                      onPressed: isLoading
                          ? null
                          : () => Navigator.of(context)
                              .pushNamed(AppRoutes.register),
                      child: const Text('Ro\'yxatdan o\'tish'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
