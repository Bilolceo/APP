import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/result_models.dart';
import '../data/models/test_models.dart';
import '../state/app_providers.dart';
import 'app_routes.dart';
import 'widgets/loading_button.dart';

/// Test topshirish ekrani (R7.2, R7.3, R7.4, 20.2).
class TestTakingScreen extends ConsumerStatefulWidget {
  /// Test identifikatori.
  final int testId;

  /// Konstruktor.
  const TestTakingScreen({super.key, required this.testId});

  @override
  ConsumerState<TestTakingScreen> createState() => _TestTakingScreenState();
}

class _TestTakingScreenState extends ConsumerState<TestTakingScreen> {
  TestDetail? _detail;
  StartSessionResponse? _session;
  String? _errorMessage;
  bool _isLoading = true;
  bool _isSubmitting = false;

  final Map<int, SubmitAnswer> _answers = <int, SubmitAnswer>{};

  Timer? _countdownTimer;
  Duration? _remaining;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _countdownTimer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final testsApi = ref.read(testsApiProvider);
      final values = await Future.wait<dynamic>([
        testsApi.getTest(widget.testId),
        testsApi.startTest(widget.testId),
      ]);

      final detail = values[0] as TestDetail;
      final session = values[1] as StartSessionResponse;

      if (!mounted) return;
      setState(() {
        _detail = detail;
        _session = session;
        _isLoading = false;
      });
      _initCountdown(session.expiresAt);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _errorMessage = '$error';
        _isLoading = false;
      });
    }
  }

  void _initCountdown(DateTime? expiresAt) {
    _countdownTimer?.cancel();
    if (expiresAt == null) {
      setState(() {
        _remaining = null;
      });
      return;
    }

    void tick() {
      final now = DateTime.now();
      final diff = expiresAt.difference(now);
      setState(() {
        _remaining = diff.isNegative ? Duration.zero : diff;
      });
      if (diff.isNegative || diff.inSeconds <= 0) {
        _countdownTimer?.cancel();
      }
    }

    tick();
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (_) => tick());
  }

  bool _isLikert(Question question) {
    final type = (question.questionType ?? '').toLowerCase();
    return type == 'likert';
  }

  void _pickLikert(Question question, int value) {
    setState(() {
      _answers[question.id] = SubmitAnswer(
        questionId: question.id,
        likertValue: value,
      );
    });
  }

  void _pickOption(Question question, int optionId) {
    setState(() {
      _answers[question.id] = SubmitAnswer(
        questionId: question.id,
        answerId: optionId,
      );
    });
  }

  bool _allQuestionsAnswered() {
    final detail = _detail;
    if (detail == null) return false;

    for (final question in detail.questions) {
      final answer = _answers[question.id];
      if (answer == null) return false;
      if (_isLikert(question)) {
        if (answer.likertValue == null) return false;
      } else {
        if (answer.answerId == null) return false;
      }
    }
    return true;
  }

  Future<void> _submit() async {
    final detail = _detail;
    final session = _session;
    if (detail == null || session == null) return;

    FocusScope.of(context).unfocus();

    if (!_allQuestionsAnswered()) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Iltimos, barcha savollarga javob bering.'),
        ),
      );
      return;
    }

    setState(() {
      _isSubmitting = true;
    });

    try {
      final testsApi = ref.read(testsApiProvider);
      final request = SubmitRequest(
        sessionId: session.id,
        answers: _answers.values.toList(growable: false),
      );
      final TestResult result = await testsApi.submitTest(widget.testId, request);

      if (!mounted) return;
      Navigator.of(context).pushReplacementNamed(
        AppRoutes.resultDetail,
        arguments: result.resultId,
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Topshirishda xato: $error')),
      );
      setState(() {
        _isSubmitting = false;
      });
    }
  }

  String _remainingLabel() {
    final remaining = _remaining;
    if (remaining == null) {
      return 'Cheklanmagan';
    }
    final totalSeconds = remaining.inSeconds;
    if (totalSeconds <= 0) {
      return 'Vaqt tugadi';
    }

    final minutes = totalSeconds ~/ 60;
    final seconds = totalSeconds % 60;
    final mm = minutes.toString().padLeft(2, '0');
    final ss = seconds.toString().padLeft(2, '0');
    return '$mm:$ss';
  }

  @override
  Widget build(BuildContext context) {
    final detail = _detail;

    if (_isLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (_errorMessage != null || detail == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Test')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.error_outline, size: 48),
                const SizedBox(height: 12),
                Text(
                  _errorMessage ?? 'Testni yuklashda xatolik yuz berdi.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                FilledButton.icon(
                  onPressed: _load,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Qayta urinish'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final answeredCount = detail.questions
        .where((q) => _answers.containsKey(q.id))
        .length;
    final totalCount = detail.questions.length;
    final progress = totalCount == 0 ? 0.0 : answeredCount / totalCount;

    return Scaffold(
      appBar: AppBar(
        title: Text(detail.title),
      ),
      body: Column(
        children: [
          Card(
            margin: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                children: [
                  Row(
                    children: [
                      const Icon(Icons.timer_outlined),
                      const SizedBox(width: 8),
                      Text('Qolgan vaqt: ${_remainingLabel()}'),
                      const Spacer(),
                      Text('$answeredCount/$totalCount'),
                    ],
                  ),
                  const SizedBox(height: 10),
                  LinearProgressIndicator(value: progress),
                ],
              ),
            ),
          ),
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
              itemCount: detail.questions.length,
              itemBuilder: (context, index) {
                final question = detail.questions[index];
                return Card(
                  margin: const EdgeInsets.only(bottom: 10),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${index + 1}. ${question.questionText}',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 10),
                        if (_isLikert(question))
                          _LikertChooser(
                            value: _answers[question.id]?.likertValue,
                            onSelected: (value) => _pickLikert(question, value),
                          )
                        else
                          _OptionsChooser(
                            options: question.answers,
                            selectedAnswerId: _answers[question.id]?.answerId,
                            onSelected: (answerId) =>
                                _pickOption(question, answerId),
                          ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          SafeArea(
            top: false,
            minimum: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            child: LoadingButton(
              label: 'Testni topshirish',
              isLoading: _isSubmitting,
              onPressed: _submit,
            ),
          ),
        ],
      ),
    );
  }
}

class _LikertChooser extends StatelessWidget {
  final int? value;
  final ValueChanged<int> onSelected;

  const _LikertChooser({required this.value, required this.onSelected});

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: List<Widget>.generate(5, (index) {
        final score = index + 1;
        return ChoiceChip(
          label: Text(score.toString()),
          selected: value == score,
          onSelected: (_) => onSelected(score),
        );
      }),
    );
  }
}

class _OptionsChooser extends StatelessWidget {
  final List<AnswerOption> options;
  final int? selectedAnswerId;
  final ValueChanged<int> onSelected;

  const _OptionsChooser({
    required this.options,
    required this.selectedAnswerId,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    if (options.isEmpty) {
      return const Text('Variantlar topilmadi');
    }

    return Column(
      children: options
          .map(
            (answer) => RadioListTile<int>(
              value: answer.id,
              groupValue: selectedAnswerId,
              onChanged: (value) {
                if (value != null) {
                  onSelected(value);
                }
              },
              title: Text(answer.answerText),
              dense: true,
              contentPadding: EdgeInsets.zero,
            ),
          )
          .toList(growable: false),
    );
  }
}
