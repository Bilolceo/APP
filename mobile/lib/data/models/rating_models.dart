import 'json_utils.dart';

/// Reyting DTO modellari (R12).
///
/// Maydon nomlari backend `app/api/schemas/rating.py` bilan aniq mos keladi.
/// Reyting anonim: faqat hudud, tashkilot turi, lavozim, foiz va rank oshkor
/// qilinadi (R12.4).

/// Reytingdagi bitta anonim yozuv (R12.1, R12.4).
///
/// Backend: `RatingEntryResponse`.
class RatingEntry {
  /// Reyting o'rni (1 dan boshlanadi).
  final int rank;

  /// Saralash ko'rsatkichi — umumiy foiz.
  final double percentage;

  /// Hudud.
  final String? region;

  /// Tashkilot turi.
  final String? orgType;

  /// Lavozim.
  final String? position;

  /// So'rovchining o'z yozuvimi.
  final bool isRequester;

  /// Modelni yaratadi.
  const RatingEntry({
    required this.rank,
    required this.percentage,
    this.region,
    this.orgType,
    this.position,
    this.isRequester = false,
  });

  /// JSON xaritadan yaratadi.
  factory RatingEntry.fromJson(Map<String, dynamic> json) {
    return RatingEntry(
      rank: JsonParse.asInt(json['rank']),
      percentage: JsonParse.asDouble(json['percentage']),
      region: JsonParse.asStringOrNull(json['region']),
      orgType: JsonParse.asStringOrNull(json['org_type']),
      position: JsonParse.asStringOrNull(json['position']),
      isRequester: JsonParse.asBool(json['is_requester']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'rank': rank,
        'percentage': percentage,
        'region': region,
        'org_type': orgType,
        'position': position,
        'is_requester': isRequester,
      };
}

/// Reytingdan tashqaridagi yozuv — yakunlangan natijasi yo'q (R12.5).
///
/// Backend: `OutOfRankingEntryResponse`.
class OutOfRankingEntry {
  /// Hudud.
  final String? region;

  /// Tashkilot turi.
  final String? orgType;

  /// Lavozim.
  final String? position;

  /// So'rovchining o'z (reytingsiz) yozuvimi.
  final bool isRequester;

  /// Modelni yaratadi.
  const OutOfRankingEntry({
    this.region,
    this.orgType,
    this.position,
    this.isRequester = false,
  });

  /// JSON xaritadan yaratadi.
  factory OutOfRankingEntry.fromJson(Map<String, dynamic> json) {
    return OutOfRankingEntry(
      region: JsonParse.asStringOrNull(json['region']),
      orgType: JsonParse.asStringOrNull(json['org_type']),
      position: JsonParse.asStringOrNull(json['position']),
      isRequester: JsonParse.asBool(json['is_requester']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'region': region,
        'org_type': orgType,
        'position': position,
        'is_requester': isRequester,
      };
}

/// To'liq anonim reyting taqdimoti (R12.1–R12.5).
///
/// Backend: `RatingResponse`.
class RatingResponse {
  /// Reyting kesimi (overall/region/organization/competency).
  final String scope;

  /// Tartiblangan anonim yozuvlar.
  final List<RatingEntry> ranked;

  /// Reytingdan tashqaridagi yozuvlar.
  final List<OutOfRankingEntry> outOfRanking;

  /// Modelni yaratadi.
  const RatingResponse({
    required this.scope,
    this.ranked = const [],
    this.outOfRanking = const [],
  });

  /// JSON xaritadan yaratadi.
  factory RatingResponse.fromJson(Map<String, dynamic> json) {
    return RatingResponse(
      scope: JsonParse.asString(json['scope']),
      ranked: JsonParse.asList(json['ranked'], RatingEntry.fromJson),
      outOfRanking:
          JsonParse.asList(json['out_of_ranking'], OutOfRankingEntry.fromJson),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'scope': scope,
        'ranked': ranked.map((r) => r.toJson()).toList(growable: false),
        'out_of_ranking':
            outOfRanking.map((r) => r.toJson()).toList(growable: false),
      };
}
