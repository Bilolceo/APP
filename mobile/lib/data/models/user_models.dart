import 'json_utils.dart';

/// Foydalanuvchi / profil DTO modellari (R5, R4).
///
/// Maydon nomlari backend `app/api/schemas/user.py` bilan aniq mos keladi.

/// To'liq foydalanuvchi profili (R5.1).
///
/// Backend: `ProfileResponse`.
class UserProfile {
  /// Foydalanuvchi ID.
  final int id;

  /// To'liq ism.
  final String fullName;

  /// Telefon raqami (o'zgarmas).
  final String phone;

  /// Ish joyi (tashkilot) ID.
  final int? organizationId;

  /// Hudud ID.
  final int? regionId;

  /// Lavozim.
  final String? position;

  /// Ish staji (yil).
  final int? experienceYears;

  /// Ta'lim darajasi.
  final String? educationLevel;

  /// Malaka oshirish kurslari.
  final String? qualificationCourses;

  /// Sertifikatlar.
  final String? certificates;

  /// Tashkilot turi.
  final String? orgType;

  /// Push bildirishnomalar yoqilganligi.
  final bool notificationsEnabled;

  /// Profilni yaratadi.
  const UserProfile({
    required this.id,
    required this.fullName,
    required this.phone,
    required this.notificationsEnabled,
    this.organizationId,
    this.regionId,
    this.position,
    this.experienceYears,
    this.educationLevel,
    this.qualificationCourses,
    this.certificates,
    this.orgType,
  });

  /// JSON xaritadan [UserProfile] yaratadi.
  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      id: JsonParse.asInt(json['id']),
      fullName: JsonParse.asString(json['full_name']),
      phone: JsonParse.asString(json['phone']),
      organizationId: JsonParse.asIntOrNull(json['organization_id']),
      regionId: JsonParse.asIntOrNull(json['region_id']),
      position: JsonParse.asStringOrNull(json['position']),
      experienceYears: JsonParse.asIntOrNull(json['experience_years']),
      educationLevel: JsonParse.asStringOrNull(json['education_level']),
      qualificationCourses:
          JsonParse.asStringOrNull(json['qualification_courses']),
      certificates: JsonParse.asStringOrNull(json['certificates']),
      orgType: JsonParse.asStringOrNull(json['org_type']),
      notificationsEnabled: JsonParse.asBool(
        json['notifications_enabled'],
        fallback: true,
      ),
    );
  }

  /// JSON xaritaga aylantiradi.
  Map<String, dynamic> toJson() => {
        'id': id,
        'full_name': fullName,
        'phone': phone,
        'organization_id': organizationId,
        'region_id': regionId,
        'position': position,
        'experience_years': experienceYears,
        'education_level': educationLevel,
        'qualification_courses': qualificationCourses,
        'certificates': certificates,
        'org_type': orgType,
        'notifications_enabled': notificationsEnabled,
      };
}

/// Profilni yangilash so'rovi — tahrirlanadigan maydonlar (R5.2, R5.3).
///
/// Backend: `ProfileUpdateRequest`. Faqat berilgan (null bo'lmagan) maydonlar
/// yuboriladi (qisman yangilash — `exclude_unset` semantikasi). Telefonni
/// o'zgartirish backend tomonidan rad etiladi (R5.4).
class ProfileUpdateRequest {
  /// To'liq ism (1–200 belgi).
  final String? fullName;

  /// Ish joyi (tashkilot) ID.
  final int? organizationId;

  /// Hudud ID.
  final int? regionId;

  /// Lavozim.
  final String? position;

  /// Ish staji (0–60).
  final int? experienceYears;

  /// Ta'lim darajasi.
  final String? educationLevel;

  /// Malaka oshirish kurslari.
  final String? qualificationCourses;

  /// Sertifikatlar.
  final String? certificates;

  /// Tashkilot turi.
  final String? orgType;

  /// Push bildirishnomalar yoqilganligi.
  final bool? notificationsEnabled;

  /// So'rovni yaratadi.
  const ProfileUpdateRequest({
    this.fullName,
    this.organizationId,
    this.regionId,
    this.position,
    this.experienceYears,
    this.educationLevel,
    this.qualificationCourses,
    this.certificates,
    this.orgType,
    this.notificationsEnabled,
  });

  /// So'rov tanasi uchun JSON xaritaga aylantiradi (faqat berilgan maydonlar).
  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{};
    if (fullName != null) map['full_name'] = fullName;
    if (organizationId != null) map['organization_id'] = organizationId;
    if (regionId != null) map['region_id'] = regionId;
    if (position != null) map['position'] = position;
    if (experienceYears != null) map['experience_years'] = experienceYears;
    if (educationLevel != null) map['education_level'] = educationLevel;
    if (qualificationCourses != null) {
      map['qualification_courses'] = qualificationCourses;
    }
    if (certificates != null) map['certificates'] = certificates;
    if (orgType != null) map['org_type'] = orgType;
    if (notificationsEnabled != null) {
      map['notifications_enabled'] = notificationsEnabled;
    }
    return map;
  }
}
