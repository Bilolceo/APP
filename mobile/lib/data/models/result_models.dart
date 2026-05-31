import 'json_utils.dart';
import 'test_models.dart';

/// Natija (test_results) DTO modellari (R8).
///
/// Maydon nomlari backend `app/api/schemas/test.py` (`SubmitResultResponse`) va
/// `app/api/schemas/result.py` (`ResultSummaryResponse`,
/// `ResultDetailResponse`, `CompetencyResultResponse`) bilan aniq mos keladi.

/// Topshirishdan keyingi hisoblangan natija (R8.1, R8.2, R8.4).
///
/// Backend: `SubmitResultResponse`. `POST /tests/{id}/submit` javobi.
class TestResult {
  /// Saqlangan natija identifikatori.
  final int resultId;

  /// Umumiy yig'ilgan ball.
  final double totalScore;

  /// Umumiy maksimal ball.
  final double maxScore;

  /// Umumiy foiz (0–100).
  final double percentage;

  /// Daraja: Past / O'rta / Yaxshi / Yuqori.
  final String level;

  /// Kompetensiya bo'yicha foizlar.
  final List<CompetencyScore> competencies;

  /// Eng kuchli kompetensiya(lar) ID.
  final List<int> strongest;

  /// Eng zaif kompetensiya(lar) ID.
  final List<int> weakest;

  /// Keyingi qayta topshirish sanasi (R8.4).
  final DateTime? nextRetakeDate;

  /// Modelni yaratadi.
  const TestResult({
    required this.resultId,
    required this.totalScore,
    required this.maxScore,
    required this.percentage,
    required this.level,
    this.competencies = const [],
    this.strongest = const [],
    this.weakest = const [],
    this.nextRetakeDate,
  });

  /// JSON xaritadan yaratadi.
  factory TestResult.fromJson(Map<String, dynamic> json) {
    return TestResult(
      resultId: JsonParse.asInt(json['result_id']),
      totalScore: JsonParse.asDouble(json['total_score']),
      maxScore: JsonParse.asDouble(json['max_score']),
      percentage: JsonParse.asDouble(json['percentage']),
      level: JsonParse.asString(json['level']),
      competencies:
          JsonParse.asList(json['competencies'], CompetencyScore.fromJson),
      strongest: JsonParse.asIntList(json['strongest']),
      weakest: JsonParse.asIntList(json['weakest']),
      nextRetakeDate: JsonParse.asDateTimeOrNull(json['next_retake_date']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'result_id': resultId,
        'total_score': totalScore,
        'max_score': maxScore,
        'percentage': percentage,
        'level': level,
        'competencies':
            competencies.map((c) => c.toJson()).toList(growable: false),
        'strongest': strongest,
        'weakest': weakest,
        'next_retake_date': nextRetakeDate?.toIso8601String(),
      };
}

/// Natija tarkibidagi bitta kompetensiya ballari (R8.3, R8.8).
///
/// Backend: `CompetencyResultResponse`.
class CompetencyResult {
  /// Kompetensiya identifikatori.
  final int competencyId;

  /// Yig'ilgan ball.
  final double score;

  /// Maksimal ball.
  final double maxScore;

  /// Kompetensiya foizi (0–100).
  final double percentage;

  /// Modelni yaratadi.
  const CompetencyResult({
    required this.competencyId,
    required this.score,
    required this.maxScore,
    required this.percentage,
  });

  /// JSON xaritadan yaratadi.
  factory CompetencyResult.fromJson(Map<String, dynamic> json) {
    return CompetencyResult(
      competencyId: JsonParse.asInt(json['competency_id']),
      score: JsonParse.asDouble(json['score']),
      maxScore: JsonParse.asDouble(json['max_score']),
      percentage: JsonParse.asDouble(json['percentage']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'competency_id': competencyId,
        'score': score,
        'max_score': maxScore,
        'percentage': percentage,
      };
}

/// Foydalanuvchi natijalari ro'yxatidagi bitta yozuv (R8.6).
///
/// Backend: `ResultSummaryResponse`. `GET /tests/results/me` ro'yxati uchun.
class ResultSummary {
  /// Natija identifikatori.
  final int id;

  /// Test identifikatori.
  final int testId;

  /// Sessiya identifikatori.
  final int sessionId;

  /// Umumiy yig'ilgan ball.
  final double totalScore;

  /// Umumiy maksimal ball.
  final double maxScore;

  /// Umumiy foiz (0–100).
  final double percentage;

  /// Daraja: Past / O'rta / Yaxshi / Yuqori.
  final String level;

  /// Ekspert qo'shimcha ko'rsatkichi (R13.2).
  final double? expertScore;

  /// Keyingi qayta topshirish sanasi (R8.4).
  final DateTime? nextRetakeDate;

  /// Yaratilgan vaqt.
  final DateTime? createdAt;

  /// Modelni yaratadi.
  const ResultSummary({
    required this.id,
    required this.testId,
    required this.sessionId,
    required this.totalScore,
    required this.maxScore,
    required this.percentage,
    required this.level,
    this.expertScore,
    this.nextRetakeDate,
    this.createdAt,
  });

  /// JSON xaritadan yaratadi.
  factory ResultSummary.fromJson(Map<String, dynamic> json) {
    return ResultSummary(
      id: JsonParse.asInt(json['id']),
      testId: JsonParse.asInt(json['test_id']),
      sessionId: JsonParse.asInt(json['session_id']),
      totalScore: JsonParse.asDouble(json['total_score']),
      maxScore: JsonParse.asDouble(json['max_score']),
      percentage: JsonParse.asDouble(json['percentage']),
      level: JsonParse.asString(json['level']),
      expertScore: JsonParse.asDoubleOrNull(json['expert_score']),
      nextRetakeDate: JsonParse.asDateTimeOrNull(json['next_retake_date']),
      createdAt: JsonParse.asDateTimeOrNull(json['created_at']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'id': id,
        'test_id': testId,
        'session_id': sessionId,
        'total_score': totalScore,
        'max_score': maxScore,
        'percentage': percentage,
        'level': level,
        'expert_score': expertScore,
        'next_retake_date': nextRetakeDate?.toIso8601String(),
        'created_at': createdAt?.toIso8601String(),
      };
}

/// Natija tafsiloti — kompetensiya ballari bilan (R8.3, R8.7).
///
/// Backend: `ResultDetailResponse`. `GET /tests/results/{id}` uchun.
class ResultDetail {
  /// Natija identifikatori.
  final int id;

  /// Natija egasi (foydalanuvchi) ID.
  final int userId;

  /// Test identifikatori.
  final int testId;

  /// Sessiya identifikatori.
  final int sessionId;

  /// Umumiy yig'ilgan ball.
  final double totalScore;

  /// Umumiy maksimal ball.
  final double maxScore;

  /// Umumiy foiz (0–100).
  final double percentage;

  /// Daraja: Past / O'rta / Yaxshi / Yuqori.
  final String level;

  /// Ekspert qo'shimcha ko'rsatkichi (R13.2).
  final double? expertScore;

  /// Keyingi qayta topshirish sanasi (R8.4).
  final DateTime? nextRetakeDate;

  /// Yaratilgan vaqt.
  final DateTime? createdAt;

  /// Kompetensiya bo'yicha ballar.
  final List<CompetencyResult> competencyResults;

  /// Modelni yaratadi.
  const ResultDetail({
    required this.id,
    required this.userId,
    required this.testId,
    required this.sessionId,
    required this.totalScore,
    required this.maxScore,
    required this.percentage,
    required this.level,
    this.expertScore,
    this.nextRetakeDate,
    this.createdAt,
    this.competencyResults = const [],
  });

  /// JSON xaritadan yaratadi.
  factory ResultDetail.fromJson(Map<String, dynamic> json) {
    return ResultDetail(
      id: JsonParse.asInt(json['id']),
      userId: JsonParse.asInt(json['user_id']),
      testId: JsonParse.asInt(json['test_id']),
      sessionId: JsonParse.asInt(json['session_id']),
      totalScore: JsonParse.asDouble(json['total_score']),
      maxScore: JsonParse.asDouble(json['max_score']),
      percentage: JsonParse.asDouble(json['percentage']),
      level: JsonParse.asString(json['level']),
      expertScore: JsonParse.asDoubleOrNull(json['expert_score']),
      nextRetakeDate: JsonParse.asDateTimeOrNull(json['next_retake_date']),
      createdAt: JsonParse.asDateTimeOrNull(json['created_at']),
      competencyResults: JsonParse.asList(
        json['competency_results'],
        CompetencyResult.fromJson,
      ),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': userId,
        'test_id': testId,
        'session_id': sessionId,
        'total_score': totalScore,
        'max_score': maxScore,
        'percentage': percentage,
        'level': level,
        'expert_score': expertScore,
        'next_retake_date': nextRetakeDate?.toIso8601String(),
        'created_at': createdAt?.toIso8601String(),
        'competency_results':
            competencyResults.map((c) => c.toJson()).toList(growable: false),
      };
}
