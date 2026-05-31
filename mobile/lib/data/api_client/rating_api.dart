import '../models/json_utils.dart';
import '../models/rating_models.dart';
import 'api_client.dart';
import 'endpoints.dart';

/// Reyting domeni API mijozi (R12).
class RatingApi {
  final ApiClient _client;

  /// Domen mijozini yaratadi.
  const RatingApi(this._client);

  /// Anonim reytingni qaytaradi (R12.1–R12.5).
  ///
  /// [scope] — reyting kesimi: `overall` (standart), `region`, `organization`
  /// yoki `competency`.
  Future<RatingResponse> get({String scope = 'overall'}) {
    return _client.getJson(
      Endpoints.rating,
      queryParameters: {'scope': scope},
      parse: (data) => RatingResponse.fromJson(JsonParse.asMap(data)),
    );
  }
}
