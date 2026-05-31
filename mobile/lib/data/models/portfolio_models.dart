import 'json_utils.dart';

/// Portfolio DTO modellari (R11).
///
/// Maydon nomlari backend `app/api/schemas/portfolio.py` bilan aniq mos keladi.

/// Portfolio yozuvi (R11.1, R11.2).
///
/// Backend: `PortfolioItemResponse`.
class PortfolioItem {
  /// Portfolio yozuvi ID.
  final int id;

  /// Yozuv nomi.
  final String title;

  /// Fayl havolasi.
  final String? fileUrl;

  /// Fayl turi (pdf/png/...).
  final String? fileType;

  /// Fayl hajmi (bayt).
  final int? sizeBytes;

  /// Yaratilgan sana.
  final DateTime? createdAt;

  /// Modelni yaratadi.
  const PortfolioItem({
    required this.id,
    required this.title,
    this.fileUrl,
    this.fileType,
    this.sizeBytes,
    this.createdAt,
  });

  /// JSON xaritadan yaratadi.
  factory PortfolioItem.fromJson(Map<String, dynamic> json) {
    return PortfolioItem(
      id: JsonParse.asInt(json['id']),
      title: JsonParse.asString(json['title']),
      fileUrl: JsonParse.asStringOrNull(json['file_url']),
      fileType: JsonParse.asStringOrNull(json['file_type']),
      sizeBytes: JsonParse.asIntOrNull(json['size_bytes']),
      createdAt: JsonParse.asDateTimeOrNull(json['created_at']),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'file_url': fileUrl,
        'file_type': fileType,
        'size_bytes': sizeBytes,
        'created_at': createdAt?.toIso8601String(),
      };
}
