# Requirements Document

## Introduction

"MTT Menejer Diagnostika" — maktabgacha ta'lim tashkiloti (MTT) rahbarlarining
intellektual salohiyatini, kasbiy, reflexiv, kommunikativ va boshqaruv
kompetensiyalarini raqamli tarzda diagnostika qilish, baholash, monitoring qilish
hamda natijalar asosida individual rivojlanish tavsiyalarini shakllantirish uchun
mo'ljallangan Android mobil ilovasidir.

Tizim quyidagi ko'rsatkichlarni o'lchaydi: bilim darajasi, analitik fikrlash,
strategik qaror qabul qilish, pedagogik vaziyatlarni baholash qobiliyati,
o'z-o'zini tahlil qilish darajasi, innovatsion yondashuvga tayyorlik, AKT
(axborot-kommunikatsiya texnologiyalari) kompetensiyasi va boshqaruv samaradorligi.

Ilova uch toifadagi foydalanuvchiga xizmat ko'rsatadi: MTT rahbari (asosiy
foydalanuvchi), ekspert/metodist va administrator. Tizim mobil ilova (Android),
REST API va backend xizmati hamda PostgreSQL ma'lumotlar bazasidan iborat
arxitekturaga ega.

### EARS Yozuv Konvensiyasi (notation)

Talablar EARS (Easy Approach to Requirements Syntax) namunalariga muvofiq
yoziladi. Tushunarlilik va xalqaro standartga moslik uchun EARS kalit so'zlari
(WHEN, WHILE, IF ... THEN, WHERE, THE ... SHALL) formal yozuv sifatida ingliz
tilida saqlanadi, talab mazmuni esa o'zbek tilida bayon etiladi. "SHALL" — talab
majburiyligini bildiradi.

### MVP doirasi (Scope)

Ushbu hujjat MVP (minimal hayotiy mahsulot) doirasidagi barcha talablarni
qamrab oladi: ro'yxatdan o'tish va kirish, profil, testlar ro'yxati, test
topshirish, ball hisoblash, kompetensiya bo'yicha baholash, tavsiyalar,
portfolio, admin test/savol API'lari va asosiy analitika. MVP'dan keyingi
imkoniyatlar (Requirement 18) alohida belgilangan va arxitektura ularga
kengaytirilishi uchun tayyor bo'lishi shart.

## Glossary

- **Tizim**: "MTT Menejer Diagnostika" dasturiy kompleksining umumiy nomi (mobil ilova, REST API va backend xizmati birgalikda).
- **Mobil_Ilova**: Android qurilmalarida ishlaydigan, foydalanuvchi interfeysini taqdim etuvchi komponent.
- **Backend_Xizmati**: Server tomonidagi biznes-mantiqни bajaruvchi va REST API'ni taqdim etuvchi komponent.
- **REST_API**: Mobil_Ilova va Backend_Xizmati o'rtasidagi HTTP/REST interfeysi.
- **Autentifikatsiya_Moduli**: Ro'yxatdan o'tish, kirish, token boshqaruvi va parolni tiklash uchun mas'ul komponent.
- **Profil_Moduli**: Foydalanuvchi profili ma'lumotlarini boshqaruvchi komponent.
- **Diagnostika_Moduli**: Testlar ro'yxati, test topshirish jarayoni va savollarni taqdim etuvchi komponent.
- **Baholash_Moduli**: Test javoblari asosida ball va foizni hisoblovchi hamda darajani aniqlovchi komponent.
- **Analitika_Moduli**: Natijalarni grafik ko'rinishda taqdim etuvchi va dinamikani hisoblovchi komponent.
- **Tavsiya_Moduli**: Natija asosida individual rivojlanish tavsiyalarini tanlovchi komponent.
- **Portfolio_Moduli**: Foydalanuvchi sertifikatlari, hujjatlari va fayllarini boshqaruvchi komponent.
- **Reyting_Moduli**: Foydalanuvchilar reytingini hisoblovchi va taqdim etuvchi komponent.
- **Ekspert_Moduli**: Ekspert/metodist tomonidan rahbarni qo'shimcha baholash funksiyasini ta'minlovchi komponent.
- **Admin_Moduli**: Administrator uchun ma'lumotlarni boshqarish (CRUD) funksiyalarini ta'minlovchi komponent.
- **Hisobot_Moduli**: Admin va ekspert uchun jamlangan hisobotlarni shakllantiruvchi komponent.
- **Bildirishnoma_Xizmati**: Push bildirishnomalarni yuboruvchi komponent.
- **Rahbar**: MTT rahbari roli — asosiy foydalanuvchi (test topshiruvchi).
- **Ekspert**: Ekspert/metodist roli — biriktirilgan tashkilotlar rahbarlarini baholovchi foydalanuvchi.
- **Administrator**: Tizimni va kontentni boshqaruvchi yuqori imtiyozli foydalanuvchi roli.
- **Kompetensiya**: Baholanadigan kasbiy/intellektual yo'nalish (masalan, boshqaruv, pedagogik, kommunikativ, AKT, innovatsion).
- **Test**: Bir yoki bir nechta kompetensiyaga bog'langan savollar to'plami.
- **Savol**: Testdagi alohida topshiriq; kompetensiyaga bog'langan va ball qiymatiga ega.
- **Likert_Shkalasi**: Beshlik baholash shkalasi (mutlaqo qo'shilmayman, qisman qo'shilmayman, neytral, qisman qo'shilaman, to'liq qo'shilaman).
- **Daraja**: Foiz natijasiga mos baholash toifasi: Past (0% ≤ foiz ≤ 40%), O'rta (40% < foiz ≤ 60%), Yaxshi (60% < foiz ≤ 80%), Yuqori (80% < foiz ≤ 100%).
- **Tavsiya**: Kompetensiya va darajaga bog'langan rivojlanish ko'rsatmasi.
- **JWT**: JSON Web Token — autentifikatsiya va avtorizatsiya uchun ishlatiladigan token.
- **MTT**: Maktabgacha ta'lim tashkiloti.
- **AKT**: Axborot-kommunikatsiya texnologiyalari kompetensiyasi.

## Requirements

### Requirement 1: Ro'yxatdan o'tish

**User Story:** MTT rahbari sifatida men telefon raqamim va shaxsiy
ma'lumotlarim orqali ro'yxatdan o'tmoqchiman, shunda tizimga kirib diagnostika
testlarini topshira olaman.

#### Acceptance Criteria

1. WHEN foydalanuvchi yaroqli telefon raqami (+998 bilan boshlanuvchi, jami 13 belgi), uzunligi 8–64 belgi bo'lgan parol, to'liq ism (1–200 belgi), tashkilot nomi (1–200 belgi), lavozim (1–200 belgi), hudud va yaroqli rol (Rahbar, Ekspert yoki Administrator) ni kiritib ro'yxatdan o'tishni tasdiqlaydi, THE Autentifikatsiya_Moduli SHALL yangi hisob yaratadi va tasdiq javobini qaytaradi.
2. IF kiritilgan telefon raqami allaqachon ro'yxatdan o'tgan bo'lsa, THEN THE Autentifikatsiya_Moduli SHALL ro'yxatdan o'tishni rad etadi, yangi hisob yaratmaydi va telefon raqami bandligi haqida xato xabarini qaytaradi.
3. IF majburiy maydonlardan (telefon raqami, parol, to'liq ism, rol) biri kiritilmagan yoki faqat bo'sh joy belgilaridan iborat bo'lsa, THEN THE Autentifikatsiya_Moduli SHALL ro'yxatdan o'tishni rad etadi, yangi hisob yaratmaydi va to'ldirilmagan maydonni ko'rsatuvchi xato xabarini qaytaradi.
4. WHEN yangi hisob yaratiladi, THE Autentifikatsiya_Moduli SHALL parolni xeshlangan ko'rinishda saqlaydi va ochiq matnda saqlamaydi.
5. IF kiritilgan parol uzunligi 8 belgidan kam yoki 64 belgidan ko'p bo'lsa, THEN THE Autentifikatsiya_Moduli SHALL ro'yxatdan o'tishni rad etadi, yangi hisob yaratmaydi va parol talablari haqida xato xabarini qaytaradi.
6. IF kiritilgan telefon raqami formati noto'g'ri bo'lsa (+998 bilan boshlanmasa yoki jami 13 belgi bo'lmasa), THEN THE Autentifikatsiya_Moduli SHALL ro'yxatdan o'tishni rad etadi, yangi hisob yaratmaydi va telefon raqami formati noto'g'ri ekanligini bildiruvchi xato xabarini qaytaradi.
7. IF kiritilgan rol yaroqli rollar ro'yxatida (Rahbar, Ekspert, Administrator) bo'lmasa, THEN THE Autentifikatsiya_Moduli SHALL ro'yxatdan o'tishni rad etadi, yangi hisob yaratmaydi va rol noto'g'ri ekanligini bildiruvchi xato xabarini qaytaradi.

### Requirement 2: Tizimga kirish va token boshqaruvi

**User Story:** Ro'yxatdan o'tgan foydalanuvchi sifatida men telefon raqamim va
parolim orqali tizimga xavfsiz kirmoqchiman, shunda o'z ma'lumotlarimdan
foydalana olaman.

#### Acceptance Criteria

1. WHEN foydalanuvchi to'g'ri telefon raqami va parol bilan kirishni so'raydi, THE Autentifikatsiya_Moduli SHALL amal qilish muddati 15 daqiqa bo'lgan JWT kirish tokeni va amal qilish muddati 30 kun bo'lgan yangilash (refresh) tokenini qaytaradi.
2. IF foydalanuvchi noto'g'ri telefon raqami yoki parol bilan kirishni so'rasa, THEN THE Autentifikatsiya_Moduli SHALL kirishni rad etadi va telefon raqami yoki parolning mos kelmaganligini (qaysi biri xato ekanligini oshkor qilmagan holda) bildiruvchi xato xabarini qaytaradi.
3. WHEN yaroqli va bekor qilinmagan yangilash tokeni bilan token yangilash so'ralganda, THE Autentifikatsiya_Moduli SHALL amal qilish muddati 15 daqiqa bo'lgan yangi JWT kirish tokenini qaytaradi.
4. WHEN foydalanuvchi tizimdan chiqishni (logout) so'raydi, THE Autentifikatsiya_Moduli SHALL foydalanuvchining amaldagi kirish va yangilash tokenlarini bekor qiladi va shundan so'ng ushbu tokenlar bilan yuborilgan keyingi so'rovlarni rad etadi.
5. IF muddati o'tgan yoki yaroqsiz token bilan himoyalangan resursga murojaat qilinsa, THEN THE REST_API SHALL so'rovni rad etadi va 401 avtorizatsiya xatosini qaytaradi.
6. IF muddati o'tgan, yaroqsiz yoki bekor qilingan yangilash tokeni bilan token yangilash so'ralsa, THEN THE Autentifikatsiya_Moduli SHALL token yangilashni rad etadi va qaytadan tizimga kirishni talab qiluvchi xato xabarini qaytaradi.
7. IF bir foydalanuvchi hisobi uchun ketma-ket 5 marta noto'g'ri parol bilan kirish urinishi amalga oshirilsa, THEN THE Autentifikatsiya_Moduli SHALL ushbu hisob uchun kirishni 15 daqiqa davomida vaqtincha bloklaydi va kirish so'rovini rad etadi.

### Requirement 3: Parolni tiklash

**User Story:** Parolni unutgan foydalanuvchi sifatida men parolimni
tiklamoqchiman, shunda hisobimga qayta kira olaman.

#### Acceptance Criteria

1. WHEN foydalanuvchi ro'yxatdan o'tgan telefon raqami bilan parolni tiklashni so'raydi, THE Autentifikatsiya_Moduli SHALL parolni tiklash jarayonini boshlaydi va 6 raqamli, yuborilgandan keyin 15 daqiqa davomida amal qiladigan tasdiqlash kodini yuboradi.
2. IF parolni tiklash ro'yxatdan o'tmagan telefon raqami uchun so'ralsa, THEN THE Autentifikatsiya_Moduli SHALL hisob mavjudligini oshkor qilmaydigan va 1-mezondagi muvaffaqiyatli javobdan farqlanmaydigan umumiy javob qaytaradi.
3. WHEN foydalanuvchi to'g'ri va muddati o'tmagan tasdiqlash kodi hamda kamida 8 belgidan iborat yangi parolni kiritadi, THE Autentifikatsiya_Moduli SHALL parolni xeshlangan ko'rinishda yangilaydi, ishlatilgan tasdiqlash kodini bekor qiladi va tasdiq javobini qaytaradi.
4. IF tasdiqlash kodi noto'g'ri yoki yuborilganidan keyin 15 daqiqadan ko'p vaqt o'tgan bo'lsa, THEN THE Autentifikatsiya_Moduli SHALL parolni yangilashni rad etadi, mavjud parolni o'zgartirmaydi va kod yaroqsizligini bildiruvchi xato xabarini qaytaradi.
5. WHEN tasdiqlash kodi tekshiriladi, THE Autentifikatsiya_Moduli SHALL kodning 6 raqamli formatda ekanligini va kutilgan kodga to'liq mos kelishini talab qiladi.
6. IF kiritilgan yangi parol uzunligi 8 belgidan kam bo'lsa, THEN THE Autentifikatsiya_Moduli SHALL parolni yangilashni rad etadi va parol talablari haqida xato xabarini qaytaradi.
7. IF bitta tasdiqlash kodi uchun noto'g'ri kod 5 martadan ko'p kiritilsa, THEN THE Autentifikatsiya_Moduli SHALL ushbu tasdiqlash kodini bekor qiladi va parolni tiklashni qaytadan so'rashni talab qiluvchi xato xabarini qaytaradi.

### Requirement 4: Rolga asoslangan kirish nazorati (RBAC)

**User Story:** Tizim egasi sifatida men har bir foydalanuvchi faqat o'z roliga
ruxsat etilgan ma'lumotlarga kira olishini istayman, shunda maxfiylik va
xavfsizlik ta'minlanadi.

#### Acceptance Criteria

1. WHILE foydalanuvchi Rahbar roli bilan autentifikatsiyalangan sessiyada, THE REST_API SHALL foydalanuvchiga faqat o'zi egasi bo'lgan profil, faol diagnostika testlari va o'z natijalariga kirish ruxsatini beradi hamda boshqa foydalanuvchilarning profili va natijalariga kirishni rad etadi.
2. WHILE foydalanuvchi Ekspert roli bilan autentifikatsiyalangan sessiyada, THE REST_API SHALL ekspertga faqat o'ziga biriktirilgan tashkilotlar rahbarlarining natijalariga kirish ruxsatini beradi hamda biriktirilmagan tashkilotlar rahbarlarining natijalariga kirishni rad etadi.
3. WHILE foydalanuvchi Administrator roli bilan autentifikatsiyalangan sessiyada, THE REST_API SHALL administratorga barcha foydalanuvchilar profili, testlar va natijalariga kirish ruxsatini beradi.
4. WHEN himoyalangan resursga murojaat qilinadi, THE REST_API SHALL foydalanuvchining roli hamda resursga egalik/biriktirilganlik shartini birgalikda tekshiradi va shu asosda kirishga ruxsat beradi yoki rad etadi.
5. IF foydalanuvchi o'z roli, egaligi yoki biriktirilganligi bo'yicha ruxsat etilmagan resursga murojaat qilsa, THEN THE REST_API SHALL so'rovni rad etadi, hech qanday ma'lumotni o'zgartirmaydi yoki oshkor qilmaydi va 403 ruxsat yo'q xatosini qaytaradi.

### Requirement 5: Profil ko'rish va tahrirlash

**User Story:** Foydalanuvchi sifatida men o'z professional profil ma'lumotlarimni
kiritishni va tahrirlashni istayman, shunda diagnostika natijalarim shaxsiy
kontekstda tahlil qilinadi.

#### Acceptance Criteria

1. WHEN foydalanuvchi o'z profilini ko'rishni so'raydi, THE Profil_Moduli SHALL to'liq ism, telefon, ish joyi, lavozim, ish staji, ta'lim darajasi, malaka oshirish kurslari, sertifikatlar, hudud va tashkilot turini qaytaradi.
2. WHEN foydalanuvchi profilning tahrirlanishi mumkin bo'lgan maydonlarini (to'liq ism, ish joyi, lavozim, ish staji, ta'lim darajasi, malaka oshirish kurslari, sertifikatlar, hudud, tashkilot turi) yaroqli qiymatlar bilan yangilaydi, THE Profil_Moduli SHALL o'zgarishlarni saqlaydi va yangilangan profilni qaytaradi.
3. IF profilni tahrirlashda ish staji 0–60 oralig'idagi butun sondan tashqari qiymat (manfiy, kasrli yoki 60 dan katta) yoki biror matnli maydon 200 belgidan uzun bo'lsa, THEN THE Profil_Moduli SHALL saqlashni rad etadi, mavjud ma'lumotlarni o'zgartirmaydi va qaysi maydon yaroqsizligini ko'rsatuvchi validatsiya xatosini qaytaradi. Bunday validatsiya faqat foydalanuvchi profilni faol tahrirlash jarayonida amalga oshiriladi.
4. IF foydalanuvchi profil orqali telefon raqamini o'zgartirishga urinsa, THEN THE Profil_Moduli SHALL o'zgartirishni rad etadi va telefon raqami (hisob identifikatori) tahrirlab bo'lmasligini bildiruvchi xato xabarini qaytaradi.
5. THE Profil_Moduli SHALL profil ma'lumotlarini diagnostika natijalarini tahlil qilishda kontekst sifatida taqdim etadi.

### Requirement 6: Diagnostika testlari ro'yxati

**User Story:** Rahbar sifatida men mavjud diagnostika testlari ro'yxatini
ko'rmoqchiman, shunda topshirmoqchi bo'lgan testni tanlay olaman.

#### Acceptance Criteria

1. WHEN foydalanuvchi testlar ro'yxatini so'raydi, THE Diagnostika_Moduli SHALL faqat faol (is_active = true) testlarni har biri uchun noyob identifikatori, nomi, tavsifi, toifasi va davomiyligi (daqiqalarda) bilan qaytaradi.
2. THE Diagnostika_Moduli SHALL testlarni quyidagi yo'nalishlar bo'yicha toifalaydi: kognitiv diagnostika, kompetensiya diagnostikasi, reflexiv diagnostika va situatsion (case-study) diagnostika.
3. WHEN foydalanuvchi ma'lum bir testni noyob identifikatori bo'yicha tanlaydi, THE Diagnostika_Moduli SHALL test tafsilotlarini (nomi, tavsifi, toifasi, davomiyligi daqiqalarda va savollar soni) hamda savollar to'plamini (har bir savol matni va javob variantlari bilan) belgilangan tartibda qaytaradi.
4. IF mavjud bo'lmagan yoki faol bo'lmagan test so'ralsa, THEN THE Diagnostika_Moduli SHALL so'rovni rad etadi va test topilmadi xatosini qaytaradi.
5. WHEN foydalanuvchi testlar ro'yxatini so'raydi va hech qanday faol test mavjud bo'lmasa, THE Diagnostika_Moduli SHALL bo'sh ro'yxatni qaytaradi va xato qaytarmaydi.

### Requirement 7: Test topshirish jarayoni

**User Story:** Rahbar sifatida men tanlangan testni topshirmoqchiman, shunda
mening kompetensiyalarim baholanadi.

#### Acceptance Criteria

1. WHEN foydalanuvchi testni boshlaydi va shu testning tugatilmagan (yakunlanmagan) sessiyasi mavjud bo'lmasa, THE Diagnostika_Moduli SHALL yangi test sessiyasini yaratadi va boshlanish sanasi hamda vaqtini qayd etadi.
2. WHILE test topshirilmoqda, THE Mobil_Ilova SHALL joriy savol matnini, javob variantlarini, qolgan vaqtni (test davomiyligidan o'tgan vaqt ayirilgan holda) va jarayon ko'rsatkichini (javob berilgan savollar soni / jami savollar soni) ko'rsatadi.
3. WHERE test reflexiv diagnostika turiga tegishli, THE Mobil_Ilova SHALL javoblarni Likert_Shkalasi (mutlaqo qo'shilmayman, qisman qo'shilmayman, neytral, qisman qo'shilaman, to'liq qo'shilaman) ko'rinishida taqdim etadi.
4. WHERE test situatsion (case-study) turiga tegishli, THE Mobil_Ilova SHALL real boshqaruv vaziyatini va kamida ikkita yechim variantini ko'rsatadi hamda faqat bitta variant tanlashga ruxsat beradi.
5. WHEN sessiya boshlanish vaqtidan test davomiyligi o'tib muddat tugaydi, THE Diagnostika_Moduli SHALL testni avtomatik yakunlaydi, mavjud javoblarni topshirish uchun qabul qiladi va javob berilmagan savollarni javobsiz holatda belgilaydi.
6. WHEN foydalanuvchi barcha savollarga javob berilgan testni topshiradi, THE Diagnostika_Moduli SHALL javoblarni saqlaydi, sessiyani yakunlangan holatga o'tkazadi va javoblarni Baholash_Moduliga uzatadi.
7. IF foydalanuvchi allaqachon yakunlangan (topshirilgan) sessiyaga qayta javob yuborsa, THEN THE Diagnostika_Moduli SHALL takroriy topshirishni rad etadi, dastlabki saqlangan javoblarni o'zgartirmaydi va takroriy topshirish rad etilganini bildiruvchi xato xabarini qaytaradi.
8. IF foydalanuvchi muddat tugamagan holda javob berilmagan savollari mavjud testni topshirishga urinsa, THEN THE Diagnostika_Moduli SHALL topshirishni rad etadi va javob berilmagan savollar mavjudligini bildiruvchi xato xabarini qaytaradi.
9. IF foydalanuvchi mavjud bo'lmagan yoki o'ziga tegishli bo'lmagan sessiyaga javob topshirsa, THEN THE Diagnostika_Moduli SHALL so'rovni rad etadi va sessiya topilmadi xatosini qaytaradi.
10. IF foydalanuvchi shu test bo'yicha tugatilmagan sessiyasi mavjud bo'lganda testni qaytadan boshlashga urinsa, THEN THE Diagnostika_Moduli SHALL yangi sessiya yaratmaydi va mavjud tugatilmagan sessiyani davom ettiradi.

### Requirement 8: Ball hisoblash va daraja aniqlash

**User Story:** Rahbar sifatida men test topshirgach avtomatik natija olmoqchiman,
shunda intellektual salohiyatim darajasini bilaman.

#### Acceptance Criteria

1. WHEN test topshiriladi, THE Baholash_Moduli SHALL umumiy foizni (yig'ilgan ball / maksimal ball × 100) formulasi asosida 0–100% oralig'idagi va 2 kasr xonasigacha yaxlitlangan qiymat sifatida hisoblaydi.
2. WHEN umumiy foiz hisoblanadi, THE Baholash_Moduli SHALL darajani quyidagi uzluksiz oraliqlar bo'yicha aniqlaydi: 0% ≤ foiz ≤ 40% uchun Past, 40% < foiz ≤ 60% uchun O'rta, 60% < foiz ≤ 80% uchun Yaxshi, 80% < foiz ≤ 100% uchun Yuqori; shu tarzda har qanday kasrli foiz (masalan, 40.5% → O'rta) aynan bitta darajaga tegishli bo'ladi.
3. WHEN natija hisoblanadi, THE Baholash_Moduli SHALL har bir kompetensiya bo'yicha foizni (shu kompetensiyaga tegishli savollardan yig'ilgan ball / shu kompetensiya maksimal balli × 100) formulasi asosida 0–100% oralig'ida va 2 kasr xonasigacha yaxlitlangan holda hisoblaydi.
4. WHEN natija shakllantiriladi, THE Baholash_Moduli SHALL umumiy intellektual salohiyat balli, kompetensiya bo'yicha ballar, kuchli tomonlar, zaif tomonlar va keyingi qayta topshirish sanasini qaytaradi.
5. IF testda hech bo'lmaganda bitta kompetensiyaga bog'lanmagan savol bo'lsa, THEN THE Baholash_Moduli SHALL umumiy ballni hisoblaydi va bog'lanmagan savollarni kompetensiya foizidan tashqarida qoldiradi.
6. THE Baholash_Moduli SHALL har bir test natijasini foydalanuvchi, test, umumiy ball, foiz va daraja bilan birga saqlaydi.
7. WHEN natijaning ayrim tarkibiy qismlari (umumiy ball, kompetensiya ballari, kuchli tomonlar, zaif tomonlar yoki qayta topshirish sanasi) so'ralganda, THE Baholash_Moduli SHALL mavjud tarkibiy qismlarni to'liq natija shakllanishidan mustaqil ravishda qaytaradi va ayrim qismlar mavjud bo'lmasa qisman natijani qaytaradi.
8. IF testning yoki biror kompetensiyaning maksimal balli 0 ga teng bo'lsa, THEN THE Baholash_Moduli SHALL tegishli foizni nolga bo'lish amalini bajarmasdan 0% deb belgilaydi va natijani hisoblashni davom ettiradi.

### Requirement 9: Natijalar va analitika

**User Story:** Rahbar sifatida men natijalarimni grafik ko'rinishda va vaqt
o'tishi bilan o'sish dinamikasini ko'rmoqchiman, shunda rivojlanishimni
kuzata olaman.

#### Acceptance Criteria

1. WHEN foydalanuvchi analitikani so'raydi, THE Analitika_Moduli SHALL umumiy ballni (0 dan 100 gacha foizda), kompetensiyalar bo'yicha taqsimotni va o'sish dinamikasini har bir natija uchun sana bilan belgilangan, xronologik (eng eskidan eng yangiga) tartibda joylashtirilgan umumiy foiz qiymatlari ketma-ketligi sifatida qaytaradi.
2. THE Analitika_Moduli SHALL kompetensiyalar taqsimotini radar diagramma, jarayon ko'rsatkichi (progress bar), chiziqli diagramma (line chart) va toifa ball kartochkasi ko'rinishida taqdim etish uchun zarur ma'lumotlarni qaytaradi.
3. WHEN foydalanuvchining ikki yoki undan ortiq test natijasi mavjud bo'lsa, THE Analitika_Moduli SHALL joriy natijaning umumiy foizini bevosita oldingi natijaning umumiy foizi bilan taqqoslaydi va foizlardagi farqni (musbat, manfiy yoki nol) hisoblab qaytaradi.
4. IF foydalanuvchining faqat bitta test natijasi mavjud bo'lsa, THEN THE Analitika_Moduli SHALL o'sish dinamikasini shu bitta natijadan iborat ketma-ketlik sifatida qaytaradi va taqqoslash farqini "mavjud emas" deb belgilaydi.
5. WHEN analitika shakllantiriladi, THE Analitika_Moduli SHALL eng yuqori umumiy foizga ega kompetensiyani eng kuchli kompetensiya, eng past umumiy foizga ega kompetensiyani esa rivojlantirilishi lozim bo'lgan kompetensiya sifatida aniqlaydi.
6. IF bir nechta kompetensiya eng yuqori yoki eng past foiz qiymatida o'zaro teng bo'lsa, THEN THE Analitika_Moduli SHALL shu qiymatga teng bo'lgan barcha kompetensiyalarni mos toifa (eng kuchli yoki rivojlantirilishi lozim) ostida qaytaradi.
7. IF foydalanuvchining hech qanday test natijasi bo'lmasa, THEN THE Analitika_Moduli SHALL bo'sh natija holatini bildiruvchi javobni xato sifatida emas, balki muvaffaqiyatli bo'sh holat (umumiy ball, taqsimot va o'sish dinamikasi bo'sh) sifatida qaytaradi.

### Requirement 10: Individual rivojlanish tavsiyalari

**User Story:** Rahbar sifatida men natijalarim asosida individual rivojlanish
tavsiyalarini olmoqchiman, shunda zaif kompetensiyalarimni rivojlantira olaman.

#### Acceptance Criteria

1. WHEN test natijasi hisoblanadi, THE Tavsiya_Moduli SHALL har bir kompetensiya va uning darajasiga (Past, O'rta, Yaxshi yoki Yuqori) mos tavsiyani avtomatik tanlaydi va tanlangan tavsiyalarni shu natijaga bog'lab saqlaydi.
2. WHEN foydalanuvchi o'z tavsiyalarini so'raydi, THE Tavsiya_Moduli SHALL eng so'nggi yakunlangan natijaga bog'lab saqlangan rivojlanish tavsiyalarini har bir baholangan kompetensiya nomi, darajasi va rivojlanish ko'rsatmasi bilan qaytaradi.
3. WHEN foydalanuvchi o'ziga tegishli mavjud natija identifikatori bo'yicha tavsiya so'raganda, THE Tavsiya_Moduli SHALL shu natijaga bog'lab saqlangan tavsiyalarni qaytaradi.
4. IF kompetensiya va daraja kombinatsiyasi uchun mos tavsiya mavjud bo'lmasa, THEN THE Tavsiya_Moduli SHALL umumiy standart rivojlanish tavsiyasini tanlaydi va uni natijaga bog'lab saqlaydi.
5. IF foydalanuvchining hech qanday yakunlangan natijasi bo'lmasa, THEN THE Tavsiya_Moduli SHALL bo'sh holatni bildiruvchi javobni xato sifatida emas, balki muvaffaqiyatli bo'sh holat sifatida qaytaradi.
6. IF so'ralgan natija identifikatori mavjud bo'lmasa yoki so'rovchi foydalanuvchiga tegishli bo'lmasa, THEN THE Tavsiya_Moduli SHALL so'rovni rad etadi va natija topilmadi xatosini qaytaradi.

### Requirement 11: Portfolio boshqaruvi

**User Story:** Rahbar sifatida men sertifikatlar, kurslar va yutuqlarimni
yuklab portfolio sifatida saqlamoqchiman, shunda kasbiy faoliyatim hujjatlangan
bo'ladi.

#### Acceptance Criteria

1. WHEN foydalanuvchi o'z portfoliosini so'raydi, THE Portfolio_Moduli SHALL foydalanuvchining barcha portfolio yozuvlarini nomi, fayl havolasi, fayl turi va yaratilgan sanasi bilan, yaratilgan sanasi bo'yicha kamayish tartibida qaytaradi; agar yozuv bo'lmasa, bo'sh ro'yxatni qaytaradi.
2. WHEN foydalanuvchi PDF, JPG, PNG, DOC yoki DOCX formatidagi va hajmi 10 MB (10 485 760 bayt) dan oshmaydigan faylni 1–200 belgidan iborat nom bilan yuklaydi, THE Portfolio_Moduli SHALL faylni saqlaydi va portfolio yozuvini yaratadi.
3. IF yuklangan fayl turi ruxsat etilgan formatlar (PDF, JPG, PNG, DOC, DOCX) ro'yxatida bo'lmasa, THEN THE Portfolio_Moduli SHALL yuklashni rad etadi, faylni saqlamaydi va fayl turi qo'llab-quvvatlanmasligi haqida xato xabarini qaytaradi.
4. IF yuklangan fayl hajmi 10 MB (10 485 760 bayt) dan oshsa, THEN THE Portfolio_Moduli SHALL yuklashni rad etadi, faylni va yozuvni saqlamaydi va fayl hajmi cheklovi haqida xato xabarini qaytaradi.
5. WHEN foydalanuvchi o'z portfolio yozuvini o'chirishni so'raydi, THE Portfolio_Moduli SHALL yozuvni va unga bog'langan faylni o'chiradi.
6. IF foydalanuvchi boshqa foydalanuvchiga tegishli portfolio yozuvini o'chirishni so'rasa, THEN THE Portfolio_Moduli SHALL so'rovni rad etadi va ruxsat yo'q xatosini qaytaradi.
7. IF foydalanuvchi mavjud bo'lmagan portfolio yozuvini o'chirishni so'rasa, THEN THE Portfolio_Moduli SHALL so'rovni rad etadi va yozuv topilmadi xatosini qaytaradi.

### Requirement 12: Reyting

**User Story:** Rahbar sifatida men reytingni ko'rmoqchiman, shunda o'z
ko'rsatkichlarimni boshqa tashkilotlar va hududlar bilan taqqoslay olaman.

#### Acceptance Criteria

1. WHEN reyting so'ralganda, THE Reyting_Moduli SHALL umumiy reytingni, hudud bo'yicha, tashkilot bo'yicha va kompetensiya bo'yicha reytinglarni har bir yozuv uchun reyting o'rni (rank) va saralash ko'rsatkichi (umumiy foiz, 0–100%, 2 kasr xonasigacha) bilan qaytaradi.
2. WHEN reyting shakllantiriladi, THE Reyting_Moduli SHALL yozuvlarni saralash ko'rsatkichi (umumiy foiz) bo'yicha kamayish tartibida tartiblaydi.
3. IF bir nechta yozuv bir xil saralash ko'rsatkichiga ega bo'lsa, THEN THE Reyting_Moduli SHALL ularga bir xil reyting o'rnini beradi, keyingi o'rinni teng yozuvlar soniga mos ravishda o'tkazib yuboradi va teng yozuvlarni natijaga erishilgan sana bo'yicha o'sish tartibida joylashtiradi.
4. WHILE reyting taqdim etilmoqda, THE Reyting_Moduli SHALL har bir yozuv uchun faqat hudud, tashkilot turi, lavozim, saralash ko'rsatkichi va reyting o'rnini taqdim etadi hamda to'liq ism, telefon raqami va boshqa bevosita identifikatsiyalovchi shaxsiy ma'lumotlarni oshkor qilmaydi; so'rovchining o'z yozuvini esa ajratib ko'rsatadi.
5. IF foydalanuvchining kamida bitta yakunlangan test natijasi bo'lmasa, THEN THE Reyting_Moduli SHALL foydalanuvchini reytingdan tashqarida holatda belgilaydi va unga reyting o'rni bermaydi.

### Requirement 13: Ekspert baholash

**User Story:** Ekspert sifatida men biriktirilgan tashkilot rahbarini qo'shimcha
baholamoqchiman, shunda umumiy natijaga professional ekspert ko'rsatkichi
qo'shiladi.

#### Acceptance Criteria

1. WHILE ekspert biriktirilgan rahbarni baholamoqda, THE Ekspert_Moduli SHALL quyidagi har bir mezon bo'yicha 1 dan 5 gacha bo'lgan butun son shkalasida (1 — eng past, 5 — eng yuqori) baholashga ruxsat beradi: boshqaruv madaniyati, jamoaviy ishlash, pedagogik jarayonlarni tashkil etish, innovatsion yondashuv, hujjatlar bilan ishlash va strategik rejalashtirish.
2. WHEN ekspert barcha olti mezon bo'yicha baholashni topshiradi, THE Ekspert_Moduli SHALL ekspert bahosini olti mezon o'rtacha qiymati (1.00–5.00, 2 kasr xonasigacha yaxlitlangan) sifatida hisoblaydi va uni rahbarning umumiy natijasiga qo'shimcha ko'rsatkich sifatida qo'shadi.
3. IF ekspert biror mezonga 1–5 oralig'idan tashqari yoki butun son bo'lmagan qiymat kiritsa, THEN THE Ekspert_Moduli SHALL baholashni rad etadi, hech qanday ma'lumot saqlamaydi va validatsiya xatosini qaytaradi.
4. IF ekspert olti mezondan birortasini baholamasdan topshirishga urinsa, THEN THE Ekspert_Moduli SHALL baholashni rad etadi va to'ldirilmagan mezon mavjudligini bildiruvchi xato xabarini qaytaradi.
5. IF ekspert o'ziga biriktirilmagan tashkilot rahbarini baholashga urinsa, THEN THE Ekspert_Moduli SHALL so'rovni rad etadi va ruxsat yo'q xatosini qaytaradi.
6. WHEN ekspert bahosi qo'shilganda, THE Bildirishnoma_Xizmati SHALL tegishli rahbarga ekspert tavsiyasi kelgani haqida bildirishnoma yuboradi.

### Requirement 14: Administrator tomonidan kontent boshqaruvi

**User Story:** Administrator sifatida men testlar, savollar, kompetensiyalar va
boshqa kontentni boshqarmoqchiman, shunda diagnostika tizimi dolzarb bo'lib
turadi.

#### Acceptance Criteria

1. WHILE foydalanuvchi Administrator roli bilan kirgan, THE Admin_Moduli SHALL foydalanuvchilar, test toifalari, savollar, javob variantlari, baholash mezonlari, kompetensiyalar, tavsiyalar, hududlar, tashkilotlar va reyting sozlamalari ustida yaratish, ko'rish, yangilash va o'chirish (CRUD) amallarini bajarishga ruxsat beradi.
2. WHEN administrator yangi testni yaroqli majburiy maydonlar (nomi 1–200 belgi, toifasi yaroqli toifalardan biri — kognitiv, kompetensiya, reflexiv yoki situatsion diagnostika, davomiyligi 1–600 daqiqa oralig'idagi butun son) bilan yaratadi, THE Admin_Moduli SHALL testni saqlaydi va uni testlar ro'yxatida mavjud qiladi.
3. WHEN administrator savolni yaroqli majburiy maydonlar (savol matni 1–1000 belgi, kamida 2 ta javob varianti, savol balli 0.01–1000 oralig'idagi musbat son) bilan va mavjud kompetensiyaga bog'lab yaratadi yoki tahrirlaydi, THE Admin_Moduli SHALL savolni belgilangan ball va kompetensiya bog'lanishi bilan saqlaydi.
4. WHEN administrator testni o'chirishni yoki nofaol qilishni so'raydi, THE Admin_Moduli SHALL testni testlar ro'yxatidan olib tashlaydi yoki nofaol holatga o'tkazadi.
5. IF Administrator bo'lmagan foydalanuvchi admin amallariga murojaat qilsa, THEN THE Admin_Moduli SHALL so'rovni rad etadi va ruxsat yo'q xatosini qaytaradi.
6. IF administrator testni yoki savolni majburiy maydonlardan biri kiritilmagan, faqat bo'sh joy belgilaridan iborat yoki belgilangan oraliqdan tashqari (yaroqsiz) qiymat bilan yaratish yoki tahrirlashga urinsa, THEN THE Admin_Moduli SHALL amalni rad etadi, hech qanday ma'lumotni saqlamaydi yoki o'zgartirmaydi va qaysi maydon yaroqsizligini ko'rsatuvchi validatsiya xatosini qaytaradi.
7. IF administrator savolni mavjud bo'lmagan kompetensiyaga bog'lab yaratish yoki tahrirlashga urinsa, THEN THE Admin_Moduli SHALL amalni rad etadi, savolni saqlamaydi va kompetensiya topilmadi xatosini qaytaradi.
8. IF administrator bir yoki bir nechta savol tomonidan ishlatilayotgan (bog'langan) kompetensiyani o'chirishga urinsa, THEN THE Admin_Moduli SHALL o'chirishni rad etadi, kompetensiyani va uning bog'lanishlarini o'chirmaydi va bog'liqlik (referensial yaxlitlik) mavjudligini bildiruvchi xato xabarini qaytaradi.

### Requirement 15: Hisobotlar (Admin va Ekspert)

**User Story:** Administrator yoki ekspert sifatida men jamlangan hisobotlarni
ko'rmoqchiman, shunda umumiy holatni monitoring qila olaman.

#### Acceptance Criteria

1. WHEN administrator hisobotni so'raydi, THE Hisobot_Moduli SHALL rahbarlar soni, test topshirganlar soni, o'rtacha ball (barcha yakunlangan natijalarning umumiy foizlari arifmetik o'rtachasi, 0–100% oralig'ida va 2 kasr xonasigacha yaxlitlangan), eng past kompetensiyalar va eng yuqori kompetensiyalarni qaytaradi.
2. WHEN eng past va eng yuqori kompetensiyalar so'ralganda, THE Hisobot_Moduli SHALL har bir kompetensiya bo'yicha jamlangan foizni (shu kompetensiyaga oid barcha yakunlangan natijalar foizlarining o'rtachasi) hisoblaydi va eng past jamlangan foizli kompetensiya(lar)ni "eng past", eng yuqori jamlangan foizli kompetensiya(lar)ni "eng yuqori" sifatida qaytaradi; teng qiymatda bir nechta kompetensiya bo'lsa, ularning barchasini qaytaradi.
3. WHEN hudud bo'yicha hisobot so'ralganda, THE Hisobot_Moduli SHALL har bir hudud kesimida rahbarlar soni, test topshirganlar soni va o'rtacha ballni jamlab qaytaradi.
4. WHEN tashkilot bo'yicha hisobot so'ralganda, THE Hisobot_Moduli SHALL har bir tashkilot kesimida rahbarlar soni, test topshirganlar soni va o'rtacha ballni jamlab qaytaradi.
5. WHEN individual rivojlanish dinamikasi so'ralganda, THE Hisobot_Moduli SHALL tanlangan rahbarning natijalari o'zgarishini sana bilan belgilangan, xronologik (eng eskidan eng yangiga) tartibda qaytaradi.
6. WHILE ekspert hisobot so'ramoqda, THE Hisobot_Moduli SHALL faqat ekspertga biriktirilgan tashkilotlar ma'lumotlarini qamrab oladi.
7. IF so'ralgan hisobot doirasida hech qanday yakunlangan natija mavjud bo'lmasa, THEN THE Hisobot_Moduli SHALL nol qiymatli sanoqlar va bo'sh kompetensiya ro'yxatlari bilan muvaffaqiyatli bo'sh holatni qaytaradi va xato qaytarmaydi.

### Requirement 16: Push bildirishnomalar

**User Story:** Foydalanuvchi sifatida men muhim hodisalar haqida bildirishnoma
olmoqchiman, shunda yangiliklar va muddatlardan xabardor bo'laman.

#### Acceptance Criteria

1. WHEN yangi test qo'shiladi, THE Bildirishnoma_Xizmati SHALL push bildirishnomalarni yoqgan va ro'yxatdan o'tgan yaroqli qurilma tokeniga ega tegishli foydalanuvchilarga yangi test haqida push bildirishnoma yuboradi.
2. WHEN rahbarning qayta diagnostika qilish sanasi yetib kelganda, THE Bildirishnoma_Xizmati SHALL push bildirishnomalarni yoqgan va yaroqli qurilma tokeniga ega rahbarga qayta topshirish haqida push bildirishnoma yuboradi.
3. WHEN rivojlanish rejasi muddati tugashiga 3 kun qolganda, THE Bildirishnoma_Xizmati SHALL push bildirishnomalarni yoqgan va yaroqli qurilma tokeniga ega foydalanuvchiga muddat haqida push bildirishnoma yuboradi.
4. WHEN ekspert tavsiyasi kelganda, THE Bildirishnoma_Xizmati SHALL push bildirishnomalarni yoqgan va yaroqli qurilma tokeniga ega rahbarga ekspert tavsiyasi haqida push bildirishnoma yuboradi.
5. IF bildirishnoma yuborilishi kerak bo'lgan foydalanuvchi push bildirishnomalarni o'chirib qo'ygan bo'lsa, THEN THE Bildirishnoma_Xizmati SHALL shu foydalanuvchiga yuborishni o'tkazib yuboradi, buni xato deb hisoblamaydi va boshqa tegishli foydalanuvchilarga yuborishni davom ettiradi.
6. IF bildirishnoma yuborilishi kerak bo'lgan foydalanuvchining ro'yxatdan o'tgan yaroqli qurilma tokeni bo'lmasa, THEN THE Bildirishnoma_Xizmati SHALL shu foydalanuvchiga yuborishni o'tkazib yuboradi, buni xato deb hisoblamaydi va boshqa tegishli foydalanuvchilarga yuborishni davom ettiradi.

### Requirement 17: Xavfsizlik va maxfiylik

**User Story:** Tizim egasi sifatida men foydalanuvchi ma'lumotlari himoyalanishini
istayman, shunda maxfiy ma'lumotlar oshkor bo'lmaydi va tizim suiiste'moldan
himoyalanadi.

#### Acceptance Criteria

1. THE Autentifikatsiya_Moduli SHALL parollarni xeshlangan ko'rinishda saqlaydi.
2. THE REST_API SHALL himoyalangan resurslarga kirishni JWT tokenlar orqali autentifikatsiya qiladi.
3. IF bir manbadan belgilangan vaqt oralig'ida ruxsat etilgan so'rovlar sonidan ko'p so'rov kelsa, THEN THE REST_API SHALL ortiqcha so'rovlarni cheklaydi (rate limit) va 429 xatosini qaytaradi. Cheklov qarori faqat joriy vaqt oynasidagi so'rovlar soni asosida qabul qilinadi.
4. WHEN fayl yuklanganda, THE Portfolio_Moduli SHALL fayl turini ruxsat etilgan formatlar ro'yxatiga ko'ra tekshiradi.
5. THE Backend_Xizmati SHALL maxfiy ma'lumotlarni (parol, token, telefon raqami kabi) jurnal (log) yozuvlariga yozmaydi.
6. WHEN foydalanuvchi o'z natijalarini so'raydi, THE REST_API SHALL faqat shu foydalanuvchiga tegishli natijalarni qaytaradi.

### Requirement 18: MVP'dan keyingi kengaytirilishlar uchun tayyorlik (Out of scope)

**User Story:** Tizim egasi sifatida men MVP arxitekturasi kelajakdagi
imkoniyatlarga tayyor bo'lishini istayman, shunda keyingi bosqichlar qayta
qurishsiz qo'shiladi.

#### Acceptance Criteria

1. THE Backend_Xizmati SHALL 360 daraja teskari aloqa (o'z-o'zini baholash, xodimlar bahosi, ekspert bahosi, ota-onalar fikri, yuqori tashkilot bahosi) ma'lumotlarini saqlash uchun kengaytiriladigan ma'lumotlar modelini taqdim etadi.
2. THE Backend_Xizmati SHALL fayl saqlashni MVP bosqichida lokal server xotirasida, keyinchalik bulut (masalan, AWS S3) xotirasiga ko'chirish imkonini beruvchi abstraksiya orqali amalga oshiradi.
3. WHERE quyidagi imkoniyatlar belgilangan — 360 daraja teskari aloqa, sun'iy intellektga asoslangan avtomatik tavsiyalar, to'liq veb admin panel dizayni, ota-onalar fikri moduli, tashkilotlararo taqqoslama reyting, sertifikat generatsiyasi, QR-kod orqali natija tekshiruvi va iOS versiyasi — THE Tizim SHALL ularni MVP doirasidan tashqarida deb belgilaydi va MVP yetkazib berishida amalga oshirmaydi.

### Requirement 19: Platforma va offline qo'llab-quvvatlash

**User Story:** Rahbar sifatida men ilovani Android qurilmamda ishlata olmoqchiman
va internet bo'lmaganda ham ilgari yuklangan testlarni ko'ra olmoqchiman, shunda
ulanish uzilganda ham ishlashni davom ettiraman.

#### Acceptance Criteria

1. THE Mobil_Ilova SHALL Android 8.0 va undan yuqori versiyalarda o'rnatiladi va ishga tushadi.
2. THE Mobil_Ilova SHALL Material Design tamoyillariga muvofiq foydalanuvchi interfeysini taqdim etadi.
3. WHERE offline qo'llab-quvvatlash yoqilgan, WHILE qurilma internetga ulanmagan, THE Mobil_Ilova SHALL ilgari yuklangan testlarni ko'rsatadi va topshirilgan test natijasini vaqtincha saqlaydi.
4. WHERE offline qo'llab-quvvatlash yoqilgan, WHEN internet aloqasi tiklanadi, THE Mobil_Ilova SHALL vaqtincha saqlangan natijalarni Backend_Xizmatiga yuboradi.

### Requirement 20: REST API interfeysi va hujjatlari

**User Story:** Dasturchi sifatida men aniq belgilangan REST API va uning
hujjatlaridan foydalanmoqchiman, shunda mobil ilova va boshqa mijozlar backend
bilan ishonchli integratsiya qila oladi.

#### Acceptance Criteria

1. THE REST_API SHALL autentifikatsiya so'rovlarini quyidagi nuqtalar orqali taqdim etadi: POST /auth/register, POST /auth/login, POST /auth/refresh, POST /auth/logout va POST /auth/forgot-password.
2. THE REST_API SHALL foydalanuvchi profili so'rovlarini quyidagi nuqtalar orqali taqdim etadi: GET /users/me, PATCH /users/me va GET /users/{id}.
3. THE REST_API SHALL test so'rovlarini quyidagi nuqtalar orqali taqdim etadi: GET /tests, GET /tests/{id}, POST /tests/{id}/start, POST /tests/{id}/submit, GET /tests/results/me va GET /tests/results/{id}.
4. THE REST_API SHALL kontent va analitika so'rovlarini quyidagi nuqtalar orqali taqdim etadi: savollar (GET /questions, POST /questions, PATCH /questions/{id}, DELETE /questions/{id}), tavsiyalar (GET /recommendations/me, GET /recommendations/by-result/{result_id}), portfolio (GET /portfolio/me, POST /portfolio/upload, DELETE /portfolio/{id}), analitika (GET /analytics/me, GET /analytics/organization/{id}, GET /analytics/region/{id}) va admin (GET /admin/users, GET /admin/results, POST /admin/tests, PATCH /admin/tests/{id}, DELETE /admin/tests/{id}).
5. THE REST_API SHALL 1–4-mezonlarda sanab o'tilgan barcha nuqtalar uchun mashina o'qiy oladigan API hujjatlarini (masalan, OpenAPI) har bir nuqtaning HTTP usuli, yo'li, parametrlari hamda so'rov va javob sxemalari bilan taqdim etadi.
6. IF so'rov yaroqsiz yoki to'liqsiz ma'lumot (kiritilmagan majburiy maydon yoki yaroqsiz qiymat) bilan yuborilsa, THEN THE REST_API SHALL so'rovni rad etadi, hech qanday resurs holatini o'zgartirmaydi va yaroqsiz maydon hamda sababini ko'rsatuvchi tuzilgan xato javobini (400 toifasi) qaytaradi.
7. IF mavjud bo'lmagan nuqtaga yoki nuqta uchun qo'llab-quvvatlanmaydigan HTTP usuli bilan murojaat qilinsa, THEN THE REST_API SHALL so'rovni rad etadi va mos xato javobini (mos ravishda 404 yoki 405 toifasi) qaytaradi.
