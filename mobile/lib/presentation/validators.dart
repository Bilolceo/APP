/// Mijoz tomonidagi forma validatorlari (R1.5, R1.6, R5.3).
///
/// Bu qoidalar backend validatsiyasini (`app/domain/auth_validation.py` va
/// profil servisidagi cheklovlar) **aks ettiradi**, lekin uni almashtirmaydi —
/// haqiqiy haqiqat manbai backend. Mijoz validatsiyasi foydalanuvchiga tez,
/// keraksiz tarmoq so'rovisiz fikr-mulohaza (feedback) berish uchun xizmat
/// qiladi. Funksiyalar `TextFormField.validator` shartnomasiga mos: yaroqli
/// bo'lsa `null`, aks holda o'zbekcha xato matnini qaytaradi.

/// Telefon formati (R1.6): `+998` bilan boshlanib, jami 13 belgi.
const String kPhonePrefix = '+998';

/// Telefon raqami uzunligi (R1.6).
const int kPhoneLength = 13;

/// Parol minimal uzunligi (R1.5).
const int kPasswordMinLength = 8;

/// Parol maksimal uzunligi (R1.5).
const int kPasswordMaxLength = 64;

/// To'liq ism / matnli profil maydonlari maksimal uzunligi (R1.1, R5.3).
const int kTextMaxLength = 200;

/// Ish staji quyi chegarasi (R5.3).
const int kExperienceMin = 0;

/// Ish staji yuqori chegarasi (R5.3).
const int kExperienceMax = 60;

/// Parolni tiklash kodining uzunligi (R3.5).
const int kResetCodeLength = 6;

/// Yaroqli rollar whitelisti (R1.7).
const List<String> kValidRoles = <String>['Rahbar', 'Ekspert', 'Administrator'];

/// Mijoz tomonidagi forma validatorlari to'plami.
class Validators {
  const Validators._();

  /// Telefon raqami formatini tekshiradi (R1.6).
  static String? phone(String? value) {
    final v = value?.trim() ?? '';
    if (v.isEmpty) {
      return 'Telefon raqami majburiy';
    }
    if (!v.startsWith(kPhonePrefix) || v.length != kPhoneLength) {
      return 'Telefon +998 bilan boshlanib, 13 belgi bo\'lishi kerak';
    }
    // Prefiksdan keyingi belgilar faqat raqam bo'lishi kerak.
    final digits = v.substring(kPhonePrefix.length);
    if (!RegExp(r'^\d+$').hasMatch(digits)) {
      return 'Telefon raqami faqat raqamlardan iborat bo\'lishi kerak';
    }
    return null;
  }

  /// Parol uzunligini tekshiradi (R1.5).
  static String? password(String? value) {
    final v = value ?? '';
    if (v.isEmpty) {
      return 'Parol majburiy';
    }
    if (v.length < kPasswordMinLength || v.length > kPasswordMaxLength) {
      return 'Parol $kPasswordMinLength–$kPasswordMaxLength belgi bo\'lishi kerak';
    }
    return null;
  }

  /// Yangi parol uzunligini tekshiradi (R3.6 — kamida 8 belgi).
  static String? newPassword(String? value) {
    final v = value ?? '';
    if (v.isEmpty) {
      return 'Yangi parol majburiy';
    }
    if (v.length < kPasswordMinLength) {
      return 'Yangi parol kamida $kPasswordMinLength belgidan iborat bo\'lishi kerak';
    }
    return null;
  }

  /// Majburiy matnli maydon (bo'sh emas, ≤200 belgi) — R1.3, R1.1.
  static String? requiredText(String? value, {String label = 'Maydon'}) {
    final v = value?.trim() ?? '';
    if (v.isEmpty) {
      return '$label majburiy';
    }
    if (v.length > kTextMaxLength) {
      return '$label $kTextMaxLength belgidan oshmasligi kerak';
    }
    return null;
  }

  /// Ixtiyoriy matnli maydon (≤200 belgi) — R5.3.
  static String? optionalText(String? value, {String label = 'Maydon'}) {
    final v = value?.trim() ?? '';
    if (v.length > kTextMaxLength) {
      return '$label $kTextMaxLength belgidan oshmasligi kerak';
    }
    return null;
  }

  /// Tasdiqlash kodi formatini tekshiradi (R3.5 — 6 ta raqam).
  static String? resetCode(String? value) {
    final v = value?.trim() ?? '';
    if (v.isEmpty) {
      return 'Tasdiqlash kodi majburiy';
    }
    if (!RegExp(r'^\d{6}$').hasMatch(v)) {
      return 'Kod $kResetCodeLength ta raqamdan iborat bo\'lishi kerak';
    }
    return null;
  }

  /// Ixtiyoriy ish staji maydonini tekshiradi (R5.3 — 0–60 butun son).
  ///
  /// Bo'sh qiymat yaroqli (maydon ixtiyoriy); aks holda 0–60 oralig'idagi
  /// butun son bo'lishi shart (manfiy/kasrli/60 dan katta rad etiladi).
  static String? optionalExperienceYears(String? value) {
    final v = value?.trim() ?? '';
    if (v.isEmpty) {
      return null;
    }
    final parsed = int.tryParse(v);
    if (parsed == null) {
      return 'Ish staji butun son bo\'lishi kerak';
    }
    if (parsed < kExperienceMin || parsed > kExperienceMax) {
      return 'Ish staji $kExperienceMin–$kExperienceMax oralig\'ida bo\'lishi kerak';
    }
    return null;
  }
}
