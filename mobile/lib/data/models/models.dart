/// DTO (Data Transfer Object) modellari — barrel (re-export) fayli.
///
/// Backend Pydantic sxemalariga (`app/api/schemas/*.py`) mos to'liq DTO
/// modellar domen bo'yicha alohida fayllarda e'lon qilinadi va shu yerdan
/// qayta eksport qilinadi. Har bir model `fromJson`/`toJson` metodlariga ega,
/// o'zgarmas (immutable) va null-safety'ga mos.
///
/// Foydalanish:
/// ```dart
/// import 'package:mtt_menejer_diagnostika/data/models/models.dart';
/// final tokens = AuthTokens.fromJson(jsonMap);
/// ```

export 'analytics_models.dart';
export 'api_error.dart';
export 'auth_models.dart';
export 'device_models.dart';
export 'json_utils.dart';
export 'portfolio_models.dart';
export 'rating_models.dart';
export 'recommendation_models.dart';
export 'result_models.dart';
export 'test_models.dart';
export 'user_models.dart';
