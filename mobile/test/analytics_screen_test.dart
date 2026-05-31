import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/analytics_api.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/api_client.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/auth_events.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/token_store.dart';
import 'package:mtt_menejer_diagnostika/data/models/analytics_models.dart';
import 'package:mtt_menejer_diagnostika/presentation/analytics_screen.dart';
import 'package:mtt_menejer_diagnostika/state/app_providers.dart';

ApiClient _dummyApiClient() {
  return ApiClient.withDio(
    dio: Dio(BaseOptions(baseUrl: 'http://localhost')),
    tokenStore: InMemoryTokenStore(),
    authEvents: AuthEvents(),
  );
}

class _FakeAnalyticsApi extends AnalyticsApi {
  final AnalyticsResponse response;

  _FakeAnalyticsApi(this.response) : super(_dummyApiClient());

  @override
  Future<AnalyticsResponse> mine() async => response;
}

void main() {
  testWidgets('AnalyticsScreen ma\'lumotli holatda asosiy bloklarni ko\'rsatadi',
      (tester) async {
    final fakeApi = _FakeAnalyticsApi(
      const AnalyticsResponse(
        overallScore: 72.5,
        resultCount: 3,
        hasResults: true,
        growthDiff: 4.2,
        distribution: [
          CompetencyDistribution(
            competencyId: 1,
            competencyName: 'Liderlik',
            percentage: 80,
            level: 'Yaxshi',
          ),
        ],
        dynamics: [
          GrowthPoint(percentage: 60),
          GrowthPoint(percentage: 72.5),
        ],
      ),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [analyticsApiProvider.overrideWithValue(fakeApi)],
        child: const MaterialApp(home: AnalyticsScreen()),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Analitika'), findsOneWidget);
    expect(find.text('Umumiy ball'), findsOneWidget);
    expect(find.text('Natijalar soni'), findsOneWidget);
  });

  testWidgets('AnalyticsScreen bo\'sh holatda xabarnoma ko\'rsatadi',
      (tester) async {
    final fakeApi = _FakeAnalyticsApi(
      const AnalyticsResponse(
        overallScore: 0,
        resultCount: 0,
        hasResults: false,
      ),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [analyticsApiProvider.overrideWithValue(fakeApi)],
        child: const MaterialApp(home: AnalyticsScreen()),
      ),
    );

    await tester.pumpAndSettle();

    expect(
      find.text('Analitika uchun hali natijalar mavjud emas'),
      findsOneWidget,
    );
  });
}
