# ================================================================
#  core/config.py  —  App Configuration & Location Data
#  Khattak Qomi Etehad Pakistan
# ================================================================

# ========================
# APP SETTINGS
# ========================
APP_NAME = "Khattak Qomi Etehad Pakistan"
APP_VERSION = "1.0.0"
LANGUAGES = ["English", "Urdu"]
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5

# ========================
# ROLES
# ========================
ROLES = {
    "MEMBER": "member",
    "DONOR": "donor",
    "ADMIN": "admin",
    "HEAD_ADMIN": "head_admin",
}

# ========================
# BLOOD GROUPS
# ========================
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

# ========================
# DONOR SETTINGS
# ========================
DONATION_GAP_DAYS = 90

# ========================
# URGENCY LEVELS
# ========================
URGENCY_LEVELS = {
    "LOW": "low",
    "MEDIUM": "medium",
    "HIGH": "high",
    "CRITICAL": "critical",
}

URGENCY_LABELS = {
    "low": "کم ضروری (3-7 دن)",
    "medium": "درمیانہ (1-2 دن)",
    "high": "ضروری (آج)",
    "critical": "ہنگامی (ابھی)",
}

# ========================
# REQUEST STATUS
# ========================
REQUEST_STATUS = {
    "PENDING": "pending",
    "MATCHING": "matching",
    "IN_PROGRESS": "in_progress",
    "FULFILLED": "fulfilled",
    "CANCELLED": "cancelled",
    "EXPIRED": "expired",
}

# ========================
# DONOR RESPONSE STATUS
# ========================
RESPONSE_STATUS = {
    "NOTIFIED": "notified",
    "ACCEPTED": "accepted",
    "DECLINED": "declined",
    "DONATED": "donated",
}

# ========================
# NOTIFICATION TYPES
# ========================
NOTIFICATION_TYPES = {
    "BLOOD_REQUEST": "blood_request",
    "DONOR_ACCEPTED": "donor_accepted",
    "DONATION_CONFIRMED": "donation_confirmed",
    "NEW_REQUEST_ADMIN": "new_request_admin",
    "ELIGIBILITY_RESTORED": "eligibility_restored",
    "REQUEST_EXPIRED": "request_expired",
    "GENERAL": "general",
}

# ================================================================
#  COUNTRY CODES WITH FLAGS & PHONE PREFIXES (TOP 25 COUNTRIES)
# ================================================================
COUNTRY_PHONE_CODES = [
    {"name": "Pakistan", "code": "+92", "flag": "🇵🇰", "display": "🇵🇰 +92"},
    {"name": "Saudi Arabia", "code": "+966", "flag": "🇸🇦", "display": "🇸🇦 +966"},
    {"name": "United Kingdom", "code": "+44", "flag": "🇬🇧", "display": "🇬🇧 +44"},
    {"name": "United Arab Emirates", "code": "+971", "flag": "🇦🇪", "display": "🇦🇪 +971"},
    {"name": "United States", "code": "+1", "flag": "🇺🇸", "display": "🇺🇸 +1"},
    {"name": "Kuwait", "code": "+965", "flag": "🇰🇼", "display": "🇰🇼 +965"},
    {"name": "Canada", "code": "+1", "flag": "🇨🇦", "display": "🇨🇦 +1"},
    {"name": "Oman", "code": "+968", "flag": "🇴🇲", "display": "🇴🇲 +968"},
    {"name": "Qatar", "code": "+974", "flag": "🇶🇦", "display": "🇶🇦 +974"},
    {"name": "Italy", "code": "+39", "flag": "🇮🇹", "display": "🇮🇹 +39"},
    {"name": "Malaysia", "code": "+60", "flag": "🇲🇾", "display": "🇲🇾 +60"},
    {"name": "Germany", "code": "+49", "flag": "🇩🇪", "display": "🇩🇪 +49"},
    {"name": "Australia", "code": "+61", "flag": "🇦🇺", "display": "🇦🇺 +61"},
    {"name": "Spain", "code": "+34", "flag": "🇪🇸", "display": "🇪🇸 +34"},
    {"name": "Bahrain", "code": "+973", "flag": "🇧🇭", "display": "🇧🇭 +973"},
    {"name": "France", "code": "+33", "flag": "🇫🇷", "display": "🇫🇷 +33"},
    {"name": "Afghanistan", "code": "+93", "flag": "🇦🇫", "display": "🇦🇫 +93"},
    {"name": "Norway", "code": "+47", "flag": "🇳🇴", "display": "🇳🇴 +47"},
    {"name": "Greece", "code": "+30", "flag": "🇬🇷", "display": "🇬🇷 +30"},
    {"name": "Portugal", "code": "+351", "flag": "🇵🇹", "display": "🇵🇹 +351"},
    {"name": "Denmark", "code": "+45", "flag": "🇩🇰", "display": "🇩🇰 +45"},
    {"name": "India", "code": "+91", "flag": "🇮🇳", "display": "🇮🇳 +91"},
    {"name": "Bangladesh", "code": "+880", "flag": "🇧🇩", "display": "🇧🇩 +880"},
    {"name": "Iran", "code": "+98", "flag": "🇮🇷", "display": "🇮🇷 +98"},
    {"name": "Turkey", "code": "+90", "flag": "🇹🇷", "display": "🇹🇷 +90"},
]

DEFAULT_COUNTRY_CODE = "+92"  # ڈیفالٹ کے طور پر پاکستان کا کوڈ سلیکٹ ہوگا

# ========================
# PAKISTAN LOCATION DATA
# ========================
#
# ── DATA SOURCE & ACCURACY NOTE ─────────────────────────────────
# District -> tehsil data below is compiled from Pakistan's provincial
# Boards/Departments of Revenue (Punjab, Sindh, Balochistan tehsil
# notifications) and Wikipedia's "List of tehsils of <province>" pages.
# It is accurate at the DISTRICT and TEHSIL level as of the sources
# checked (2023-2025), but Pakistan's admin map keeps changing —
# Punjab went from 36 to 41 districts in 2022-2024, Balochistan has
# been reorganized several times (32 -> 35 -> 42 districts across
# 2021-2026 reforms), and Lahore was reportedly split into North/South
# in Jan 2026. This file reflects the pre-2022/pre-split baseline
# structure (stable, well-documented) with newer splits still nested
# under their historical parent tehsil rather than promoted to their
# own district entry. Verify against the official portals below
# before relying on this for anything legally/administratively
# sensitive:
#   - Punjab:        https://www.punjab.gov.pk/districts
#   - Sindh:         https://sindh.gov.pk
#   - Balochistan:   https://balochistan.gov.pk
#   - KPK:           https://kp.gov.pk
#
# ── VILLAGES: INTENTIONALLY NOT INCLUDED ────────────────────────
# Pakistan has 50,000+ villages/mouzas. There is no way to hand-type
# or hand-verify that from search results without it turning into
# confident-sounding guesswork — a wrong village name here is worse
# than not having one, since it could misroute a blood request to
# the wrong area. If village-level location is genuinely needed:
#   1. Source an official dataset (Pakistan Bureau of Statistics
#      village/mouza codes from the census, or a maps/places API
#      like Google Places/OpenStreetMap Nominatim) rather than a
#      static Python dict — it's the only way to get this right AND
#      keep it maintainable.
#   2. Load it into a Supabase table (village, tehsil, district,
#      province columns) and give users a searchable autocomplete
#      field instead of a fourth cascading dropdown — a flat
#      dict-of-dicts-of-dicts-of-lists for 50k+ entries would also
#      bloat the app bundle and slow down every province/district/
#      tehsil dropdown rebuild in the registration flow.
#   3. Until then, "tehsil" remains the most granular level, which
#      is precise enough for donor/request geographic matching.

KPK_DISTRICTS = {
    "Peshawar": ["Peshawar City", "Chamkani", "Mathra", "Bara", "Hayatabad", "Badaber", "Sheikhabad", "Wazir Bagh"],
    "Nowshera": ["Nowshera", "Pabbi", "Jehangira", "Akora Khattak", "Mohib Banda"],
    "Mardan": ["Mardan City", "Takht Bhai", "Katlang", "Rustam"],
    "Charsadda": ["Charsadda", "Tangi", "Shabqadar", "Prang"],
    "Swabi": ["Swabi", "Topi", "Razzar", "Lahor", "Gadezai"],
    "Kohat": ["Kohat City", "Lachi", "Gumbat", "Darra Adam Khel"],
    "Karak": ["Karak", "Banda Daud Shah", "Takht-e-Nasrati", "Sabir Abad"],
    "Hangu": ["Hangu", "Thall", "Pewar"],
    "Abbottabad": ["Abbottabad City", "Havelian", "Nathiagali", "Sherwan"],
    "Mansehra": ["Mansehra City", "Balakot", "Oghi", "Darband", "Battal"],
    "Haripur": ["Haripur", "Ghazi", "Khalabat"],
    "Battagram": ["Battagram", "Allai", "Chahar Bagh"],
    "Swat": ["Mingora", "Saidu Sharif", "Matta", "Bahrain", "Khwazakhela", "Kabal", "Charbagh"],
    "Buner": ["Daggar", "Totalai", "Gagra", "Mandanr"],
    "Dir Lower": ["Timergara", "Balambat", "Munda", "Samarbagh"],
    "Dir Upper": ["Dir City", "Wari", "Sheringal", "Kumrat"],
    "Chitral": ["Chitral City", "Drosh", "Mastuj", "Booni"],
    "Malakand": ["Malakand", "Batkhela", "Dargai"],
    "Shangla": ["Alpuri", "Puran", "Chakesar"],
    "Lakki Marwat": ["Lakki Marwat", "Serai Naurang", "Ghazni Khel"],
    "Bannu": ["Bannu City", "Domel", "Kakki"],
    "Tank": ["Tank City", "Kulachi"],
    "Dera Ismail Khan": ["D.I. Khan City", "Paharpur", "Kulachi", "Darabar"],
    "Kurram": ["Parachinar", "Sadda", "Tall"],
    "North Waziristan": ["Miranshah", "Razmak", "Spinwam"],
    "South Waziristan": ["Wana", "Ladha", "Sarwakai"],
    "Bajaur": ["Khar", "Nawagai", "Mamund"],
    "Mohmand": ["Ghalanai", "Ekka Ghund", "Safi"],
    "Khyber": ["Landi Kotal", "Bara", "Jamrud"],
    "Orakzai": ["Kalaya", "Ghiljo", "Darra Adam Khel"],
}

# Punjab — 36-district historical baseline, 145 tehsils (Board of Revenue,
# Government of Punjab notifications + Wikipedia "List of tehsils of
# Punjab"). The 2022-2024 promotion of Wazirabad, Murree, Kot Addu,
# Talagang and Taunsa tehsils into their own districts is NOT reflected
# separately here — they're still listed under their historical parent
# district below. Update if your registration flow needs the new
# 41-district structure.
PUNJAB_CITIES = {
    "Lahore": ["Lahore City", "Lahore Cantt", "Model Town", "Raiwind", "Shalimar"],
    "Kasur": ["Kasur", "Chunian", "Kot Radha Kishan", "Pattoki"],
    "Sheikhupura": ["Sheikhupura", "Ferozewala", "Muridke", "Safdarabad", "Sharaqpur"],
    "Nankana Sahib": ["Nankana Sahib", "Sangla Hill", "Shahkot"],
    "Okara": ["Okara", "Depalpur", "Renala Khurd"],
    "Sahiwal": ["Sahiwal", "Chichawatni"],
    "Pakpattan": ["Pakpattan", "Arifwala"],
    "Faisalabad": ["Faisalabad City", "Faisalabad Saddar", "Chak Jhumra", "Jaranwala", "Samundri", "Tandlianwala"],
    "Jhang": ["Jhang", "18-Hazari", "Ahmadpur Sial", "Shorkot"],
    "Toba Tek Singh": ["Toba Tek Singh", "Gojra", "Kamalia", "Pir Mahal"],
    "Chiniot": ["Chiniot", "Bhawana", "Lalian"],
    "Gujranwala": ["Gujranwala City", "Gujranwala Saddar", "Kamoke", "Nowshera Virkan", "Wazirabad"],
    "Hafizabad": ["Hafizabad", "Pindi Bhattian"],
    "Gujrat": ["Gujrat", "Kharian", "Sarai Alamgir"],
    "Mandi Bahauddin": ["Mandi Bahauddin", "Malakwal", "Phalia"],
    "Sialkot": ["Sialkot", "Daska", "Pasrur", "Sambrial"],
    "Narowal": ["Narowal", "Shakargarh", "Zafarwal"],
    "Rawalpindi": ["Rawalpindi", "Gujar Khan", "Kahuta", "Kallar Sayyedan", "Kotli Sattian", "Murree", "Taxila"],
    "Attock": ["Attock", "Fateh Jang", "Hassan Abdal", "Hazro", "Jand", "Pindi Gheb"],
    "Jhelum": ["Jhelum", "Dina", "Pind Dadan Khan", "Sohawa"],
    "Chakwal": ["Chakwal", "Choa Saidan Shah", "Kallar Kahar", "Lawa", "Talagang"],
    "Sargodha": ["Sargodha", "Bhalwal", "Bhera", "Kot Momin", "Sahiwal (Sargodha)", "Shahpur", "Sillanwali"],
    "Bhakkar": ["Bhakkar", "Darya Khan", "Kalur Kot", "Mankera"],
    "Khushab": ["Khushab", "Naushera", "Noorpur Thal", "Quaidabad"],
    "Multan": ["Multan City", "Multan Saddar", "Jalalpur Pirwala", "Shujabad"],
    "Khanewal": ["Khanewal", "Jahanian", "Kabirwala", "Mian Channu"],
    "Lodhran": ["Lodhran", "Dunyapur", "Kahror Pacca"],
    "Vehari": ["Vehari", "Burewala", "Mailsi"],
    "Dera Ghazi Khan": ["Dera Ghazi Khan", "Taunsa", "Kot Chutta"],
    "Rajanpur": ["Rajanpur", "Jampur", "Rojhan"],
    "Layyah": ["Layyah", "Chaubara", "Karor Lal Esan"],
    "Muzaffargarh": ["Muzaffargarh", "Alipur", "Jatoi", "Kot Addu"],
    "Bahawalpur": ["Bahawalpur City", "Bahawalpur Saddar", "Ahmadpur East", "Hasilpur", "Khairpur Tamewali", "Yazman"],
    "Bahawalnagar": ["Bahawalnagar", "Chishtian", "Fort Abbas", "Haroonabad", "Minchinabad"],
    "Rahim Yar Khan": ["Rahim Yar Khan", "Khanpur", "Liaquatpur", "Sadiqabad"],
}

# Sindh — 30 districts / ~138 tehsils (locally called "talukas"). Source:
# Sindh government tehsil notifications + Wikipedia "List of tehsils of
# Sindh". Karachi's 7 districts are listed individually below (as they
# are administratively) with their sub-divisions/towns as "tehsils".
SINDH_CITIES = {
    "Karachi Central": ["Gulberg", "Liaquatabad", "Nazimabad", "New Karachi", "North Nazimabad"],
    "Karachi East": ["Ferozabad", "Gulshan-e-Iqbal", "Gulzar-e-Hijri", "Jamshed Quarters"],
    "Karachi South": ["Aram Bagh", "Civil Lines", "Garden", "Lyari", "Saddar"],
    "Karachi West": ["Baldia", "Harbour", "Manghopir", "Mominabad", "Orangi", "SITE"],
    "Malir": ["Airport", "Bin Qasim", "Gadap", "Ibrahim Hyderi", "Murad Memon", "Shah Murad"],
    "Korangi": ["Korangi", "Landhi", "Model Colony", "Shah Faisal"],
    "Keamari": ["Keamari"],
    "Hyderabad": ["Hyderabad City", "Latifabad", "Qasimabad"],
    "Tando Muhammad Khan": ["Tando Muhammad Khan", "Bulri Shah Karim", "Mirpur Bathoro"],
    "Tando Allahyar": ["Tando Allahyar", "Chamber", "Jhando Mari"],
    "Matiari": ["Matiari", "Hala", "Saeedabad"],
    "Badin": ["Badin", "Matli", "Golarchi", "Talhar", "Tando Bago"],
    "Sujawal": ["Sujawal", "Jati", "Kharo Chan", "Mirpur Bathoro", "Shah Bunder"],
    "Thatta": ["Thatta", "Ghorabari", "Mirpur Sakro", "Keti Bunder"],
    "Jamshoro": ["Kotri", "Sehwan", "Manjhand", "Thano Bula Khan"],
    "Dadu": ["Dadu", "Johi", "Khairpur Nathan Shah", "Mehar"],
    "Larkana": ["Larkana", "Bakrani", "Dokri", "Ratodero"],
    "Qambar Shahdadkot": ["Qambar", "Shahdadkot", "Miro Khan", "Nasirabad", "Sijawal Junejo", "Warah"],
    "Shikarpur": ["Shikarpur", "Garhi Yasin", "Khanpur", "Lakhi"],
    "Jacobabad": ["Jacobabad", "Garhi Khairo", "Thul"],
    "Kashmore": ["Kandhkot", "Kashmore", "Tangwani"],
    "Sukkur": ["Sukkur", "New Sukkur", "Pano Aqil", "Rohri", "Salehpat"],
    "Ghotki": ["Ghotki", "Daharki", "Khangarh (Khanpur)", "Mirpur Mathelo", "Ubauro"],
    "Khairpur": ["Khairpur", "Faiz Ganj", "Gambat", "Kingri", "Kot Diji", "Sobho Dero", "Thari Mirwah"],
    "Naushahro Feroze": ["Naushahro Feroze", "Bhiria", "Kandiaro", "Mehrabpur", "Moro"],
    "Shaheed Benazirabad": ["Nawabshah", "Daur", "Sakrand", "Qazi Ahmed"],
    "Sanghar": ["Sanghar", "Jam Nawaz Ali", "Khipro", "Shahdadpur", "Sinjhoro", "Tando Adam"],
    "Mirpur Khas": ["Mirpur Khas", "Digri", "Jhuddo", "Kot Ghulam Muhammad", "Sindhri"],
    "Umerkot": ["Umerkot", "Kunri", "Pithoro", "Samaro"],
    "Tharparkar": ["Mithi", "Chachro", "Diplo", "Islamkot", "Nagarparkar", "Dahli"],
}

# Balochistan — reflects the ~32-35 district baseline used consistently
# across 2023-2025 sources (Board of Revenue tehsil lists + Wikipedia).
# Balochistan has been reorganized several times in quick succession
# (most recently a May 2026 reform reported bringing the total toward
# 42 districts, splitting Quetta into East/West, creating Taftan and
# Wadh districts, etc.) — those newest splits are NOT reflected here.
# Verify against balochistan.gov.pk if you need the current-year figure.
BALOCHISTAN_CITIES = {
    "Quetta": ["Quetta City", "Quetta Saddar", "Panjpai"],
    "Pishin": ["Pishin", "Barshore", "Hurramzai", "Karezat", "Saranan"],
    "Killa Abdullah": ["Killa Abdullah", "Dobandi", "Gulistan"],
    "Chaman": ["Chaman", "Chaman Saddar"],
    "Chagai": ["Dalbandin", "Nokundi"],
    "Nushki": ["Nushki", "Dak"],
    "Ziarat": ["Ziarat", "Sinjawi"],
    "Loralai": ["Loralai", "Mekhtar"],
    "Duki": ["Duki"],
    "Musakhel": ["Musakhel", "Kingri"],
    "Barkhan": ["Barkhan", "Rakhni"],
    "Zhob": ["Zhob", "Kapip"],
    "Sherani": ["Sherani"],
    "Qilla Saifullah": ["Qilla Saifullah", "Muslim Bagh"],
    "Sibi": ["Sibi", "Kutmandai", "Sangan"],
    "Lehri": ["Lehri", "Bhag"],
    "Harnai": ["Harnai", "Khost", "Sharigh"],
    "Kohlu": ["Kohlu", "Grisini", "Kahan", "Mawand", "Tambu"],
    "Dera Bugti": ["Dera Bugti", "Baiker", "Loti", "Phelawagh", "Sui"],
    "Nasirabad": ["Dera Murad Jamali", "Baba Kot", "Chattar"],
    "Jaffarabad": ["Usta Muhammad", "Gandakha", "Jhat Pat"],
    "Bolan": ["Dhadar", "Balanari", "Khattan", "Mach", "Sanni"],
    "Jhal Magsi": ["Gandawa", "Jhal Magsi", "Mirpur"],
    "Sohbatpur": ["Sohbatpur", "Faridabad"],
    "Kalat": ["Kalat", "Gazg", "Johan", "Mangochar"],
    "Surab": ["Surab"],
    "Mastung": ["Mastung", "Dasht", "Kirdgap"],
    "Khuzdar": ["Khuzdar", "Karkh", "Moola", "Nal", "Ornach", "Wadh", "Zehri"],
    "Awaran": ["Awaran", "Gishkore", "Jhal Jao", "Korak", "Mashkai"],
    "Kharan": ["Kharan", "Sar-Kharan", "Tohumulk"],
    "Washuk": ["Washuk", "Besima", "Mashkhel", "Nag"],
    "Lasbela": ["Uthal", "Bela", "Dureji", "Gaddani", "Hub", "Liari", "Sonmiani/Winder"],
    "Kech": ["Turbat", "Balnigor", "Buleda", "Dasht", "Mand", "Tump"],
    "Gwadar": ["Gwadar", "Jiwani", "Ormara", "Pasni"],
    "Panjgur": ["Panjgur", "Gichk", "Paroom"],
}

AJK_CITIES = [
    "Muzaffarabad", "Mirpur", "Rawalakot", "Kotli", "Bagh",
    "Haveli", "Neelum", "Poonch", "Sudhnoti", "Hattian Bala"
]

GB_CITIES = [
    "Gilgit", "Skardu", "Hunza", "Ghanche", "Astore",
    "Diamer", "Ghizer", "Nagar", "Shigar", "Kharmang"
]

ICT_AREAS = ["Islamabad", "Rawalpindi"]

PAKISTAN_LOCATIONS = {
    "KPK": KPK_DISTRICTS,
    "Punjab": PUNJAB_CITIES,
    "Sindh": SINDH_CITIES,
    "Balochistan": BALOCHISTAN_CITIES,
    "Azad Kashmir": AJK_CITIES,
    "Gilgit Baltistan": GB_CITIES,
    "Islamabad": ICT_AREAS,
}

PROVINCES = list(PAKISTAN_LOCATIONS.keys())

# ================================================================
#  GLOBAL LOCATION DATA (TOP 25 COUNTRIES FOR OVERSEAS PAKISTANIS)
# ================================================================

GLOBAL_COUNTRIES_DATA = {
    "Pakistan": PAKISTAN_LOCATIONS,
    "Saudi Arabia": {
        "Riyadh": ["Riyadh City", "Al-Kharj", "Al-Majma'ah"],
        "Makkah / Jeddah": ["Jeddah", "Makkah City", "Taif", "Rabigh"],
        "Madinah": ["Madinah City", "Yanbu", "Badr"],
        "Eastern Province": ["Dammam", "Khobar", "Jubail", "Hafuf", "Qatif"],
        "Asir / Southern": ["Abha", "Khamis Mushait", "Jazan", "Najran"],
    },
    "United Kingdom": {
        "England": ["London", "Birmingham", "Manchester", "Bradford", "Leeds", "Luton", "Slough", "Coventry"],
        "Scotland": ["Glasgow", "Edinburgh", "Dundee", "Aberdeen"],
        "Wales": ["Cardiff", "Swansea", "Newport"],
        "Northern Ireland": ["Belfast", "Derry"],
    },
    "United Arab Emirates": {
        "Dubai": ["Dubai City", "Jebel Ali", "Hatta"],
        "Abu Dhabi": ["Abu Dhabi City", "Al Ain", "Ruwais"],
        "Sharjah": ["Sharjah City", "Khor Fakkan", "Kalba"],
        "Ajman": ["Ajman City"],
        "Ras Al Khaimah": ["Ras Al Khaimah City"],
        "Fujairah": ["Fujairah City"],
        "Umm Al Quwain": ["Umm Al Quwain City"],
    },
    "United States": {
        "New York": ["New York City", "Brooklyn", "Queens", "Long Island"],
        "Texas": ["Houston", "Dallas", "Austin", "Fort Worth"],
        "California": ["Los Angeles", "San Francisco", "San Jose", "Sacramento"],
        "Illinois": ["Chicago", "Naperville", "Schaumburg"],
        "Virginia / Maryland": ["Arlington", "Baltimore", "Silver Spring"],
        "Florida": ["Miami", "Orlando", "Tampa"],
    },
    "Kuwait": {
        "Al Asimah": ["Kuwait City", "Dasman", "Sharq"],
        "Hawalli": ["Hawalli City", "Salmiya", "Salwa"],
        "Farwaniya": ["Farwaniya City", "Khaitan", "Jleeb Al-Shuyoukh"],
        "Ahmadi": ["Fahaheel", "Ahmadi City", "Mangaf"],
    },
    "Canada": {
        "Ontario": ["Toronto", "Mississauga", "Brampton", "Ottawa", "Hamilton"],
        "Alberta": ["Calgary", "Edmonton"],
        "British Columbia": ["Vancouver", "Surrey", "Burnaby"],
        "Quebec": ["Montreal", "Laval"],
    },
    "Oman": {
        "Muscat": ["Muscat City", "Seeb", "Muttrah", "Bawshar"],
        "Dhofar": ["Salalah"],
        "Al Batinah": ["Sohar", "Barka", "Rustaq"],
        "Ad Dakhiliyah": ["Nizwa"],
    },
    "Qatar": {
        "Doha": ["Doha City", "The Pearl", "Industrial Area"],
        "Al Rayyan": ["Al Rayyan City", "Muaither"],
        "Al Khor": ["Al Khor City"],
        "Al Wakrah": ["Al Wakrah City"],
    },
    "Italy": {
        "Lombardy": ["Milan", "Brescia", "Bergamo"],
        "Lazio": ["Rome", "Latina"],
        "Emilia-Romagna": ["Bologna", "Carpi", "Reggio Emilia"],
        "Veneto": ["Venice", "Verona", "Padua"],
    },
    "Malaysia": {
        "Kuala Lumpur": ["KL City Centre", "Cheras", "Bukit Bintang"],
        "Selangor": ["Shah Alam", "Petaling Jaya", "Subang Jaya", "Klang"],
        "Penang": ["George Town", "Butterworth"],
        "Johor": ["Johor Bahru"],
    },
    "Germany": {
        "Frankfurt / Hesse": ["Frankfurt", "Wiesbaden", "Kassel"],
        "North Rhine-Westphalia": ["Cologne", "Düsseldorf", "Bonn", "Dortmund"],
        "Bavaria": ["Munich", "Nuremberg", "Augsburg"],
        "Berlin": ["Berlin City"],
        "Hamburg": ["Hamburg City"],
    },
    "Australia": {
        "New South Wales": ["Sydney", "Parramatta", "Liverpool"],
        "Victoria": ["Melbourne", "Geelong"],
        "Queensland": ["Brisbane", "Gold Coast"],
        "Western Australia": ["Perth"],
    },
    "Spain": {
        "Catalonia": ["Barcelona", "Badalona", "L'Hospitalet"],
        "Madrid": ["Madrid City", "Alcalá de Henares"],
        "Valencia": ["Valencia City", "Alicante"],
    },
    "Bahrain": {
        "Capital Governorate": ["Manama", "Juffair"],
        "Muharraq": ["Muharraq City", "Hidd"],
        "Central / Southern": ["Riffa", "Isa Town", "Hamad Town"],
    },
    "France": {
        "Île-de-France": ["Paris", "Saint-Denis", "Creil", "Sarcelles"],
        "Auvergne-Rhône-Alpes": ["Lyon", "Grenoble"],
        "Provence-Alpes-Côte d'Azur": ["Marseille", "Nice"],
    },
    "Afghanistan": {
        "Kabul": ["Kabul City", "Paghman"],
        "Nangarhar": ["Jalalabad", "Torkham"],
        "Kandahar": ["Kandahar City", "Spin Boldak"],
        "Herat": ["Herat City"],
    },
    "Norway": {
        "Oslo": ["Oslo City", "Sentrum"],
        "Akershus": ["Asker", "Bærum", "Lillestrøm"],
        "Rogaland": ["Stavanger", "Sandnes"],
    },
    "Greece": {
        "Attica": ["Athens", "Piraeus", "Peristeri"],
        "Central Macedonia": ["Thessaloniki"],
    },
    "Portugal": {
        "Lisbon": ["Lisbon City", "Amadora", "Cascais"],
        "Porto": ["Porto City", "Vila Nova de Gaia"],
        "Algarve": ["Faro", "Albufeira"],
    },
    "Denmark": {
        "Hovedstaden": ["Copenhagen", "Frederiksberg", "Gladsaxe"],
        "Midtjylland": ["Aarhus"],
    },
    "India": {
        "Punjab": ["Amritsar", "Ludhiana", "Jalandhar"],
        "Delhi": ["New Delhi", "Noida", "Gurugram"],
        "Maharashtra": ["Mumbai", "Pune"],
    },
    "Bangladesh": {
        "Dhaka": ["Dhaka City", "Gazipur"],
        "Chittagong": ["Chittagong City", "Cox's Bazar"],
    },
    "Iran": {
        "Tehran": ["Tehran City"],
        "Sistan and Baluchestan": ["Zahedan", "Iranshahr"],
        "Khorasan Razavi": ["Mashhad"],
    },
    "Turkey": {
        "Istanbul": ["Fatih", "Esenyurt", "Kadikoy"],
        "Ankara": ["Cankaya", "Kecioren"],
        "Izmir": ["Konak"],
    },
}

# Master routing compatibility
COUNTRIES_DATA = GLOBAL_COUNTRIES_DATA
COUNTRIES = list(COUNTRIES_DATA.keys())
COUNTRY_LIST = COUNTRIES
PROVINCE_LIST = PROVINCES


# ========================
# HELPER FUNCTIONS
# ========================

def get_provinces(country: str):
    """Country ke provinces/states/regions return karo"""
    data = COUNTRIES_DATA.get(country, {})
    if isinstance(data, dict):
        return list(data.keys())
    return []


def get_districts(country: str, province: str):
    """Province ke districts/cities return karo"""
    country_data = COUNTRIES_DATA.get(country, {})
    if not isinstance(country_data, dict):
        return []
    
    province_data = country_data.get(province, [])
    
    # Aggregated pattern validation for both nested and flat layouts
    if isinstance(province_data, dict):
        return list(province_data.keys())
    if isinstance(province_data, list):
        return province_data
    
    return []


def get_tehsils(country: str, province: str, district: str):
    """Pakistan KPK یا دیگر خلیجی ممالک کے ذیلی علاقوں (Sub-areas/Tehsils) کے لیے"""
    country_data = COUNTRIES_DATA.get(country, {})
    province_data = country_data.get(province, {})
    
    if isinstance(province_data, dict):
        return province_data.get(district, [])
    return []


def get_all_kpk_tehsils():
    """Sare KPK tehsils flat list mein"""
    tehsils = []
    kpk_data = PAKISTAN_LOCATIONS.get("KPK", {})
    if isinstance(kpk_data, dict):
        for district, t_list in kpk_data.items():
            tehsils.extend(t_list)
    return tehsils


def match_location(member_country: str, member_province: str, member_city: str,
                   admin_country: str, admin_province: str, admin_city: str) -> bool:
    return (member_country == admin_country and 
            member_province == admin_province and 
            member_city == admin_city)


def get_nearby_donors_filter(country: str, province: str, city: str, tehsil: str = None):
    filters = []

    if tehsil:
        filters.append({
            "priority": 1,
            "label": "Same Area/Tehsil",
            "country": country,
            "province": province,
            "city": city,
            "tehsil": tehsil,
        })

    filters.append({
        "priority": 2,
        "label": "Same City/District",
        "country": country,
        "province": province,
        "city": city,
        "tehsil": None,
    })

    filters.append({
        "priority": 3,
        "label": "Same Province/State",
        "country": country,
        "province": province,
        "city": None,
        "tehsil": None,
    })

    return filters


