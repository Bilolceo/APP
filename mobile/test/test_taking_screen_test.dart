import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/api_client.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/auth_events.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/tests_api.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/token_store.dart';
import 'package:mtt_menejer_diagnostika/data/models/result_models.dart';
import 'package:mtt_menejer_diagnostika/data/models/test_models.dart';
import 'package:mtt_menejer_diagnostika/presentation/app_routes.dart';
import 'package:mtt_menejer_diagnostika/presentation/test_taking_screen.dart';
import 'package:mtt_menejer_diagnostika/state/app_providers.dart';

ApiClient _dummyApiClient() {
  return ApiClient.withDio(
    dio: Dio(BaseOptions(baseUrl: 'http://localhost')),
    tokenStore: InMemoryTokenStore(),
    authEvents: AuthEvents(),
  );
}

class _FakeTestsApi extends TestsApi {
  final TestDetail detail;
  final StartSessionResponse session;
  final TestResult submitResponse;

  SubmitRequest? lastSubmit;

  _FakeTestsApi({
    required this.detail,
    required this.session,
    required this.submitResponse,
  }) : super(_dummyApiClient());

  @override
  Future<TestDetail> getTest(int testId) async => detail;

  @override
  Future<StartSessionResponse> startTest(int testId) async => session;

  @override
  Future<TestResult> submitTest(int testId, SubmitRequest request) async {
    lastSubmit = request;
    return submitResponse;
  }
}

void main() {
  testWidgets('TestTakingScreen savollarni ko\'rsatadi va submit qiladi',
      (tester) async {
    final fakeApi = _FakeTestsApi(
      detail: const TestDetail(
        id: 1,
        title: 'Sinov testi',
        questionCount: 2,
        questions: [
          Question(
            id: 10,
            questionText: 'Birinchi savol',
            questionType: 'cognitive',
            answers: [
              AnswerOption(id: 100, answerText: 'A variant'),
              AnswerOption(id: 101, answerText: 'B variant'),
            ],
          ),
          Question(
            id: 20,
            questionText: 'Ikkinchi savol',
            questionType: 'likert',
          ),
        ],
      ),
      session: StartSessionResponse(
        id: 77,
        userId: 1,
        testId: 1,
        status: 'in_progress',
        expiresAt: DateTime.now().add(const Duration(minutes: 5)),
      ),
      submitResponse: const TestResult(
        resultId: 501,
        totalScore: 16,
        maxScore: 20,
        percentage: 80,
        level: 'Yaxshi',
      ),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          testsApiProvider.overrideWithValue(fakeApi),
        ],
        child: MaterialApp(
          onGenerateRoute: (settings) {
            if (settings.name == AppRoutes.resultDetail) {
              return MaterialPageRoute<void>(
                builder: (_) => const Scaffold(
                  body: Text('result-detail-page'),
                ),
              );
            }
            return null;
          },
          home: const TestTakingScreen(testId: 1),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('Sinov testi'), findsOneWidget);
    expect(find.textContaining('Birinchi savol'), findsOneWidget);
    expect(find.textContaining('Ikkinchi savol'), findsOneWidget);

    await tester.tap(find.text('A variant'));
    await tester.pump();

    await tester.tap(find.text('5'));
    await tester.pump();

    await tester.tap(find.text('Testni topshirish'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(fakeApi.lastSubmit, isNotNull);
    expect(fakeApi.lastSubmit!.sessionId, 77);
    expect(fakeApi.lastSubmit!.answers.length, 2);
    expect(find.text('result-detail-page'), findsOneWidget);
  });
}
