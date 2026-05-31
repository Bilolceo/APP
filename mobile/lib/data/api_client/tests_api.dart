import '../models/json_utils.dart';
import '../models/result_models.dart';
import '../models/test_models.dart';
import 'api_client.dart';
import 'endpoints.dart';

/// Test, sessiya va natija domeni API mijozi (R6, R7, R8).
class TestsApi {
  final ApiClient _client;

  /// Domen mijozini yaratadi.
  const TestsApi(this._client);

  /// Faol testlar ro'yxatini qaytaradi (R6.1).
  Future<List<TestSummary>> listTests() {
    return _client.getJson(
      Endpoints.tests,
      parse: (data) => JsonParse.asList(data, TestSummary.fromJson),
    );
  }

  /// Test tafsilotini va savollarini qaytaradi (R6.3).
  Future<TestDetail> getTest(int testId) {
    return _client.getJson(
      Endpoints.test(testId),
      parse: (data) => TestDetail.fromJson(JsonParse.asMap(data)),
    );
  }

  /// Yangi sessiya boshlaydi yoki mavjudini davom ettiradi (R7.1, R7.10).
  Future<StartSessionResponse> startTest(int testId) {
    return _client.postJson(
      Endpoints.startTest(testId),
      parse: (data) => StartSessionResponse.fromJson(JsonParse.asMap(data)),
    );
  }

  /// Javoblarni topshiradi va hisoblangan natijani qaytaradi (R7.6, R8.6).
  Future<TestResult> submitTest(int testId, SubmitRequest request) {
    return _client.postJson(
      Endpoints.submitTest(testId),
      data: request.toJson(),
      parse: (data) => TestResult.fromJson(JsonParse.asMap(data)),
    );
  }

  /// Joriy foydalanuvchining barcha natijalarini qaytaradi (R8.6).
  Future<List<ResultSummary>> myResults() {
    return _client.getJson(
      Endpoints.myResults,
      parse: (data) => JsonParse.asList(data, ResultSummary.fromJson),
    );
  }

  /// Natija tafsilotini egalik tekshiruvi bilan qaytaradi (R8.7).
  Future<ResultDetail> getResult(int resultId) {
    return _client.getJson(
      Endpoints.result(resultId),
      parse: (data) => ResultDetail.fromJson(JsonParse.asMap(data)),
    );
  }
}
