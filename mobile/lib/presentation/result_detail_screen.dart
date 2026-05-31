import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/result_models.dart';
import '../state/app_providers.dart';

/// Natija tafsiloti ekrani (R8.7, 20.2).
class ResultDetailScreen extends ConsumerStatefulWidget {
  /// Natija identifikatori.
  final int resultId;

  /// Konstruktor.
  const ResultDetailScreen({super.key, required this.resultId});

  @override
  ConsumerState<ResultDetailScreen> createState() => _ResultDetailScreenState();
}

class _ResultDetailScreenState extends ConsumerState<ResultDetailScreen> {
  late Future<ResultDetail> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<ResultDetail> _load() {
    return ref.read(testsApiProvider).getResult(widget.resultId);
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
      appBar: AppBar(title: const Text('Natija tafsiloti')),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: FutureBuilder<ResultDetail>(
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
                          const Text('Natija tafsilotini yuklab bo\'lmadi'),
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

            final data = snapshot.data;
            if (data == null) {
              return ListView(
                children: const [
                  SizedBox(height: 120),
                  Center(child: Text('Ma\'lumot topilmadi')),
                ],
              );
            }

            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Umumiy natija',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        Text('Daraja: ${data.level}'),
                        Text(
                          'Foiz: ${data.percentage.toStringAsFixed(2)}%',
                        ),
                        Text(
                          'Ball: ${data.totalScore.toStringAsFixed(2)} / '
                          '${data.maxScore.toStringAsFixed(2)}',
                        ),
                        if (data.createdAt != null)
                          Text('Sana: ${_formatDateTime(data.createdAt!)}'),
                        if (data.nextRetakeDate != null)
                          Text(
                            'Qayta topshirish: ${_formatDate(data.nextRetakeDate!)}',
                          ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Kompetensiya natijalari',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                if (data.competencyResults.isEmpty)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(16),
                      child: Text('Kompetensiya bo\'yicha tafsilot mavjud emas'),
                    ),
                  )
                else
                  ...data.competencyResults.map(
                    (item) => Card(
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Kompetensiya #${item.competencyId}'),
                            const SizedBox(height: 6),
                            LinearProgressIndicator(
                              value:
                                  item.percentage.clamp(0, 100).toDouble() /
                                      100,
                            ),
                            const SizedBox(height: 6),
                            Text(
                              '${item.percentage.toStringAsFixed(2)}% '
                              '(${item.score.toStringAsFixed(2)} / '
                              '${item.maxScore.toStringAsFixed(2)})',
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
              ],
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
