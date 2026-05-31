import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/test_models.dart';
import '../state/app_providers.dart';
import 'app_routes.dart';

/// Faol testlar ro'yxati ekrani (R6.1, 20.2).
class TestsListScreen extends ConsumerStatefulWidget {
  /// Konstruktor.
  const TestsListScreen({super.key});

  @override
  ConsumerState<TestsListScreen> createState() => _TestsListScreenState();
}

class _TestsListScreenState extends ConsumerState<TestsListScreen> {
  late Future<List<TestSummary>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<TestSummary>> _load() {
    return ref.read(testsApiProvider).listTests();
  }

  Future<void> _reload() async {
    setState(() {
      _future = _load();
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Diagnostika testlari')),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: FutureBuilder<List<TestSummary>>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return ListView(
                children: const [
                  SizedBox(height: 180),
                  Center(child: CircularProgressIndicator()),
                ],
              );
            }

            if (snapshot.hasError) {
              return ListView(
                children: [
                  const SizedBox(height: 96),
                  Center(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 24),
                      child: Column(
                        children: [
                          const Icon(Icons.error_outline, size: 48),
                          const SizedBox(height: 12),
                          const Text(
                            'Testlarni yuklab bo\'lmadi',
                            style: TextStyle(fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            '${snapshot.error}',
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 12),
                          FilledButton.icon(
                            onPressed: _reload,
                            icon: const Icon(Icons.refresh),
                            label: const Text('Qayta urinish'),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              );
            }

            final tests = snapshot.data ?? const <TestSummary>[];
            if (tests.isEmpty) {
              return ListView(
                children: const [
                  SizedBox(height: 120),
                  Center(
                    child: Padding(
                      padding: EdgeInsets.symmetric(horizontal: 24),
                      child: Column(
                        children: [
                          Icon(Icons.assignment_outlined, size: 56),
                          SizedBox(height: 10),
                          Text(
                            'Hozircha faol testlar mavjud emas',
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              );
            }

            return ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: tests.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                final item = tests[index];
                final meta = <String>[
                  if ((item.category ?? '').isNotEmpty) item.category!,
                  if (item.durationMinutes != null)
                    '${item.durationMinutes} daqiqa',
                ].join(' • ');

                return Card(
                  child: ListTile(
                    leading: const Icon(Icons.quiz_outlined),
                    title: Text(item.title),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if ((item.description ?? '').trim().isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.only(top: 4),
                            child: Text(item.description!.trim()),
                          ),
                        if (meta.isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.only(top: 6),
                            child: Text(meta),
                          ),
                      ],
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () {
                      Navigator.of(context).pushNamed(
                        AppRoutes.testTaking,
                        arguments: item.id,
                      );
                    },
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
