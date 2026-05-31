import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/result_models.dart';
import '../state/app_providers.dart';
import 'app_routes.dart';

/// Foydalanuvchining natijalari ro'yxati (R8.6, 20.2).
class ResultsScreen extends ConsumerStatefulWidget {
  /// Konstruktor.
  const ResultsScreen({super.key});

  @override
  ConsumerState<ResultsScreen> createState() => _ResultsScreenState();
}

class _ResultsScreenState extends ConsumerState<ResultsScreen> {
  late Future<List<ResultSummary>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<ResultSummary>> _load() {
    return ref.read(testsApiProvider).myResults();
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
      appBar: AppBar(title: const Text('Mening natijalarim')),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: FutureBuilder<List<ResultSummary>>(
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
                          const Text('Natijalarni yuklab bo\'lmadi'),
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

            final items = snapshot.data ?? const <ResultSummary>[];
            if (items.isEmpty) {
              return ListView(
                children: const [
                  SizedBox(height: 120),
                  Center(
                    child: Padding(
                      padding: EdgeInsets.symmetric(horizontal: 24),
                      child: Column(
                        children: [
                          Icon(Icons.fact_check_outlined, size: 56),
                          SizedBox(height: 10),
                          Text(
                            'Hozircha natijalar mavjud emas',
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
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                final item = items[index];
                return Card(
                  child: ListTile(
                    leading: CircleAvatar(
                      child: Text(item.percentage.toStringAsFixed(0)),
                    ),
                    title: Text('Test #${item.testId} • ${item.level}'),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${item.totalScore.toStringAsFixed(2)} / '
                          '${item.maxScore.toStringAsFixed(2)} ball',
                        ),
                        if (item.createdAt != null)
                          Text('Sana: ${_formatDateTime(item.createdAt!)}'),
                        if (item.nextRetakeDate != null)
                          Text(
                            'Qayta topshirish: ${_formatDate(item.nextRetakeDate!)}',
                          ),
                      ],
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () {
                      Navigator.of(context).pushNamed(
                        AppRoutes.resultDetail,
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

  static String _two(int value) => value.toString().padLeft(2, '0');

  static String _formatDate(DateTime date) {
    return '${date.year}-${_two(date.month)}-${_two(date.day)}';
  }

  static String _formatDateTime(DateTime date) {
    return '${_formatDate(date)} ${_two(date.hour)}:${_two(date.minute)}';
  }
}
