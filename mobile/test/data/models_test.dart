import 'package:flutter_test/flutter_test.dart';
import 'package:mtt_menejer_diagnostika/data/models/models.dart';

/// DTO modellarining JSON ajratish (fromJson) va serializatsiya (toJson)
/// xulq-atvori birlik testlari.
///
/// Maqsad: backend sxemalaridagi snake_case kalitlar Dart camelCase
/// maydonlariga to'g'ri o'qilishi va `Decimal` (matn/son) qiymatlari xavfsiz
/// `double` ga keltirilishini tasdiqlash.
void main() {
  group('AuthTokens', () {
    test('backend TokenPairResponse JSON dan to\'g\'ri o\'qiydi', () {
      final json = {
        'access_token': 'acc-123',
        'refresh_token': 'ref-456',
        'token_type': 'bearer',
        'expires_in': 900,
      };
      final tokens = AuthTokens.fromJson(json);
      expect(tokens.accessToken, 'acc-123');
      expect(tokens.refreshToken, 'ref-456');
      expect(tokens.tokenType, 'bearer');
      expect(tokens.expiresIn, 900);
    });

    test('yetishmaydigan maydonlar uchun xavfsiz standart qiymat', () {
      final tokens = AuthTokens.fromJson({'access_token': 'a'});
      expect(tokens.accessToken, 'a');
      expect(tokens.refreshToken, '');
      expect(tokens.expiresIn, 0);
    });
  });

  group('UserProfile', () {
    test('barcha maydonlarni snake_case dan o\'qiydi', () {
      final json = {
        'id': 7,
        'full_name': 'Ali Valiyev',
        'phone': '+998901234567',
        'organization_id': 1,
        'region_id': 2,
        'position': 'Direktor',
        'experience_years': 5,
        'education_level': 'Oliy',
        'qualification_courses': 'Kurs',
        'certificates': 'Sertifikat',
        'org_type': 'MTT',
        'notifications_enabled': true,
      };
      final profile = UserProfile.fromJson(json);
      expect(profile.id, 7);
      expect(profile.fullName, 'Ali Valiyev');
      expect(profile.phone, '+998901234567');
      expect(profile.experienceYears, 5);
      expect(profile.orgType, 'MTT');
      expect(profile.notificationsEnabled, isTrue);
    });

    test('ixtiyoriy null maydonlar null bo\'lib qoladi', () {
      final profile = UserProfile.fromJson({
        'id': 1,
        'full_name': 'X',
        'phone': '+998900000000',
      });
      expect(profile.organizationId, isNull);
      expect(profile.position, isNull);
      expect(profile.notificationsEnabled, isTrue);
    });
  });

  group('TestResult', () {
    test('Decimal qiymatlarni son va matndan o\'qiydi', () {
      final json = {
        'result_id': 555,
        'total_score': 78.0,
        'max_score': '100.00',
        'percentage': '78.00',
        'level': 'Yaxshi',
        'competencies': [
          {'competency_id': 3, 'percentage': 85.0}
        ],
        'strongest': [3],
        'weakest': [7],
        'next_retake_date': '2025-09-01',
      };
      final result = TestResult.fromJson(json);
      expect(result.resultId, 555);
      expect(result.totalScore, 78.0);
      expect(result.maxScore, 100.0);
      expect(result.percentage, 78.0);
      expect(result.level, 'Yaxshi');
      expect(result.competencies.single.competencyId, 3);
      expect(result.competencies.single.percentage, 85.0);
      expect(result.strongest, [3]);
      expect(result.weakest, [7]);
      expect(result.nextRetakeDate, DateTime.parse('2025-09-01'));
    });
  });

  group('TestDetail', () {
    test('savollar va variantlarni ichma-ich o\'qiydi', () {
      final json = {
        'id': 1,
        'title': 'Kognitiv',
        'question_count': 1,
        'questions': [
          {
            'id': 10,
            'question_text': 'Savol?',
            'question_type': 'likert',
            'order_index': 0,
            'competency_id': 2,
            'answers': [
              {'id': 100, 'answer_text': 'A'},
              {'id': 101, 'answer_text': 'B'},
            ],
          }
        ],
      };
      final detail = TestDetail.fromJson(json);
      expect(detail.questionCount, 1);
      expect(detail.questions.single.answers.length, 2);
      expect(detail.questions.single.answers.first.answerText, 'A');
    });
  });

  group('AnalyticsResponse', () {
    test('taqsimot va dinamikani o\'qiydi (R9.2, R9.1)', () {
      final json = {
        'overall_score': '72.50',
        'distribution': [
          {
            'competency_id': 1,
            'competency_name': 'Boshqaruv',
            'percentage': '80.00',
            'level': 'Yuqori',
          }
        ],
        'dynamics': [
          {'achieved_at': '2025-01-01T10:00:00Z', 'percentage': '70.00'}
        ],
        'growth_diff': '2.50',
        'strongest': [
          {'competency_id': 1, 'competency_name': 'Boshqaruv'}
        ],
        'to_develop': [
          {'competency_id': 2, 'competency_name': 'Innovatsiya'}
        ],
        'result_count': 3,
        'has_results': true,
      };
      final analytics = AnalyticsResponse.fromJson(json);
      expect(analytics.overallScore, 72.5);
      expect(analytics.distribution.single.level, 'Yuqori');
      expect(analytics.dynamics.single.percentage, 70.0);
      expect(analytics.growthDiff, 2.5);
      expect(analytics.strongest.single.competencyName, 'Boshqaruv');
      expect(analytics.toDevelop.single.competencyId, 2);
      expect(analytics.resultCount, 3);
      expect(analytics.hasResults, isTrue);
    });

    test('bo\'sh holatni xavfsiz o\'qiydi (R9.7)', () {
      final analytics = AnalyticsResponse.fromJson({
        'overall_score': '0.00',
        'has_results': false,
      });
      expect(analytics.overallScore, 0.0);
      expect(analytics.distribution, isEmpty);
      expect(analytics.dynamics, isEmpty);
      expect(analytics.growthDiff, isNull);
      expect(analytics.hasResults, isFalse);
    });
  });

  group('RatingResponse', () {
    test('anonim yozuvlar va reytingsizlarni o\'qiydi (R12.4, R12.5)', () {
      final json = {
        'scope': 'overall',
        'ranked': [
          {
            'rank': 1,
            'percentage': '90.00',
            'region': 'Toshkent',
            'org_type': 'MTT',
            'position': 'Direktor',
            'is_requester': true,
          }
        ],
        'out_of_ranking': [
          {
            'region': 'Samarqand',
            'org_type': 'MTT',
            'position': 'Mudir',
            'is_requester': false,
          }
        ],
      };
      final rating = RatingResponse.fromJson(json);
      expect(rating.scope, 'overall');
      expect(rating.ranked.single.rank, 1);
      expect(rating.ranked.single.isRequester, isTrue);
      expect(rating.outOfRanking.single.region, 'Samarqand');
    });
  });

  group('toJson — so\'rov modellari', () {
    test('RegisterRequest null ixtiyoriy maydonlarni tashlab yuboradi', () {
      final json = const RegisterRequest(
        phone: '+998901234567',
        password: 'secret123',
        fullName: 'Ali',
        role: 'Rahbar',
      ).toJson();
      expect(json.containsKey('organization_id'), isFalse);
      expect(json['phone'], '+998901234567');
      expect(json['full_name'], 'Ali');
    });

    test('SubmitRequest answers ni to\'g\'ri serializatsiya qiladi', () {
      final json = const SubmitRequest(
        sessionId: 1024,
        answers: [
          SubmitAnswer(questionId: 1, answerId: 4),
          SubmitAnswer(questionId: 2, likertValue: 5),
        ],
      ).toJson();
      expect(json['session_id'], 1024);
      final answers = json['answers'] as List;
      expect(answers.first['answer_id'], 4);
      expect((answers[1] as Map).containsKey('answer_id'), isFalse);
      expect(answers[1]['likert_value'], 5);
    });

    test('ProfileUpdateRequest faqat berilgan maydonlarni yuboradi', () {
      final json = const ProfileUpdateRequest(
        position: 'Bosh direktor',
        notificationsEnabled: false,
      ).toJson();
      expect(json, {
        'position': 'Bosh direktor',
        'notifications_enabled': false,
      });
    });
  });
}
