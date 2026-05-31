/// Repository qatlami — API va kesh manbalarini birlashtiradi (design.md).
///
/// Repository qatlamining mas'uliyati:
///  - `ApiClient` (Dio) orqali Backend'dan ma'lumot olish.
///  - `LocalCache` (Drift) orqali offline keshlash va o'qish (R19.3).
///  - `SyncQueue` orqali offline topshiriqlarni navbatga olish va yuborish
///    (R19.4).
///  - Online/offline holatga qarab manbalarni tanlash va birlashtirish.
///
/// TODO(19.2/19.3): Quyidagi abstrakt shartnomalar to'liq implementatsiya
/// qilinadi. Hozircha skeleton sifatida interfeyslar qoldirilgan.

/// Test ma'lumotlariga kirishni ta'minlovchi repository shartnomasi.
///
/// Online bo'lganda API'dan oladi va keshga yozadi; offline bo'lganda keshdan
/// qaytaradi (R19.3).
abstract interface class TestRepository {
  /// Faol testlar ro'yxatini qaytaradi (API yoki keshdan).
  ///
  /// TODO(19.2): ApiClient + LocalCache birlashtirish.
  Future<List<Map<String, dynamic>>> listTests();

  /// Berilgan [testId] bo'yicha test tafsilotini qaytaradi.
  ///
  /// TODO(19.2): ApiClient + LocalCache birlashtirish.
  Future<Map<String, dynamic>> getTest(String testId);
}

/// Test topshirish va natijalar bilan ishlovchi repository shartnomasi.
abstract interface class ResultRepository {
  /// Test natijasini topshiradi.
  ///
  /// Offline bo'lsa, natija `SyncQueue` ga `idempotency_key` bilan navbatga
  /// olinadi (R19.4); online bo'lsa to'g'ridan-to'g'ri yuboriladi.
  ///
  /// TODO(19.3): ApiClient + SyncQueue birlashtirish.
  Future<void> submitResult({
    required String sessionId,
    required Map<String, dynamic> payload,
  });
}
