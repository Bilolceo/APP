import 'package:flutter/material.dart';

import 'app_routes.dart';

/// Onboarding ekrani — 3 sahifali tanishtiruv (TZ 7-bo'lim: onboarding×3).
///
/// Foydalanuvchi sahifalarni ko'rib chiqadi va oxirgi sahifada "Boshlash"
/// tugmasi orqali login ekraniga o'tadi. Bu ekran kirilmagan oqimning kirish
/// nuqtasi sifatida `AuthGate` tomonidan ko'rsatiladi.
class OnboardingScreen extends StatefulWidget {
  /// Konstruktor.
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _controller = PageController();
  int _page = 0;

  static const List<_OnboardingPage> _pages = <_OnboardingPage>[
    _OnboardingPage(
      icon: Icons.assignment_outlined,
      title: 'Diagnostika testlari',
      description:
          'Kognitiv, kompetensiya, refleksiv va situatsion testlar orqali '
          'kompetensiyalaringizni baholang.',
    ),
    _OnboardingPage(
      icon: Icons.insights_outlined,
      title: 'Tahlil va tavsiyalar',
      description:
          'Natijalaringiz bo\'yicha shaxsiy tahlil va rivojlanish '
          'tavsiyalarini oling.',
    ),
    _OnboardingPage(
      icon: Icons.cloud_off_outlined,
      title: 'Offline rejim',
      description:
          'Internet bo\'lmaganda ham yuklangan testlarni ko\'ring; aloqa '
          'tiklanganda natijalar avtomatik yuboriladi.',
    ),
  ];

  bool get _isLastPage => _page == _pages.length - 1;

  void _goToLogin() {
    Navigator.of(context).pushReplacementNamed(AppRoutes.login);
  }

  void _next() {
    if (_isLastPage) {
      _goToLogin();
    } else {
      _controller.nextPage(
        duration: const Duration(milliseconds: 280),
        curve: Curves.easeInOut,
      );
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: _isLastPage ? null : _goToLogin,
                child: const Text('O\'tkazib yuborish'),
              ),
            ),
            Expanded(
              child: PageView.builder(
                controller: _controller,
                itemCount: _pages.length,
                onPageChanged: (index) => setState(() => _page = index),
                itemBuilder: (context, index) {
                  final page = _pages[index];
                  return Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 32),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(page.icon, size: 96, color: scheme.primary),
                        const SizedBox(height: 32),
                        Text(
                          page.title,
                          style: Theme.of(context).textTheme.headlineSmall,
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          page.description,
                          style: Theme.of(context).textTheme.bodyLarge,
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
            _PageDots(count: _pages.length, active: _page),
            Padding(
              padding: const EdgeInsets.all(24),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _next,
                  child: Text(_isLastPage ? 'Boshlash' : 'Keyingi'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OnboardingPage {
  final IconData icon;
  final String title;
  final String description;

  const _OnboardingPage({
    required this.icon,
    required this.title,
    required this.description,
  });
}

class _PageDots extends StatelessWidget {
  final int count;
  final int active;

  const _PageDots({required this.count, required this.active});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List<Widget>.generate(count, (index) {
        final isActive = index == active;
        return AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          margin: const EdgeInsets.symmetric(horizontal: 4),
          height: 8,
          width: isActive ? 24 : 8,
          decoration: BoxDecoration(
            color: isActive ? scheme.primary : scheme.primaryContainer,
            borderRadius: BorderRadius.circular(4),
          ),
        );
      }),
    );
  }
}
