import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/api_client/auth_api.dart';
import '../data/api_client/auth_events.dart';
import '../data/api_client/token_store.dart';
import '../data/api_client/users_api.dart';
import '../data/models/api_error.dart';
import '../data/models/auth_models.dart';
import '../data/models/user_models.dart';

/// Global autentifikatsiya holati va uni boshqaruvchi notifier (20.1).
///
/// Bu modul ilova bo'ylab yagona "kim kirgan?" haqiqatini (token, rol, profil)
/// saqlaydi (R1.1, R2.1, R5.1, R19.2). Prezentatsiya qatlami [AuthState] ni
/// kuzatib, splash → login/register → home oqimini boshqaradi.

/// Autentifikatsiya jarayonining yuqori darajali bosqichi.
enum AuthStatus {
  /// Boshlang'ich/aniqlanmagan — startda token tekshirilmoqda (splash).
  unknown,

  /// Foydalanuvchi tizimga kirgan (token mavjud, profil yuklangan).
  authenticated,

  /// Foydalanuvchi tizimga kirmagan — login/register talab qilinadi.
  unauthenticated,
}

/// O'zgarmas (immutable) global autentifikatsiya holati.
///
/// [status] — bosqich; [profile] va [role] faqat [AuthStatus.authenticated]
/// holatda to'ldiriladi. [isLoading] login/register kabi amallar davomida UI
/// uchun yuklanish indikatorini, [errorMessage] esa foydalanuvchiga
/// ko'rsatiladigan (o'zbekcha) xato matnini ifodalaydi.
class AuthState {
  /// Joriy autentifikatsiya bosqichi.
  final AuthStatus status;

  /// Kirgan foydalanuvchining to'liq profili (kirgan bo'lsa).
  final UserProfile? profile;

  /// Kirgan foydalanuvchining roli (Rahbar/Ekspert/Administrator).
  final String? role;

  /// Davom etayotgan amal (login/register/bootstrap) indikatori.
  final bool isLoading;

  /// Oxirgi amaldagi foydalanuvchiga ko'rsatiladigan xato (mavjud bo'lsa).
  final String? errorMessage;

  /// Holatni yaratadi.
  const AuthState({
    required this.status,
    this.profile,
    this.role,
    this.isLoading = false,
    this.errorMessage,
  });

  /// Boshlang'ich (aniqlanmagan) holat — splash ko'rsatiladi.
  const AuthState.unknown()
      : status = AuthStatus.unknown,
        profile = null,
        role = null,
        isLoading = false,
        errorMessage = null;

  /// Kirilgan holat (profil va rol bilan).
  const AuthState.authenticated({required UserProfile this.profile, this.role})
      : status = AuthStatus.authenticated,
        isLoading = false,
        errorMessage = null;

  /// Kirilmagan holat (ixtiyoriy xato xabari bilan).
  const AuthState.unauthenticated({this.errorMessage})
      : status = AuthStatus.unauthenticated,
        profile = null,
        role = null,
        isLoading = false;

  /// Foydalanuvchi tizimga kirgan-kirmaganini bildiradi.
  bool get isAuthenticated => status == AuthStatus.authenticated;

  /// Berilgan maydonlar bilan nusxa qaytaradi.
  ///
  /// [clearError] `true` bo'lsa, [errorMessage] majburan tozalanadi.
  AuthState copyWith({
    AuthStatus? status,
    UserProfile? profile,
    String? role,
    bool? isLoading,
    String? errorMessage,
    bool clearError = false,
  }) {
    return AuthState(
      status: status ?? this.status,
      profile: profile ?? this.profile,
      role: role ?? this.role,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }
}

/// Global autentifikatsiya holatini boshqaruvchi [StateNotifier] (20.1).
///
/// Mas'uliyatlari:
///  - `bootstrap`: startda saqlangan tokenni tekshirib, profilni yuklaydi
///    (R2.1) yoki kirilmagan holatga o'tadi.
///  - `login`/`register`: kredensiallar bilan kirib, tokenlarni saqlaydi va
///    profilni yuklaydi (R1.1, R2.1).
///  - `logout`: tokenlarni bekor qiladi va kirilmagan holatga o'tadi (R2.4).
///  - `forgotPassword`/`resetPassword`: parolni tiklash passthrough'lari (R3).
///  - `updateProfile`: profilni yangilab, global holatni sinxronlaydi (R5.2).
///  - `authEventsProvider.stream` ni tinglab, `AuthEvent.unauthorized`
///    kelganda majburiy logout qiladi → login'ga yo'naltirish (R2.3).
class AuthNotifier extends StateNotifier<AuthState> {
  final AuthApi _authApi;
  final UsersApi _usersApi;
  final TokenStore _tokenStore;
  final AuthEvents _authEvents;

  StreamSubscription<AuthEvent>? _authEventsSub;

  /// Bog'liqliklar bilan notifierni yaratadi va auth hodisalariga obuna bo'ladi.
  AuthNotifier({
    required AuthApi authApi,
    required UsersApi usersApi,
    required TokenStore tokenStore,
    required AuthEvents authEvents,
  })  : _authApi = authApi,
        _usersApi = usersApi,
        _tokenStore = tokenStore,
        _authEvents = authEvents,
        super(const AuthState.unknown()) {
    // Sessiya yaroqsiz bo'lganda (refresh ham ishlamadi) majburiy logout (R2.3).
    _authEventsSub = _authEvents.stream.listen((event) {
      if (event == AuthEvent.unauthorized) {
        _forceUnauthenticated();
      }
    });
  }

  /// Ilova ishga tushganda saqlangan sessiyani tiklaydi (R2.1).
  ///
  /// Saqlangan access token bo'lsa, profilni yuklab kirilgan holatga o'tadi;
  /// aks holda (yoki xatoda) kirilmagan holatga o'tadi.
  Future<void> bootstrap() async {
    final accessToken = await _tokenStore.readAccessToken();
    if (accessToken == null || accessToken.isEmpty) {
      state = const AuthState.unauthenticated();
      return;
    }
    try {
      final profile = await _usersApi.getMe();
      state = AuthState.authenticated(
        profile: profile,
        role: _roleFromAccessToken(accessToken),
      );
    } on ApiException {
      // Token mavjud, lekin yaroqsiz/eskirgan — toza kirilmagan holatga o't.
      await _tokenStore.clear();
      state = const AuthState.unauthenticated();
    }
  }

  /// Telefon va parol bilan tizimga kiradi (R2.1).
  ///
  /// Muvaffaqiyatda tokenlar [AuthApi] tomonidan saqlanadi, profil yuklanadi va
  /// holat kirilganga o'tadi. Xatoda holat kirilmaganga, [AuthState.errorMessage]
  /// esa foydalanuvchiga ko'rsatiladigan matnga o'rnatiladi.
  Future<bool> login({required String phone, required String password}) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final tokens = await _authApi.login(
        LoginRequest(phone: phone, password: password),
      );
      final profile = await _usersApi.getMe();
      state = AuthState.authenticated(
        profile: profile,
        role: _roleFromAccessToken(tokens.accessToken),
      );
      return true;
    } on ApiException catch (e) {
      state = AuthState.unauthenticated(errorMessage: authErrorMessage(e));
      return false;
    }
  }

  /// Yangi hisob yaratadi va so'ng avtomatik kiradi (R1.1).
  ///
  /// Avval `register`, keyin `login` chaqiriladi; muvaffaqiyatda holat
  /// kirilganga o'tadi.
  Future<bool> register(RegisterRequest request) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      await _authApi.register(request);
      final tokens = await _authApi.login(
        LoginRequest(phone: request.phone, password: request.password),
      );
      final profile = await _usersApi.getMe();
      state = AuthState.authenticated(
        profile: profile,
        role: _roleFromAccessToken(tokens.accessToken),
      );
      return true;
    } on ApiException catch (e) {
      state = AuthState.unauthenticated(errorMessage: authErrorMessage(e));
      return false;
    }
  }

  /// Tizimdan chiqadi (R2.4).
  ///
  /// Backend `logout` "best-effort" chaqiriladi (tarmoq xatosi e'tiborsiz
  /// qoldiriladi); mahalliy tokenlar har holda tozalanadi va holat
  /// kirilmaganga o'tadi.
  Future<void> logout() async {
    try {
      await _authApi.logout();
    } on ApiException {
      // Best-effort: server xatosi bo'lsa ham mahalliy sessiyani tozalaymiz.
    } finally {
      await _tokenStore.clear();
      state = const AuthState.unauthenticated();
    }
  }

  /// Parolni tiklash kodini so'raydi (R3.1, R3.2). Passthrough.
  Future<MessageResponse> forgotPassword(String phone) {
    return _authApi.forgotPassword(ForgotPasswordRequest(phone: phone));
  }

  /// Tasdiqlash kodi bilan parolni yangilaydi (R3.3–R3.7). Passthrough.
  Future<MessageResponse> resetPassword({
    required String phone,
    required String code,
    required String newPassword,
  }) {
    return _authApi.resetPassword(
      ResetPasswordRequest(phone: phone, code: code, newPassword: newPassword),
    );
  }

  /// Profilni yangilaydi va global holatni sinxronlaydi (R5.2).
  ///
  /// Muvaffaqiyatda [AuthState.profile] yangilangan profil bilan almashtiriladi.
  Future<UserProfile> updateProfile(ProfileUpdateRequest request) async {
    final updated = await _usersApi.updateMe(request);
    state = state.copyWith(profile: updated);
    return updated;
  }

  /// Tashqi xato xabarini tozalaydi (UI qayta urinishdan oldin chaqiradi).
  void clearError() {
    if (state.errorMessage != null) {
      state = state.copyWith(clearError: true);
    }
  }

  /// `AuthEvent.unauthorized` kelganda majburiy kirilmagan holatga o'tadi (R2.3).
  void _forceUnauthenticated() {
    // Tokenlar interseptorda allaqachon tozalangan bo'lishi mumkin; baribir
    // mahalliy holatni kirilmaganga o'tkazamiz (login'ga yo'naltirish).
    unawaited(_tokenStore.clear());
    state = const AuthState.unauthenticated(
      errorMessage: 'Sessiya muddati tugadi, qayta kiring',
    );
  }

  @override
  void dispose() {
    _authEventsSub?.cancel();
    super.dispose();
  }
}

/// JWT access token'ning `role` da'vosini (claim) ajratib oladi (R4 — rol).
///
/// Token `header.payload.signature` ko'rinishida; `payload` base64url-JSON.
/// Imzo bu yerda tekshirilmaydi (faqat UI uchun rolni o'qish) — server har bir
/// so'rovda tokenni baribir tekshiradi. Har qanday xatoda `null` qaytadi.
String? _roleFromAccessToken(String token) {
  try {
    final parts = token.split('.');
    if (parts.length != 3) {
      return null;
    }
    final payload = utf8.decode(base64Url.decode(base64Url.normalize(parts[1])));
    final decoded = jsonDecode(payload);
    if (decoded is Map && decoded['role'] is String) {
      return decoded['role'] as String;
    }
    return null;
  } catch (_) {
    return null;
  }
}

/// [ApiException] ni foydalanuvchiga ko'rsatiladigan (o'zbekcha) matnga keltiradi.
///
/// Tarmoq xatosi uchun aniqroq maslahat beradi; aks holda backendning tayyor
/// (o'zbekcha) xabarini ishlatadi (R2.2 umumiy xabarini saqlaydi).
String authErrorMessage(ApiException e) {
  switch (e.code) {
    case 'network_error':
      return 'Tarmoq xatosi: internet aloqasini tekshiring';
    case 'unknown_error':
      return e.message.isEmpty ? 'Nomaʼlum xatolik yuz berdi' : e.message;
    default:
      return e.message;
  }
}
