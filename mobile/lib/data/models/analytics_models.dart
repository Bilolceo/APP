import 'json_utils.dart';

/// Analitika DTO modellari (R9, R15).
///
/// Maydon nomlari backend `app/api/schemas/analytics.py` bilan aniq mos keladi.

/// Kompetensiya taqsimotidagi bitta yozuv (R9.2).
///
/// Backend: `CompetencyDistributionResponse`. Radar / progress bar / kartochka
/// uchun ma'lumot.
class CompetencyDistribution {
  /// Kompetensiya ID.
  final int competencyId;

  /// Kompetensiya nomi.
  final String? competencyName;

  /// Jamlangan foiz (0–100).
  final double percentage;

  /// Jamlangan foizdan aniqlangan daraja.
  final String level;

  /// Modelni yaratadi.
  const CompetencyDistribution({
    required this.competencyId,
    this.competencyName,
    required this.percentage,
    required this.level,
  });

  /// JSON xaritadan yaratadi.
  factory CompetencyDistribution.fromJson(Map<String, dynamic> json) {
    return CompetencyDistribution(
      competencyId: JsonParse.asInt(json['competency_id']),
      competencyName: JsonParse.asStringOrNull(json['competency_name']),
      percentage: JsonParse.asDouble(json['percentage']),
      level: JsonParse.asString(json['level']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'competency_id': competencyId,
        'competency_name': competencyName,
        'percentage': percentage,
        'level': level,
      };
}

/// O'sish dinamikasidagi bitta nuqta — sana bilan belgilangan foiz (R9.1).
///
/// Backend: `GrowthPointResponse`.
class GrowthPoint {
  /// Natija sanasi/vaqti.
  final DateTime? achievedAt;

  /// Shu natijaning umumiy foizi.
  final double percentage;

  /// Modelni yaratadi.
  const GrowthPoint({this.achievedAt, required this.percentage});

  /// JSON xaritadan yaratadi.
  factory GrowthPoint.fromJson(Map<String, dynamic> json) {
    return GrowthPoint(
      achievedAt: JsonParse.asDateTimeOrNull(json['achieved_at']),
      percentage: JsonParse.asDouble(json['percentage']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'achieved_at': achievedAt?.toIso8601String(),
        'percentage': percentage,
      };
}

/// Kompetensiyaga ishora (kuchli / rivojlantirilishi lozim) (R9.5, R9.6).
///
/// Backend: `CompetencyRefResponse`.
class CompetencyRef {
  /// Kompetensiya ID.
  final int competencyId;

  /// Kompetensiya nomi.
  final String? competencyName;

  /// Modelni yaratadi.
  const CompetencyRef({required this.competencyId, this.competencyName});

  /// JSON xaritadan yaratadi.
  factory CompetencyRef.fromJson(Map<String, dynamic> json) {
    return CompetencyRef(
      competencyId: JsonParse.asInt(json['competency_id']),
      competencyName: JsonParse.asStringOrNull(json['competency_name']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'competency_id': competencyId,
        'competency_name': competencyName,
      };
}

/// Foydalanuvchi analitikasining to'liq javobi (R9.1–R9.7).
///
/// Backend: `AnalyticsResponse`.
class AnalyticsResponse {
  /// Jamlangan o'rtacha foiz (0–100).
  final double overallScore;

  /// Kompetensiya taqsimoti (radar/progress/card).
  final List<CompetencyDistribution> distribution;

  /// Xronologik o'sish dinamikasi (line chart).
  final List<GrowthPoint> dynamics;

  /// Joriy vs oldingi farq; bitta natijada null (R9.4).
  final double? growthDiff;

  /// Eng kuchli kompetensiya(lar).
  final List<CompetencyRef> strongest;

  /// Rivojlantirilishi lozim kompetensiya(lar).
  final List<CompetencyRef> toDevelop;

  /// Hisobga olingan natijalar soni.
  final int resultCount;

  /// Kamida bitta natija bormi.
  final bool hasResults;

  /// Modelni yaratadi.
  const AnalyticsResponse({
    required this.overallScore,
    this.distribution = const [],
    this.dynamics = const [],
    this.growthDiff,
    this.strongest = const [],
    this.toDevelop = const [],
    this.resultCount = 0,
    this.hasResults = false,
  });

  /// JSON xaritadan yaratadi.
  factory AnalyticsResponse.fromJson(Map<String, dynamic> json) {
    return AnalyticsResponse(
      overallScore: JsonParse.asDouble(json['overall_score']),
      distribution: JsonParse.asList(
        json['distribution'],
        CompetencyDistribution.fromJson,
      ),
      dynamics: JsonParse.asList(json['dynamics'], GrowthPoint.fromJson),
      growthDiff: JsonParse.asDoubleOrNull(json['growth_diff']),
      strongest: JsonParse.asList(json['strongest'], CompetencyRef.fromJson),
      toDevelop: JsonParse.asList(json['to_develop'], CompetencyRef.fromJson),
      resultCount: JsonParse.asInt(json['result_count']),
      hasResults: JsonParse.asBool(json['has_results']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'overall_score': overallScore,
        'distribution':
            distribution.map((d) => d.toJson()).toList(growable: false),
        'dynamics': dynamics.map((d) => d.toJson()).toList(growable: false),
        'growth_diff': growthDiff,
        'strongest': strongest.map((s) => s.toJson()).toList(growable: false),
        'to_develop': toDevelop.map((s) => s.toJson()).toList(growable: false),
        'result_count': resultCount,
        'has_results': hasResults,
      };
}

/// Tashkilot/hudud kesimi bo'yicha jamlangan analitika (R15.3, R15.4).
///
/// Backend: `SectionAnalyticsResponse`.
class SectionAnalytics {
  /// Kesim (tashkilot/hudud) ID.
  final int? sectionId;

  /// Kesim nomi.
  final String? sectionName;

  /// Kesimdagi noyob rahbarlar soni.
  final int leadersCount;

  /// Kesimda test topshirgan rahbarlar soni.
  final int testTakersCount;

  /// Kesim o'rtacha balli (0–100).
  final double averageScore;

  /// Modelni yaratadi.
  const SectionAnalytics({
    this.sectionId,
    this.sectionName,
    this.leadersCount = 0,
    this.testTakersCount = 0,
    required this.averageScore,
  });

  /// JSON xaritadan yaratadi.
  factory SectionAnalytics.fromJson(Map<String, dynamic> json) {
    return SectionAnalytics(
      sectionId: JsonParse.asIntOrNull(json['section_id']),
      sectionName: JsonParse.asStringOrNull(json['section_name']),
      leadersCount: JsonParse.asInt(json['leaders_count']),
      testTakersCount: JsonParse.asInt(json['test_takers_count']),
      averageScore: JsonParse.asDouble(json['average_score']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'section_id': sectionId,
        'section_name': sectionName,
        'leaders_count': leadersCount,
        'test_takers_count': testTakersCount,
        'average_score': averageScore,
      };
}
