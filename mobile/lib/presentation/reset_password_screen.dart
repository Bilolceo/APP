import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/api_error.dart';
import '../state/app_providers.dart';
import '../state/auth_state.dart';
import 'app_routes.dart';
import 'validators.dart';
import 'widgets/error_banner.dart';
import 'widgets/loading_button.dart';

/// Parolni tiklash ekrani — kod + yangi parol (R3.3–R3.7).
///
/// Telefon raqami `Navigator` argumenti orqali (forgot-password ekranidan)
/// uzatiladi; bo'lmasa qo'lda kiritiladi. 6 raqamli kod va yangi parolni
/// tekshirib, `AuthNotifier.resetPassword` ni chaqiradi; muvaffaqiyatda login
/// ekraniga qaytaradi.
class ResetPasswordScreen extends ConsumerStatefulWidget {
  /// Forgot-password oqimidan uzatilgan telefon raqami (ixtiyoriy).
  final String? phone;

  /// Konstruktor.
  const ResetPasswordScreen({super.key, this.phone});

  @override
  ConsumerState<ResetPasswordScreen> createState() =>
      _ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends ConsumerState<ResetPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _phoneController;
  final _codeController = TextEditingController();
  final _newPasswordController = TextEditingController();
  bool _obscurePassword = true;
  bool _isLoading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final initialPhone =
        (widget.phone == null || widget.phone!.isEmpty) ? kPhonePrefix : widget.phone!;
    _phoneController = TextEditingController(text: initialPhone);
  }

  @override
  void dispose() {
    _phoneController.dispose();
    _codeController.dispose();
    _newPasswordController.dispose();
    super.dispose();
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
    try {
      final response = await ref.read(authStateProvider.notifier).resetPassword(
            phone: _phoneController.text.trim(),
            code: _codeController.text.trim(),
            newPassword: _newPasswordController.text,
          );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(response.message)),
      );
      Navigator.of(context).pushNamedAndRemoveUntil(
        AppRoutes.login,
        (route) => false,
      );
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
    return Scaffold(
      appBar: AppBar(title: const Text('Yangi parol')),
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
                TextFormField(
                  controller: _phoneController,
                  keyboardType: TextInputType.phone,
                  enabled: !_isLoading,
                  decoration: const InputDecoration(
                    labelText: 'Telefon raqami',
                    prefixIcon: Icon(Icons.phone_outlined),
                    border: OutlineInputBorder(),
                  ),
                  validator: Validators.phone,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _codeController,
                  keyboardType: TextInputType.number,
                  enabled: !_isLoading,
                  decoration: const InputDecoration(
                    labelText: 'Tasdiqlash kodi',
                    hintText: '6 ta raqam',
                    prefixIcon: Icon(Icons.pin_outlined),
                    border: OutlineInputBorder(),
                  ),
                  validator: Validators.resetCode,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _newPasswordController,
                  obscureText: _obscurePassword,
                  enabled: !_isLoading,
                  decoration: InputDecoration(
                    labelText: 'Yangi parol',
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
                  validator: Validators.newPassword,
                ),
                const SizedBox(height: 24),
                LoadingButton(
                  label: 'Parolni yangilash',
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
