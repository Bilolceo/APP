import 'package:dio/dio.dart';

import '../models/json_utils.dart';
import '../models/portfolio_models.dart';
import 'api_client.dart';
import 'endpoints.dart';

/// Portfolio domeni API mijozi (R11).
class PortfolioApi {
  final ApiClient _client;

  /// Domen mijozini yaratadi.
  const PortfolioApi(this._client);

  /// Joriy foydalanuvchi portfolio yozuvlarini qaytaradi (R11.1).
  Future<List<PortfolioItem>> mine() {
    return _client.getJson(
      Endpoints.portfolioMe,
      parse: (data) => JsonParse.asList(data, PortfolioItem.fromJson),
    );
  }

  /// Faylni `multipart/form-data` orqali yuklaydi (R11.2).
  ///
  /// [filePath] — yuklanadigan faylning lokal yo'li; [title] — ixtiyoriy nom.
  Future<PortfolioItem> upload({
    required String filePath,
    String? title,
  }) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(filePath),
      if (title != null) 'title': title,
    });
    return _client.postMultipart(
      Endpoints.portfolioUpload,
      formData: formData,
      parse: (data) => PortfolioItem.fromJson(JsonParse.asMap(data)),
    );
  }

  /// Faylni xotira (bayt) ko'rinishidan yuklaydi (R11.2).
  ///
  /// Offline/keshlangan baytlar uchun qulay: [bytes] va [filename] beriladi.
  Future<PortfolioItem> uploadBytes({
    required List<int> bytes,
    required String filename,
    String? title,
  }) {
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(bytes, filename: filename),
      if (title != null) 'title': title,
    });
    return _client.postMultipart(
      Endpoints.portfolioUpload,
      formData: formData,
      parse: (data) => PortfolioItem.fromJson(JsonParse.asMap(data)),
    );
  }

  /// Portfolio yozuvini o'chiradi (R11.5–R11.7). 204 — tana yo'q.
  Future<void> delete(int portfolioId) {
    return _client.deleteJson(
      Endpoints.portfolioItem(portfolioId),
      parse: (_) {},
    );
  }
}
