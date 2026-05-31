import '../models/json_utils.dart';
import '../models/recommendation_models.dart';
import 'api_client.dart';
import 'endpoints.dart';

/// Tavsiyalar domeni API mijozi (R10).
class RecommendationsApi {
  final ApiClient _client;

  /// Domen mijozini yaratadi.
  const RecommendationsApi(this._client);

  /// Joriy foydalanuvchining so'nggi natijasiga bog'langan tavsiyalar (R10.2).
  Future<List<Recommendation>> mine() {
    return _client.getJson(
      Endpoints.recommendationsMe,
      parse: (data) => JsonParse.asList(data, Recommendation.fromJson),
    );
  }

  /// Berilgan natijaga bog'langan tavsiyalarni qaytaradi (R10.3).
  Future<List<Recommendation>> byResult(int resultId) {
    return _client.getJson(
      Endpoints.recommendationsByResult(resultId),
      parse: (data) => JsonParse.asList(data, Recommendation.fromJson),
    );
  }
}
