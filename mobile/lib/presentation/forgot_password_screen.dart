import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/api_error.dart';
import '../state/app_providers.dart';
import '../state/auth_state.dart';
import 'app_routes.dart';
import 'validators.dart';
import 'widgets/error_banner.dart';
import 'widgets/loading_button.dart';

/// Parolni unutish ekrani — tasdiqlash kodini so'raydi (R3.1, R3.2).
///
/// Telefon raqamini tekshirib, `AuthNotifier.forgotPassword` ni chaqiradi.
/// Backend hisob mavjudligini oshkor qilmaydigan umumiy javob qaytaradi
/// (R3.2), shuning uchun har qanday muvaffaqiyatda foydalanuvchi reset-password
/// ekraniga (kod kiritishga) o'tkaziladi.
class ForgotPasswordScreen extends ConsumerStatefulWidget {
  /// Konstruktor.
  const ForgotPasswordScreen({super.key});

  @override
  ConsumerState<ForgotPasswordScreen> createState() =>
      _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _phoneController = TextEditingController(text: kPhonePrefix);
  bool _isLoading = false;
  String? _error;

  @override
  void dispose() {
    _phoneController.dispose();
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
    final phone = _phoneController.text.trim();
    try {
      final response =
          await ref.read(authStateProvider.notifier).forgotPassword(phone);
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(response.message)),
      );
      Navigator.of(context).pushReplacementNamed(
        AppRoutes.resetPassword,
        arguments: phone,
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
      appBar: AppBar(title: const Text('Parolni tiklash')),
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
                Text(
                  'Ro\'yxatdan o\'tgan telefon raqamingizni kiriting. '
                  'Sizga 6 raqamli tasdiqlash kodi yuboriladi.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 24),
                TextFormField(
                  controller: _phoneController,
                  keyboardType: TextInputType.phone,
                  enabled: !_isLoading,
                  decoration: const InputDecoration(
                    labelText: 'Telefon raqami',
                    hintText: '+998901234567',
                    prefixIcon: Icon(Icons.phone_outlined),
                    border: OutlineInputBorder(),
                  ),
                  validator: Validators.phone,
                ),
                const SizedBox(height: 24),
                LoadingButton(
                  label: 'Kod yuborish',
                  isLoading: _isLoading,
                  onPressed: _submit,
                ),
                const SizedBox(height: 12),
                TextButton(
                  onPressed: _isLoading
                      ? null
                      : () => Navigator.of(context).pushReplacementNamed(
                            AppRoutes.resetPassword,
                            arguments: _phoneController.text.trim(),
                          ),
                  child: const Text('Menda kod bor'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
