import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/analytics_models.dart';
import '../state/app_providers.dart';

/// Shaxsiy analitika ekrani (R9, 20.2).
///
/// Radar/progress/line/card ko'rinishlarida analitika ma'lumotini ko'rsatadi.
class AnalyticsScreen extends ConsumerStatefulWidget {
  /// Konstruktor.
  const AnalyticsScreen({super.key});

  @override
  ConsumerState<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends ConsumerState<AnalyticsScreen> {
  late Future<AnalyticsResponse> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<AnalyticsResponse> _load() {
    return ref.read(analyticsApiProvider).mine();
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
      appBar: AppBar(title: const Text('Analitika')),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: FutureBuilder<AnalyticsResponse>(
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
                          const Text('Analitikani yuklab bo\'lmadi'),
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
            if (data == null || !data.hasResults) {
              return ListView(
                children: const [
                  SizedBox(height: 120),
                  Center(
                    child: Padding(
                      padding: EdgeInsets.symmetric(horizontal: 24),
                      child: Column(
                        children: [
                          Icon(Icons.insights_outlined, size: 56),
                          SizedBox(height: 10),
                          Text(
                            'Analitika uchun hali natijalar mavjud emas',
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              );
            }

            final distribution = data.distribution;
            final labels = distribution
                .map((e) => e.competencyName ?? 'K${e.competencyId}')
                .toList(growable: false);
            final values = distribution
                .map((e) => e.percentage.clamp(0, 100).toDouble())
                .toList(growable: false);

            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    _MetricCard(
                      title: 'Umumiy ball',
                      value: '${data.overallScore.toStringAsFixed(2)}%',
                      icon: Icons.speed_outlined,
                    ),
                    _MetricCard(
                      title: 'Natijalar soni',
                      value: '${data.resultCount}',
                      icon: Icons.fact_check_outlined,
                    ),
                    _MetricCard(
                      title: 'O\'sish farqi',
                      value: data.growthDiff == null
                          ? 'Mavjud emas'
                          : '${data.growthDiff!.toStringAsFixed(2)}%',
                      icon: Icons.trending_up_outlined,
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Text(
                  'Radar diagramma',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Card(
                  child: SizedBox(
                    height: 260,
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: CustomPaint(
                        painter: _RadarChartPainter(
                          labels: labels,
                          values: values,
                          color: Theme.of(context).colorScheme.primary,
                          labelColor: Theme.of(context).colorScheme.onSurface,
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  'O\'sish dinamikasi (line)',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Card(
                  child: SizedBox(
                    height: 220,
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: CustomPaint(
                        painter: _LineChartPainter(
                          values: data.dynamics
                              .map((e) => e.percentage.clamp(0, 100).toDouble())
                              .toList(growable: false),
                          color: Theme.of(context).colorScheme.tertiary,
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  'Kompetensiya progressi',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                ...distribution.map(
                  (item) => Card(
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            item.competencyName ?? 'Kompetensiya #${item.competencyId}',
                            style: Theme.of(context).textTheme.titleSmall,
                          ),
                          const SizedBox(height: 6),
                          LinearProgressIndicator(
                            value:
                                item.percentage.clamp(0, 100).toDouble() / 100,
                          ),
                          const SizedBox(height: 6),
                          Text(
                            '${item.percentage.toStringAsFixed(2)}% • ${item.level}',
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
}

class _MetricCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;

  const _MetricCard({
    required this.title,
    required this.value,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 160,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon),
              const SizedBox(height: 8),
              Text(title, style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: 4),
              Text(
                value,
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LineChartPainter extends CustomPainter {
  final List<double> values;
  final Color color;

  _LineChartPainter({required this.values, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final gridPaint = Paint()
      ..color = Colors.grey.withOpacity(0.3)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    final linePaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5;

    const leftPadding = 24.0;
    const bottomPadding = 18.0;
    final chartRect = Rect.fromLTWH(
      leftPadding,
      8,
      size.width - leftPadding - 8,
      size.height - bottomPadding - 8,
    );

    for (var i = 0; i <= 4; i++) {
      final y = chartRect.top + (chartRect.height / 4) * i;
      canvas.drawLine(
        Offset(chartRect.left, y),
        Offset(chartRect.right, y),
        gridPaint,
      );
    }

    if (values.isEmpty) {
      return;
    }

    final path = Path();
    for (var i = 0; i < values.length; i++) {
      final x = values.length == 1
          ? chartRect.center.dx
          : chartRect.left + (chartRect.width * i / (values.length - 1));
      final normalized = values[i].clamp(0, 100).toDouble() / 100;
      final y = chartRect.bottom - (chartRect.height * normalized);
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }

      canvas.drawCircle(Offset(x, y), 2.5, Paint()..color = color);
    }

    canvas.drawPath(path, linePaint);
  }

  @override
  bool shouldRepaint(covariant _LineChartPainter oldDelegate) {
    return oldDelegate.values != values || oldDelegate.color != color;
  }
}

class _RadarChartPainter extends CustomPainter {
  final List<String> labels;
  final List<double> values;
  final Color color;
  final Color labelColor;

  _RadarChartPainter({
    required this.labels,
    required this.values,
    required this.color,
    required this.labelColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (labels.isEmpty || values.isEmpty || labels.length != values.length) {
      return;
    }

    final center = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) * 0.34;

    final gridPaint = Paint()
      ..color = Colors.grey.withOpacity(0.35)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    final fillPaint = Paint()
      ..color = color.withOpacity(0.2)
      ..style = PaintingStyle.fill;

    final borderPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;

    final angleStep = (2 * math.pi) / labels.length;
    final startAngle = -math.pi / 2;

    for (var level = 1; level <= 4; level++) {
      final path = Path();
      final levelRadius = radius * (level / 4);
      for (var i = 0; i < labels.length; i++) {
        final angle = startAngle + angleStep * i;
        final point = Offset(
          center.dx + math.cos(angle) * levelRadius,
          center.dy + math.sin(angle) * levelRadius,
        );
        if (i == 0) {
          path.moveTo(point.dx, point.dy);
        } else {
          path.lineTo(point.dx, point.dy);
        }
      }
      path.close();
      canvas.drawPath(path, gridPaint);
    }

    final dataPath = Path();
    for (var i = 0; i < values.length; i++) {
      final angle = startAngle + angleStep * i;
      final valueRadius = radius * (values[i].clamp(0, 100).toDouble() / 100);
      final point = Offset(
        center.dx + math.cos(angle) * valueRadius,
        center.dy + math.sin(angle) * valueRadius,
      );
      if (i == 0) {
        dataPath.moveTo(point.dx, point.dy);
      } else {
        dataPath.lineTo(point.dx, point.dy);
      }
      canvas.drawCircle(point, 2.3, Paint()..color = color);
    }
    dataPath.close();

    canvas.drawPath(dataPath, fillPaint);
    canvas.drawPath(dataPath, borderPaint);

    for (var i = 0; i < labels.length; i++) {
      final angle = startAngle + angleStep * i;
      final lineEnd = Offset(
        center.dx + math.cos(angle) * radius,
        center.dy + math.sin(angle) * radius,
      );
      final labelPoint = Offset(
        center.dx + math.cos(angle) * (radius + 18),
        center.dy + math.sin(angle) * (radius + 18),
      );

      canvas.drawLine(center, lineEnd, gridPaint);

      final textPainter = TextPainter(
        text: TextSpan(
          text: labels[i],
          style: TextStyle(fontSize: 10, color: labelColor),
        ),
        textDirection: TextDirection.ltr,
        maxLines: 1,
      )..layout(maxWidth: 72);

      textPainter.paint(
        canvas,
        Offset(
          labelPoint.dx - textPainter.width / 2,
          labelPoint.dy - textPainter.height / 2,
        ),
      );
    }
  }

  @override
  bool shouldRepaint(covariant _RadarChartPainter oldDelegate) {
    return oldDelegate.labels != labels ||
        oldDelegate.values != values ||
        oldDelegate.color != color ||
        oldDelegate.labelColor != labelColor;
  }
}
