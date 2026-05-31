import 'json_utils.dart';

/// Test, savol, sessiya va topshirish DTO modellari (R6, R7, R8).
///
/// Maydon nomlari backend `app/api/schemas/test.py` bilan aniq mos keladi.

/// Testlar ro'yxatidagi bitta yozuv (R6.1).
///
/// Backend: `TestSummaryResponse`.
class TestSummary {
  /// Test noyob identifikatori.
  final int id;

  /// Test nomi.
  final String title;

  /// Test tavsifi.
  final String? description;

  /// Toifa (yo'nalish).
  final String? category;

  /// Davomiyligi (daqiqalarda).
  final int? durationMinutes;

  /// Modelni yaratadi.
  const TestSummary({
    required this.id,
    required this.title,
    this.description,
    this.category,
    this.durationMinutes,
  });

  /// JSON xaritadan yaratadi.
  factory TestSummary.fromJson(Map<String, dynamic> json) {
    return TestSummary(
      id: JsonParse.asInt(json['id']),
      title: JsonParse.asString(json['title']),
      description: JsonParse.asStringOrNull(json['description']),
      category: JsonParse.asStringOrNull(json['category']),
      durationMinutes: JsonParse.asIntOrNull(json['duration_minutes']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'description': description,
        'category': category,
        'duration_minutes': durationMinutes,
      };
}

/// Savolning bitta javob varianti (R6.3) — faqat ko'rsatiladigan ma'lumot.
///
/// Backend: `AnswerOptionResponse` (`id`, `answer_text`). To'g'rilik/ball
/// oshkor qilinmaydi.
class AnswerOption {
  /// Variant identifikatori.
  final int id;

  /// Variant matni.
  final String answerText;

  /// Modelni yaratadi.
  const AnswerOption({required this.id, required this.answerText});

  /// JSON xaritadan yaratadi.
  factory AnswerOption.fromJson(Map<String, dynamic> json) {
    return AnswerOption(
      id: JsonParse.asInt(json['id']),
      answerText: JsonParse.asString(json['answer_text']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {'id': id, 'answer_text': answerText};
}

/// Test tafsilotidagi bitta savol va uning variantlari (R6.3).
///
/// Backend: `QuestionDetailResponse`.
class Question {
  /// Savol identifikatori.
  final int id;

  /// Savol matni.
  final String questionText;

  /// Savol turi (cognitive/likert/situational).
  final String? questionType;

  /// Tartib raqami.
  final int? orderIndex;

  /// Bog'langan kompetensiya ID (yo'q bo'lsa null).
  final int? competencyId;

  /// Javob variantlari.
  final List<AnswerOption> answers;

  /// Modelni yaratadi.
  const Question({
    required this.id,
    required this.questionText,
    this.questionType,
    this.orderIndex,
    this.competencyId,
    this.answers = const [],
  });

  /// JSON xaritadan yaratadi.
  factory Question.fromJson(Map<String, dynamic> json) {
    return Question(
      id: JsonParse.asInt(json['id']),
      questionText: JsonParse.asString(json['question_text']),
      questionType: JsonParse.asStringOrNull(json['question_type']),
      orderIndex: JsonParse.asIntOrNull(json['order_index']),
      competencyId: JsonParse.asIntOrNull(json['competency_id']),
      answers: JsonParse.asList(json['answers'], AnswerOption.fromJson),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'id': id,
        'question_text': questionText,
        'question_type': questionType,
        'order_index': orderIndex,
        'competency_id': competencyId,
        'answers': answers.map((a) => a.toJson()).toList(growable: false),
      };
}

/// Test tafsiloti: meta-ma'lumot + savollar to'plami (R6.3).
///
/// Backend: `TestDetailResponse`.
class TestDetail {
  /// Test identifikatori.
  final int id;

  /// Test nomi.
  final String title;

  /// Test tavsifi.
  final String? description;

  /// Toifa (yo'nalish).
  final String? category;

  /// Davomiyligi (daqiqalarda).
  final int? durationMinutes;

  /// Savollar soni.
  final int questionCount;

  /// Savollar (belgilangan tartibda).
  final List<Question> questions;

  /// Modelni yaratadi.
  const TestDetail({
    required this.id,
    required this.title,
    this.description,
    this.category,
    this.durationMinutes,
    this.questionCount = 0,
    this.questions = const [],
  });

  /// JSON xaritadan yaratadi.
  factory TestDetail.fromJson(Map<String, dynamic> json) {
    return TestDetail(
      id: JsonParse.asInt(json['id']),
      title: JsonParse.asString(json['title']),
      description: JsonParse.asStringOrNull(json['description']),
      category: JsonParse.asStringOrNull(json['category']),
      durationMinutes: JsonParse.asIntOrNull(json['duration_minutes']),
      questionCount: JsonParse.asInt(json['question_count']),
      questions: JsonParse.asList(json['questions'], Question.fromJson),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'description': description,
        'category': category,
        'duration_minutes': durationMinutes,
        'question_count': questionCount,
        'questions': questions.map((q) => q.toJson()).toList(growable: false),
      };
}

/// Boshlangan yoki davom ettirilayotgan test sessiyasi (R7.1, R7.10).
///
/// Backend: `SessionResponse`. `start` endpointi shu modelni qaytaradi.
class StartSessionResponse {
  /// Sessiya identifikatori.
  final int id;

  /// Sessiya egasi (foydalanuvchi) ID.
  final int userId;

  /// Test identifikatori.
  final int testId;

  /// Holat: `in_progress` / `completed`.
  final String status;

  /// Boshlanish vaqti.
  final DateTime? startedAt;

  /// Muddat tugash vaqti (davomiylik belgilangan bo'lsa).
  final DateTime? expiresAt;

  /// Yakunlanish vaqti (yakunlangan bo'lsa).
  final DateTime? completedAt;

  /// Modelni yaratadi.
  const StartSessionResponse({
    required this.id,
    required this.userId,
    required this.testId,
    required this.status,
    this.startedAt,
    this.expiresAt,
    this.completedAt,
  });

  /// JSON xaritadan yaratadi.
  factory StartSessionResponse.fromJson(Map<String, dynamic> json) {
    return StartSessionResponse(
      id: JsonParse.asInt(json['id']),
      userId: JsonParse.asInt(json['user_id']),
      testId: JsonParse.asInt(json['test_id']),
      status: JsonParse.asString(json['status']),
      startedAt: JsonParse.asDateTimeOrNull(json['started_at']),
      expiresAt: JsonParse.asDateTimeOrNull(json['expires_at']),
      completedAt: JsonParse.asDateTimeOrNull(json['completed_at']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': userId,
        'test_id': testId,
        'status': status,
        'started_at': startedAt?.toIso8601String(),
        'expires_at': expiresAt?.toIso8601String(),
        'completed_at': completedAt?.toIso8601String(),
      };
}

/// Bitta savolga berilgan javob (R7.6).
///
/// Backend: `AnswerSubmission`. `questionId` majburiy; `answerId` (variant)
/// yoki `likertValue` (1–5) dan kamida bittasi beriladi.
class SubmitAnswer {
  /// Savol identifikatori.
  final int questionId;

  /// Tanlangan variant identifikatori (ixtiyoriy).
  final int? answerId;

  /// Likert shkalasi qiymati (1–5, ixtiyoriy).
  final int? likertValue;

  /// Modelni yaratadi.
  const SubmitAnswer({
    required this.questionId,
    this.answerId,
    this.likertValue,
  });

  /// JSON xaritadan yaratadi.
  factory SubmitAnswer.fromJson(Map<String, dynamic> json) {
    return SubmitAnswer(
      questionId: JsonParse.asInt(json['question_id']),
      answerId: JsonParse.asIntOrNull(json['answer_id']),
      likertValue: JsonParse.asIntOrNull(json['likert_value']),
    );
  }

  /// So'rov tanasi uchun JSON xaritaga aylantiradi (faqat berilgan maydonlar).
  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{'question_id': questionId};
    if (answerId != null) map['answer_id'] = answerId;
    if (likertValue != null) map['likert_value'] = likertValue;
    return map;
  }
}

/// Test sessiyasini topshirish so'rovi (R7.6).
///
/// Backend: `SubmitSessionRequest` (`session_id`, `answers`).
class SubmitRequest {
  /// Topshirilayotgan sessiya ID.
  final int sessionId;

  /// Javoblar ro'yxati.
  final List<SubmitAnswer> answers;

  /// So'rovni yaratadi.
  const SubmitRequest({required this.sessionId, this.answers = const []});

  /// So'rov tanasi uchun JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'session_id': sessionId,
        'answers': answers.map((a) => a.toJson()).toList(growable: false),
      };
}

/// Topshirish natijasidagi bitta kompetensiya foizi (R8.3).
///
/// Backend: `CompetencyScoreResponse` (`competency_id`, `percentage`).
class CompetencyScore {
  /// Kompetensiya identifikatori.
  final int competencyId;

  /// Kompetensiya foizi (0–100).
  final double percentage;

  /// Modelni yaratadi.
  const CompetencyScore({
    required this.competencyId,
    required this.percentage,
  });

  /// JSON xaritadan yaratadi.
  factory CompetencyScore.fromJson(Map<String, dynamic> json) {
    return CompetencyScore(
      competencyId: JsonParse.asInt(json['competency_id']),
      percentage: JsonParse.asDouble(json['percentage']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'competency_id': competencyId,
        'percentage': percentage,
      };
}
