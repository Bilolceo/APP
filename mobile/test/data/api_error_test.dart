import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mtt_menejer_diagnostika/data/api_client/api_client.dart';
import 'package:mtt_menejer_diagnostika/data/models/models.dart';

/// `ApiException` ga keltirish (mapDioException) birlik testlari (R20.6).
void main() {
  RequestOptions opts() => RequestOptions(path: '/x');

  group('ApiClient.mapDioException', () {
    test('backend tuzilgan xatosini tipli ApiException ga keltiradi', () {
      final dioError = DioException(
        requestOptions: opts(),
        type: DioExceptionType.badResponse,
        response: Response(
          requestOptions: opts(),
          statusCode: 400,
          data: {
            'error': {
              'code': 'validation_error',
              'message': 'Telefon raqami formati noto\'g\'ri',
              'details': [
                {'field': 'phone', 'reason': 'must start with +998'}
              ],
            }
          },
        ),
      );
      final exception = ApiClient.mapDioException(dioError);
      expect(exception.code, 'validation_error');
      expect(exception.message, 'Telefon raqami formati noto\'g\'ri');
      expect(exception.statusCode, 400);
      expect(exception.details.single.field, 'phone');
      expect(exception.details.single.reason, 'must start with +998');
    });

    test('taym-aut tarmoq xatosiga keltiriladi', () {
      final dioError = DioException(
        requestOptions: opts(),
        type: DioExceptionType.connectionTimeout,
      );
      final exception = ApiClient.mapDioException(dioError);
      expect(exception.code, 'network_error');
    });

    test('tuzilmagan 401 javob unauthorized ga keltiriladi', () {
      final dioError = DioException(
        requestOptions: opts(),
        type: DioExceptionType.badResponse,
        response: Response(
          requestOptions: opts(),
          statusCode: 401,
          data: 'Unauthorized',
        ),
      );
      final exception = ApiClient.mapDioException(dioError);
      expect(exception.code, 'authentication_error');
      expect(exception.statusCode, 401);
    });
  });

  group('ApiError.fromJson', () {
    test('o\'rab turgan obyektdan ham, ichki error dan ham o\'qiydi', () {
      final wrapped = ApiError.fromJson({
        'error': {'code': 'not_found', 'message': 'Topilmadi'}
      });
      expect(wrapped.code, 'not_found');
      expect(wrapped.message, 'Topilmadi');

      final inner = ApiError.fromJson({'code': 'conflict', 'message': 'Mavjud'});
      expect(inner.code, 'conflict');
    });
  });
}
