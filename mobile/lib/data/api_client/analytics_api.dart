import '../models/analytics_models.dart';
import '../models/json_utils.dart';
import 'api_client.dart';
import 'endpoints.dart';

/// Analitika domeni API mijozi (R9, R15).
class AnalyticsApi {
  final ApiClient _client;

  /// Domen mijozini yaratadi.
  const AnalyticsApi(this._client);

  /// Joriy foydalanuvchining shaxsiy analitikasini qaytaradi (R9.1–R9.7).
  Future<AnalyticsResponse> mine() {
    return _client.getJson(
      Endpoints.analyticsMe,
      parse: (data) => AnalyticsResponse.fromJson(JsonParse.asMap(data)),
    );
  }

  /// Tashkilot kesimi bo'yicha jamlangan analitikani qaytaradi (R15.4).
  Future<SectionAnalytics> byOrganization(int organizationId) {
    return _client.getJson(
      Endpoints.analyticsOrganization(organizationId),
      parse: (data) => SectionAnalytics.fromJson(JsonParse.asMap(data)),
    );
  }

  /// Hudud kesimi bo'yicha jamlangan analitikani qaytaradi (R15.3).
  Future<SectionAnalytics> byRegion(int regionId) {
    return _client.getJson(
      Endpoints.analyticsRegion(regionId),
      parse: (data) => SectionAnalytics.fromJson(JsonParse.asMap(data)),
    );
  }
}
