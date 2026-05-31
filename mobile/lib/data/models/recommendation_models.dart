import 'json_utils.dart';

/// Tavsiya DTO modellari (R10).
///
/// Maydon nomlari backend `app/api/schemas/recommendation.py` bilan aniq mos
/// keladi.

/// Natijaga bog'langan bitta tavsiya (R10.2).
///
/// Backend: `RecommendationResponse`.
class Recommendation {
  /// Kompetensiya ID (ixtiyoriy).
  final int? competencyId;

  /// Kompetensiya nomi.
  final String? competencyName;

  /// Baholangan daraja.
  final String? level;

  /// Tavsiya matni (snapshot).
  final String? text;

  /// Modelni yaratadi.
  const Recommendation({
    this.competencyId,
    this.competencyName,
    this.level,
    this.text,
  });

  /// JSON xaritadan yaratadi.
  factory Recommendation.fromJson(Map<String, dynamic> json) {
    return Recommendation(
      competencyId: JsonParse.asIntOrNull(json['competency_id']),
      competencyName: JsonParse.asStringOrNull(json['competency_name']),
      level: JsonParse.asStringOrNull(json['level']),
      text: JsonParse.asStringOrNull(json['text']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'competency_id': competencyId,
        'competency_name': competencyName,
        'level': level,
        'text': text,
      };
}
