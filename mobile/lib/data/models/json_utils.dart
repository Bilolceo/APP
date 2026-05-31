/// JSON ajratish (parsing) yordamchilari.
///
/// Backend (FastAPI/Pydantic) javoblarida `Decimal` maydonlari JSON'da son yoki
/// matn ko'rinishida kelishi mumkin (masalan `78.00` yoki `"78.00"`), sanalar
/// esa ISO-8601 matn sifatida keladi. Ushbu yordamchilar shu noaniqliklarni
/// xavfsiz, null-safety'ga mos tarzda boshqaradi va DTO `fromJson` metodlarini
/// soddalashtiradi.

/// JSON qiymatlarini Dart tiplariga xavfsiz keltiruvchi statik yordamchilar.
class JsonParse {
  const JsonParse._();

  /// Qiymatni `double` ga keltiradi; aniqlab bo'lmasa [fallback] qaytaradi.
  ///
  /// `num` (int/double) va `String` (masalan Pydantic `Decimal` -> "78.00")
  /// ko'rinishlarini qo'llab-quvvatlaydi.
  static double asDouble(Object? value, {double fallback = 0}) {
    return asDoubleOrNull(value) ?? fallback;
  }

  /// Qiymatni `double?` ga keltiradi; `null` yoki yaroqsiz bo'lsa `null`.
  static double? asDoubleOrNull(Object? value) {
    if (value == null) return null;
    if (value is num) return value.toDouble();
    if (value is String) return double.tryParse(value);
    return null;
  }

  /// Qiymatni `int` ga keltiradi; aniqlab bo'lmasa [fallback] qaytaradi.
  static int asInt(Object? value, {int fallback = 0}) {
    return asIntOrNull(value) ?? fallback;
  }

  /// Qiymatni `int?` ga keltiradi; `null` yoki yaroqsiz bo'lsa `null`.
  static int? asIntOrNull(Object? value) {
    if (value == null) return null;
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value) ?? double.tryParse(value)?.toInt();
    return null;
  }

  /// Qiymatni `String` ga keltiradi; `null` bo'lsa [fallback] qaytaradi.
  static String asString(Object? value, {String fallback = ''}) {
    return asStringOrNull(value) ?? fallback;
  }

  /// Qiymatni `String?` ga keltiradi; `null` bo'lsa `null`.
  static String? asStringOrNull(Object? value) {
    if (value == null) return null;
    if (value is String) return value;
    return value.toString();
  }

  /// Qiymatni `bool` ga keltiradi; aniqlab bo'lmasa [fallback] qaytaradi.
  static bool asBool(Object? value, {bool fallback = false}) {
    if (value is bool) return value;
    if (value is num) return value != 0;
    if (value is String) {
      final normalized = value.toLowerCase();
      if (normalized == 'true') return true;
      if (normalized == 'false') return false;
    }
    return fallback;
  }

  /// ISO-8601 sana/vaqt matnini `DateTime?` ga keltiradi.
  static DateTime? asDateTimeOrNull(Object? value) {
    if (value == null) return null;
    if (value is DateTime) return value;
    if (value is String) return DateTime.tryParse(value);
    return null;
  }

  /// JSON xaritani `Map<String, dynamic>` ko'rinishida xavfsiz qaytaradi.
  static Map<String, dynamic> asMap(Object? value) {
    if (value is Map) return Map<String, dynamic>.from(value);
    return <String, dynamic>{};
  }

  /// JSON ro'yxatini berilgan [parse] funksiyasi bilan `List<T>` ga keltiradi.
  ///
  /// `null` yoki ro'yxat bo'lmagan qiymat uchun bo'sh ro'yxat qaytaradi.
  static List<T> asList<T>(
    Object? value,
    T Function(Map<String, dynamic> json) parse,
  ) {
    if (value is! List) return <T>[];
    return value
        .whereType<Map>()
        .map((e) => parse(Map<String, dynamic>.from(e)))
        .toList(growable: false);
  }

  /// JSON ro'yxatini `int` qiymatlar ro'yxatiga keltiradi (masalan ID ro'yxati).
  static List<int> asIntList(Object? value) {
    if (value is! List) return <int>[];
    return value
        .map(asIntOrNull)
        .whereType<int>()
        .toList(growable: false);
  }
}
