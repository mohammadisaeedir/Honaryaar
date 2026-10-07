"""Public catalogue.

The lists below are the first records loaded into the database.
Pages read Profile, Project, and Opportunity from there.
"""

from datetime import date

ROLES = [
    {"slug": "actor", "title": "بازیگر"},
    {"slug": "director", "title": "کارگردان"},
    {"slug": "producer", "title": "تهیه‌کننده"},
    {"slug": "assistant-director", "title": "دستیار کارگردان"},
    {"slug": "playwright", "title": "نمایشنامه‌نویس"},
    {"slug": "set-designer", "title": "طراح صحنه"},
    {"slug": "costume-designer", "title": "طراح لباس"},
    {"slug": "composer", "title": "آهنگساز"},
    {"slug": "publicist", "title": "مدیر روابط عمومی"},
    {"slug": "investor", "title": "سرمایه‌گذار"},
    {"slug": "venue-manager", "title": "مدیر سالن"},
    {"slug": "rehearsal-manager", "title": "مدیر پلاتو"},
    {"slug": "student", "title": "هنرجو"},
    {"slug": "teacher", "title": "آموزگار"},
    {"slug": "performer", "title": "پرفورمر"},
]

# Migration 0002 still reads this list. Live arts are Art on ArtCategory.art.
ART_CATEGORIES = [
    {"slug": "theatre", "title": "تئاتر", "active": True},
    {"slug": "music", "title": "موسیقی", "active": False},
    {"slug": "film", "title": "سینما", "active": False},
    {"slug": "painting", "title": "نقاشی", "active": False},
]

CITIES = [
    {"slug": "tehran", "title": "تهران", "province": "tehran", "priority": 1, "featured": True},
    {"slug": "karaj", "title": "کرج", "province": "alborz", "priority": 2, "featured": True},
    {"slug": "mashhad", "title": "مشهد", "province": "razavi-khorasan", "priority": 3, "featured": True},
    {"slug": "isfahan", "title": "اصفهان", "province": "isfahan", "priority": 4, "featured": True},
    {"slug": "shiraz", "title": "شیراز", "province": "fars", "priority": 5, "featured": True},
    {"slug": "tabriz", "title": "تبریز", "province": "east-azerbaijan", "priority": 6, "featured": True},
    {"slug": "ahvaz", "title": "اهواز", "province": "khuzestan", "priority": 7, "featured": True},
    {"slug": "qom", "title": "قم", "province": "qom", "priority": 8, "featured": False},
    {"slug": "kermanshah", "title": "کرمانشاه", "province": "kermanshah", "priority": 9, "featured": False},
    {"slug": "rasht", "title": "رشت", "province": "gilan", "priority": 10, "featured": True},
    {"slug": "kerman", "title": "کرمان", "province": "kerman", "priority": 11, "featured": False},
    {"slug": "urmia", "title": "ارومیه", "province": "west-azerbaijan", "priority": 12, "featured": False},
    {"slug": "zahedan", "title": "زاهدان", "province": "sistan-baluchestan", "priority": 13, "featured": False},
    {"slug": "hamadan", "title": "همدان", "province": "hamadan", "priority": 14, "featured": False},
    {"slug": "yazd", "title": "یزد", "province": "yazd", "priority": 15, "featured": True},
    {"slug": "arak", "title": "اراک", "province": "markazi", "priority": 16, "featured": False},
    {"slug": "ardabil", "title": "اردبیل", "province": "ardabil", "priority": 17, "featured": False},
    {"slug": "bandar-abbas", "title": "بندرعباس", "province": "hormozgan", "priority": 18, "featured": False},
    {"slug": "zanjan", "title": "زنجان", "province": "zanjan", "priority": 19, "featured": False},
    {"slug": "sanandaj", "title": "سنندج", "province": "kurdistan", "priority": 20, "featured": False},
    {"slug": "qazvin", "title": "قزوین", "province": "qazvin", "priority": 21, "featured": False},
    {"slug": "khorramabad", "title": "خرم‌آباد", "province": "lorestan", "priority": 22, "featured": False},
    {"slug": "gorgan", "title": "گرگان", "province": "golestan", "priority": 23, "featured": False},
    {"slug": "sari", "title": "ساری", "province": "mazandaran", "priority": 24, "featured": False},
    {"slug": "bushehr", "title": "بوشهر", "province": "bushehr", "priority": 25, "featured": False},
    {"slug": "birjand", "title": "بیرجند", "province": "south-khorasan", "priority": 26, "featured": False},
    {"slug": "shahrekord", "title": "شهرکرد", "province": "chaharmahal-bakhtiari", "priority": 27, "featured": False},
    {"slug": "yasuj", "title": "یاسوج", "province": "kohgiluyeh-boyer-ahmad", "priority": 28, "featured": False},
    {"slug": "semnan", "title": "سمنان", "province": "semnan", "priority": 29, "featured": False},
    {"slug": "ilam", "title": "ایلام", "province": "ilam", "priority": 30, "featured": False},
    {"slug": "bojnord", "title": "بجنورد", "province": "north-khorasan", "priority": 31, "featured": False},
    {"slug": "kashan", "title": "کاشان", "province": "isfahan", "priority": 32, "featured": False},
    {"slug": "abadan", "title": "آبادان", "province": "khuzestan", "priority": 33, "featured": False},
    {"slug": "neyshabur", "title": "نیشابور", "province": "razavi-khorasan", "priority": 34, "featured": False},
]
GENDER_FA = {
    "male": "مرد",
    "female": "زن",
    "any": "بدون تفاوت",
}
# Migration 0008 still reads this list. New skills use SkillArea on Skill.group.
SKILL_GROUPS = [
    {"slug": "acting", "title": "بازیگری", "priority": 1},
    {"slug": "technique", "title": "تکنیک بازیگری", "priority": 2},
    {"slug": "singing", "title": "آواز", "priority": 3},
    {"slug": "dance", "title": "رقص", "priority": 4},
    {"slug": "comedy", "title": "کمدی", "priority": 5},
    {"slug": "sports", "title": "ورزش", "priority": 6},
    {"slug": "language", "title": "زبان و گویش", "priority": 7},
    {"slug": "production", "title": "تولید", "priority": 8},
    {"slug": "general", "title": "مهارت‌های عمومی", "priority": 9},
]
SKILLS = [
    {"slug": "camera-acting", "group": "acting", "title": "دوربین"},
    {"slug": "stage-acting", "group": "acting", "title": "صحنه"},
    {"slug": "youth-acting", "group": "acting", "title": "نوجوان"},
    {"slug": "musical-acting", "group": "acting", "title": "موزیکال"},
    {"slug": "body", "group": "technique", "title": "بدن"},
    {"slug": "improv", "group": "technique", "title": "بداهه"},
    {"slug": "movement", "group": "technique", "title": "حرکت"},
    {"slug": "stage-combat", "group": "technique", "title": "مبارزهٔ صحنه‌ای"},
    {"slug": "kids", "group": "technique", "title": "کودک و نوجوان"},
    {"slug": "contemporary-text", "group": "technique", "title": "متن معاصر"},
    {"slug": "voice", "group": "singing", "title": "آواز"},
    {"slug": "pop-singing", "group": "singing", "title": "پاپ"},
    {"slug": "traditional-singing", "group": "singing", "title": "سنتی"},
    {"slug": "sight-singing", "group": "singing", "title": "سلفژ"},
    {"slug": "musical-singing", "group": "singing", "title": "موزیکال"},
    {"slug": "contemporary-dance", "group": "dance", "title": "معاصر"},
    {"slug": "folk-dance", "group": "dance", "title": "محلی"},
    {"slug": "hiphop", "group": "dance", "title": "هیپ‌هاپ"},
    {"slug": "ballet", "group": "dance", "title": "باله"},
    {"slug": "sketch", "group": "comedy", "title": "اسکچ"},
    {"slug": "standup", "group": "comedy", "title": "استندآپ"},
    {"slug": "fitness", "group": "sports", "title": "ورزش"},
    {"slug": "swimming", "group": "sports", "title": "شنا"},
    {"slug": "football", "group": "sports", "title": "فوتبال"},
    {"slug": "gymnastics", "group": "sports", "title": "ژیمناستیک"},
    {"slug": "horse-riding", "group": "sports", "title": "اسب‌سواری"},
    {"slug": "cycling", "group": "sports", "title": "دوچرخه‌سواری"},
    {"slug": "tehran-accent", "group": "language", "title": "لهجهٔ تهرانی"},
    {"slug": "karaj-accent", "group": "language", "title": "گویش کرجی"},
    {"slug": "isfahan-accent", "group": "language", "title": "لهجهٔ اصفهانی"},
    {"slug": "shiraz-accent", "group": "language", "title": "لهجهٔ شیرازی"},
    {"slug": "mashhad-accent", "group": "language", "title": "لهجهٔ مشهدی"},
    {"slug": "azari", "group": "language", "title": "ترکی آذری"},
    {"slug": "english", "group": "language", "title": "انگلیسی مکالمه"},
    {"slug": "directing", "group": "production", "title": "کارگردانی"},
    {"slug": "casting", "group": "production", "title": "انتخاب بازیگر"},
    {"slug": "teaching", "group": "production", "title": "تدریس"},
    {"slug": "makeup", "group": "production", "title": "گریم"},
    {"slug": "driving", "group": "general", "title": "رانندگی"},
    {"slug": "motorcycle", "group": "general", "title": "موتورسواری"},
]
LEGACY_SKILL_TITLES = {
    "بازیگری دوربین": "camera-acting",
    "بدن": "body",
    "لهجهٔ تهرانی": "tehran-accent",
    "بازیگری صحنه": "stage-acting",
    "آواز": "voice",
    "تدریس": "teaching",
    "بداهه": "improv",
    "انگلیسی مکالمه": "english",
    "مبارزهٔ صحنه‌ای": "stage-combat",
    "موتورسواری": "motorcycle",
    "حرکت": "movement",
    "کودک و نوجوان": "kids",
    "گویش کرجی": "karaj-accent",
    "رانندگی": "driving",
    "کارگردانی": "directing",
    "انتخاب بازیگر": "casting",
    "متن معاصر": "contemporary-text",
    "بازیگری نوجوان": "youth-acting",
    "ورزش": "fitness",
}
SAMPLE_SKILL_LEVELS = {
    "sara-mohammadi": {"بازیگری دوربین": 3, "بدن": 2, "لهجهٔ تهرانی": 2},
    "kian-rezaei": {"بازیگری صحنه": 3, "آواز": 2},
    "niloufar-ahmadi": {"تدریس": 3, "بداهه": 2, "انگلیسی مکالمه": 2},
    "armin-kazemi": {"مبارزهٔ صحنه‌ای": 3, "موتورسواری": 1},
    "hasti-moradi": {"حرکت": 2, "کودک و نوجوان": 2},
    "pouria-nemati": {"گویش کرجی": 3, "رانندگی": 2},
    "maryam-soleimani": {"کارگردانی": 3, "انتخاب بازیگر": 2, "متن معاصر": 2},
    "reza-ghasemi": {"بازیگری نوجوان": 2, "ورزش": 1},
}
PRODUCTIONS = [
    {"slug": "short-film", "title": "فیلم کوتاه", "art": "film", "priority": 1},
    {"slug": "feature-film", "title": "فیلم سینمایی", "art": "film", "priority": 2},
    {"slug": "series", "title": "سریال", "art": "film", "priority": 3},
    {"slug": "commercial", "title": "تبلیغات", "art": "film", "priority": 4},
    {"slug": "content", "title": "تولید محتوا", "art": "film", "priority": 5},
    {"slug": "industrial", "title": "صنعتی", "art": "film", "priority": 6},
    {"slug": "stage-play", "title": "نمایش صحنه‌ای", "art": "theatre", "priority": 7},
    {"slug": "reading", "title": "خوانش", "art": "theatre", "priority": 8},
    {"slug": "student-theatre", "title": "تئاتر دانشجویی", "art": "theatre", "priority": 9},
]

HOME_POSTS = [
    {"kicker": "انتخاب بازیگر", "title": "چطور برای یک نقش کوتاه آماده شویم"},
    {"kicker": "پشت صحنه", "title": "از متن تا اولین تمرین چه می‌گذرد"},
    {"kicker": "فراخوان", "title": "خوانش وقتی گروه هنوز کامل نیست"},
    {"kicker": "راهنما", "title": "نقش نوجوان و حضور خانواده در جلسه"},
    {"kicker": "قرارداد", "title": "دستمزد نمایش صحنه‌ای را شفاف بنویسید"},
]

SOCIALS = [
    {"label": "تلگرام", "href": "https://t.me/honaryaar", "icon": "telegram"},
    {"label": "اینستاگرام", "href": "https://instagram.com/honaryaar", "icon": "instagram"},
    {"label": "بله", "href": "https://ble.ir/honaryaar", "icon": "bale"},
]

ARTISTS = [
    {
        "slug": "sara-mohammadi",
        "name": "سارا محمدی",
        "role": "actor",
        "city": "تهران",
        "about": "بازیگر تئاتر. ده سال روی صحنه، بیشتر در نقش‌های معاصر و متن‌های ایرانی. دنبال پروژه‌ای است که تمرین جدی و زمان‌بندی روشن داشته باشد.",
        "skills": ["بازیگری دوربین", "بدن", "لهجهٔ تهرانی"],
        "credits": [
            {"title": "اتاق شماره شش", "role": "پرستار", "year": "۱۴۰۳"},
            {"title": "خط تماس", "role": "لیلا", "year": "۱۴۰۲"},
            {"title": "زمستان در حیاط", "role": "دختر", "year": "۱۴۰۱"},
        ],
        "status": "claimed",
        "media": [
            {"kind": "عکس", "label": "پرتره"},
            {"kind": "ویدیو", "label": "مونولوگ دو دقیقه‌ای"},
        ],
    },
    {
        "slug": "kian-rezaei",
        "name": "کیان رضایی",
        "role": "actor",
        "city": "تهران",
        "about": "اطلاعات این صفحه از برنامهٔ جشنواره و معرفی گروه‌ها جمع شده است. صاحب پروفایل هنوز آن را در اختیار نگرفته.",
        "skills": ["بازیگری صحنه", "آواز"],
        "credits": [
            {"title": "مسافران", "role": "مرد جوان", "year": "۱۴۰۳"},
            {"title": "آخرین قطار", "role": "مسافر", "year": "۱۴۰۲"},
        ],
        "status": "indexed",
        "media": [{"kind": "عکس", "label": "عکس برنامه"}],
    },
    {
        "slug": "niloufar-ahmadi",
        "name": "نیلوفر احمدی",
        "role": "actor",
        "city": "اصفهان",
        "about": "بازیگر و مدرس بازیگری. بین اصفهان و تهران کار می‌کند و برای نقش‌های زن معاصر نمونهٔ اجرا دارد.",
        "skills": ["تدریس", "بداهه", "انگلیسی مکالمه"],
        "credits": [
            {"title": "سایه‌ها", "role": "راوی", "year": "۱۴۰۴"},
            {"title": "حیاط خلوت", "role": "خواهر", "year": "۱۴۰۲"},
        ],
        "status": "claimed",
        "media": [
            {"kind": "عکس", "label": "پرتره"},
            {"kind": "صوت", "label": "به‌زودی"},
        ],
    },
    {
        "slug": "armin-kazemi",
        "name": "آرمین کاظمی",
        "role": "actor",
        "city": "تهران",
        "about": "بازیگر مرد، محدودهٔ سنی نقش‌ها حدود سی تا چهل. سابقهٔ همکاری با گروه‌های مستقل تهران.",
        "skills": ["مبارزهٔ صحنه‌ای", "موتورسواری"],
        "credits": [
            {"title": "آخرین تمرین", "role": "همسر", "year": "۱۴۰۳"},
            {"title": "شبِ بلند", "role": "مرد", "year": "۱۴۰۱"},
        ],
        "status": "claimed",
        "media": [{"kind": "ویدیو", "label": "صحنه از آخرین تمرین"}],
    },
    {
        "slug": "hasti-moradi",
        "name": "هستی مرادی",
        "role": "actor",
        "city": "شیراز",
        "about": "بازیگر جوان. بیشتر در نمایش‌های دانشجویی و گروه‌های شیراز دیده شده و برای کار در تهران آمادهٔ رفت‌وآمد است.",
        "skills": ["حرکت", "کودک و نوجوان"],
        "credits": [{"title": "خط سفید", "role": "دختر", "year": "۱۴۰۴"}],
        "status": "indexed",
        "media": [{"kind": "عکس", "label": "عکس گروه"}],
    },
    {
        "slug": "pouria-nemati",
        "name": "پوریا نعمتی",
        "role": "actor",
        "city": "کرج",
        "about": "بازیگر مکمل. به نقش‌های کوتاه با متن دقیق علاقه دارد و می‌تواند در کرج و تهران تمرین کند.",
        "skills": ["گویش کرجی", "رانندگی"],
        "credits": [
            {"title": "خط سفید", "role": "همسایه", "year": "۱۴۰۴"},
            {"title": "پارکینگ", "role": "نگهبان", "year": "۱۴۰۳"},
        ],
        "status": "claimed",
        "media": [{"kind": "عکس", "label": "پرتره"}],
    },
    {
        "slug": "maryam-soleimani",
        "name": "مریم سلیمانی",
        "role": "director",
        "city": "تهران",
        "about": "کارگردان تئاتر. پروژهٔ جاری‌اش «اتاق شماره شش» است و برای دو نقش هنوز بازیگر می‌گردد.",
        "skills": ["کارگردانی", "انتخاب بازیگر", "متن معاصر"],
        "credits": [
            {"title": "اتاق شماره شش", "role": "کارگردان", "year": "۱۴۰۵"},
            {"title": "خط تماس", "role": "کارگردان", "year": "۱۴۰۲"},
        ],
        "status": "claimed",
        "media": [{"kind": "عکس", "label": "عکس تمرین"}],
    },
    {
        "slug": "reza-ghasemi",
        "name": "رضا قاسمی",
        "role": "actor",
        "city": "مشهد",
        "about": "بازیگر نوجوان و جوان. برای نقش‌های ۱۶ تا ۲۲ سال نمونه دارد.",
        "skills": ["بازیگری نوجوان", "ورزش"],
        "credits": [{"title": "زمستان طولانی", "role": "پسر", "year": "۱۴۰۳"}],
        "status": "indexed",
        "media": [{"kind": "عکس", "label": "عکس معرفی"}],
    },
]

PROJECTS = [
    {
        "slug": "room-six",
        "title": "اتاق شماره شش",
        "city": "تهران",
        "lead_role": "director",
        "art": "theatre",
        "production": "نمایش صحنه‌ای",
        "summary": "نمایش صحنه‌ای معاصر. تمرین‌ها از آذر شروع می‌شود و اجرا برای بهمن در یک سالن کوچک تهران برنامه‌ریزی شده.",
        "status": "در حال جذب بازیگر",
    },
    {
        "slug": "passengers",
        "title": "مسافران",
        "city": "تهران",
        "lead_role": "producer",
        "art": "theatre",
        "production": "نمایش صحنه‌ای",
        "summary": "نمایشی دربارهٔ انتظار و سفر. یک نقش مرد جوان هنوز باز است.",
        "status": "در حال جذب بازیگر",
    },
    {
        "slug": "shadows",
        "title": "سایه‌ها",
        "city": "اصفهان",
        "lead_role": "teacher",
        "art": "theatre",
        "production": "تئاتر دانشجویی",
        "summary": "خوانش و اجرای دانشجویی. دستمزد ندارد و تمرکز روی تمرین بازیگری است.",
        "status": "فراخوان باز",
    },
    {
        "slug": "last-rehearsal",
        "title": "آخرین تمرین",
        "city": "تهران",
        "lead_role": "producer",
        "art": "theatre",
        "production": "نمایش صحنه‌ای",
        "summary": "نمایش خانوادگی با دو نقش نسل قبل. به دنبال بازیگر زن ۴۰ تا ۵۵ سال.",
        "status": "در حال جذب بازیگر",
    },
    {
        "slug": "white-line",
        "title": "خط سفید",
        "city": "کرج",
        "lead_role": "director",
        "art": "theatre",
        "production": "خوانش",
        "summary": "خوانش یک متن کوتاه در کرج. اگر گروه جور شود، دربارهٔ اجرای کامل جداگانه حرف می‌زنند.",
        "status": "فراخوان باز",
    },
    {
        "slug": "long-winter",
        "title": "زمستان طولانی",
        "city": "مشهد",
        "lead_role": "producer",
        "art": "theatre",
        "production": "نمایش صحنه‌ای",
        "summary": "نمایش نوروزی با یک نقش اصلی نوجوان. انتخاب بازیگر هنوز باز است.",
        "status": "در حال جذب بازیگر",
    },
]

OPPORTUNITIES = [
    {
        "slug": "room-six-nurse",
        "title": "پرستار",
        "project": "room-six",
        "role": "actor",
        "production": "نمایش صحنه‌ای",
        "city": "تهران",
        "age_min": 25,
        "age_max": 35,
        "gender": "female",
        "count": 1,
        "paid": True,
        "featured": True,
        "pay_note": "دستمزد توافقی، پرداخت بعد از شروع اجرا.",
        "start_date": date(2026, 11, 22),
        "end_date": date(2027, 2, 19),
        "deadline": date(2026, 11, 6),
        "description": "نقش زن جوانی که بین مراقبت و حقیقت گیر کرده. متن معاصر است و لهجهٔ مشخص لازم نیست.",
        "requirements": ["سابقهٔ حداقل دو نمایش صحنه‌ای", "امکان تمرین عصرها در تهران", "نمونهٔ ویدیو تا دو دقیقه"],
        "status": "باز",
    },
    {
        "slug": "passengers-young-man",
        "title": "مرد جوان",
        "project": "passengers",
        "role": "actor",
        "production": "نمایش صحنه‌ای",
        "city": "تهران",
        "age_min": 20,
        "age_max": 28,
        "gender": "male",
        "count": 1,
        "paid": True,
        "featured": True,
        "pay_note": "مبلغ بعد از انتخاب نهایی اعلام می‌شود.",
        "start_date": date(2027, 3, 21),
        "end_date": date(2027, 4, 20),
        "deadline": date(2026, 11, 22),
        "description": "مسافری که بخش زیادی از نمایش را در سکوت بازی می‌کند. بدن و حضور مهم‌تر از دیالوگ طولانی است.",
        "requirements": ["آمادگی بدنی", "سابقهٔ صحنه", "اقامت یا رفت‌وآمد به تهران"],
        "status": "باز",
    },
    {
        "slug": "shadows-narrator",
        "title": "راوی",
        "project": "shadows",
        "role": "actor",
        "production": "تئاتر دانشجویی",
        "city": "اصفهان",
        "age_min": 20,
        "age_max": 30,
        "gender": "any",
        "count": 2,
        "paid": False,
        "featured": True,
        "pay_note": "این پروژه دستمزد ندارد. گواهی کارگاه داده می‌شود.",
        "start_date": date(2026, 12, 22),
        "end_date": date(2027, 1, 20),
        "deadline": date(2026, 11, 11),
        "description": "دو راوی، زن یا مرد. تمرکز روی صدا و روایت است، نه میزانسن سنگین.",
        "requirements": ["صدای واضح", "امکان حضور در اصفهان"],
        "status": "باز",
    },
    {
        "slug": "last-rehearsal-mother",
        "title": "مادر",
        "project": "last-rehearsal",
        "role": "actor",
        "production": "نمایش صحنه‌ای",
        "city": "تهران",
        "age_min": 40,
        "age_max": 55,
        "gender": "female",
        "count": 1,
        "paid": True,
        "featured": True,
        "pay_note": "قرارداد کوتاه تمرین و اجرا.",
        "start_date": date(2026, 12, 22),
        "end_date": date(2027, 3, 20),
        "deadline": date(2026, 11, 21),
        "description": "محور عاطفی نمایش. نقش دیالوگ‌محور است و نیاز به تجربهٔ نقش‌های نسل قبل دارد.",
        "requirements": ["سابقهٔ نقش اول یا مکمل جدی", "نمونهٔ اجرای صحنه‌ای"],
        "status": "باز",
    },
    {
        "slug": "white-line-supporting",
        "title": "بازیگر مکمل",
        "project": "white-line",
        "role": "actor",
        "production": "خوانش",
        "city": "کرج",
        "age_min": None,
        "age_max": None,
        "gender": "any",
        "count": 3,
        "paid": False,
        "featured": True,
        "pay_note": "خوانش بدون دستمزد. اگر به اجرا برسد، شرایط دوباره گفته می‌شود.",
        "start_date": date(2026, 11, 22),
        "end_date": date(2026, 12, 21),
        "deadline": date(2026, 12, 1),
        "description": "سه نقش کوتاه در یک خوانش. برای دیدن هماهنگی گروه است، نه اجرای کامل.",
        "requirements": ["امکان حضور در دو جلسهٔ کرج"],
        "status": "باز",
    },
    {
        "slug": "long-winter-son",
        "title": "پسر نوجوان",
        "project": "long-winter",
        "role": "actor",
        "production": "نمایش صحنه‌ای",
        "city": "مشهد",
        "age_min": 16,
        "age_max": 20,
        "gender": "male",
        "count": 1,
        "paid": True,
        "featured": True,
        "pay_note": "دستمزد متناسب با نقش نوجوان، با هماهنگی خانواده.",
        "start_date": date(2027, 3, 21),
        "end_date": date(2027, 4, 2),
        "deadline": date(2026, 11, 26),
        "description": "نقش اصلی جوان. برای زیر ۱۸ سال حضور والدین در جلسهٔ آشنای الزامی است.",
        "requirements": ["محدودهٔ سنی نقش", "معرفی کوتاه و یک عکس"],
        "status": "باز",
    },
]


MEDIA_KIND = {"عکس": "photo", "ویدیو": "video", "صوت": "audio"}
MEDIA_LABEL = {"photo": "عکس", "video": "ویدیو", "audio": "صوت"}
PROJECT_STATUS = {"در حال جذب بازیگر": "casting", "فراخوان باز": "open_call"}
_JALALI_MONTHS = (
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
)
_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _to_jalali(year, month, day):
    gregorian_month_lengths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    jalali_month_lengths = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
    year -= 1600
    month -= 1
    day -= 1
    day_number = 365 * year + (year + 3) // 4 - (year + 99) // 100 + (year + 399) // 400
    for index in range(month):
        day_number += gregorian_month_lengths[index]
    leap = (year + 1600) % 4 == 0 and ((year + 1600) % 100 != 0 or (year + 1600) % 400 == 0)
    if month > 1 and leap:
        day_number += 1
    day_number += day - 79
    year_cycles = day_number // 12053
    day_number %= 12053
    jalali_year = 979 + 33 * year_cycles + 4 * (day_number // 1461)
    day_number %= 1461
    if day_number >= 366:
        jalali_year += (day_number - 1) // 365
        day_number = (day_number - 1) % 365
    for index, length in enumerate(jalali_month_lengths):
        if day_number < length:
            return jalali_year, index + 1, day_number + 1
        day_number -= length
    return jalali_year, 12, day_number + 1


def format_date(value):
    if not value:
        return ""
    jalali_year, jalali_month, jalali_day = _to_jalali(value.year, value.month, value.day)
    text = f"{jalali_day} {_JALALI_MONTHS[jalali_month - 1]} {jalali_year}"
    return text.translate(_PERSIAN_DIGITS)


def format_datetime(value):
    if not value:
        return ""
    clock = value.strftime("%H:%M").translate(_PERSIAN_DIGITS)
    return f"{format_date(value)}، {clock}"


def format_time(value):
    if not value:
        return ""
    return value.strftime("%H:%M").translate(_PERSIAN_DIGITS)


def format_jalali_period(start, end=None):
    if not start:
        return ""
    if end is None or (start.year, start.month, start.day) == (end.year, end.month, end.day):
        return format_date(start)
    start_year, start_month, _start_day = _to_jalali(start.year, start.month, start.day)
    end_year, end_month, _end_day = _to_jalali(end.year, end.month, end.day)
    start_label = _JALALI_MONTHS[start_month - 1]
    end_label = _JALALI_MONTHS[end_month - 1]
    if (start_year, start_month) == (end_year, end_month):
        text = f"{start_label} {start_year}"
    elif start_year == end_year:
        text = f"{start_label} – {end_label} {start_year}"
    else:
        text = f"{start_label} {start_year} – {end_label} {end_year}"
    return text.translate(_PERSIAN_DIGITS)


def format_date_range(start, end):
    if start and end:
        return f"{format_date(start)} تا {format_date(end)}"
    return format_date(start) or format_date(end)


def gender_label(value):
    return GENDER_FA.get(value, value)


def genders():
    from ejranow.models import Gender

    return [{"value": value, "label": gender_label(value)} for value, _title in Gender.choices]


def role_title(slug):
    from ejranow.models import Role

    match = Role.objects.filter(slug=slug).first()
    return match.title if match else slug


def art_title(slug):
    from ejranow.models import Art

    return dict(Art.choices).get(slug, slug)


def _art_order():
    from ejranow.models import Art

    return [value for value, _label in Art.choices]


def arts_in_use():
    from ejranow.models import Art, ArtCategory

    present = set(ArtCategory.objects.values_list("art", flat=True).distinct())
    return [{"slug": value, "title": label} for value, label in Art.choices if value in present]


def roles():
    from ejranow.models import Role

    return [{"slug": item.slug, "title": item.title} for item in Role.objects.all()]


def age_label(item):
    start, end = item["age_min"], item["age_max"]
    if start and end:
        return f"{start} تا {end} سال"
    if start:
        return f"از {start} سال"
    if end:
        return f"تا {end} سال"
    return ""


def _contains(value, query):
    return query.casefold() in value.casefold()


def _artist_dict(profile):
    links = list(profile.profile_roles.all())
    primary = next((link.role for link in links if link.is_primary), None)
    if primary is None and links:
        primary = links[0].role
    return {
        "slug": profile.slug,
        "name": profile.name,
        "role": primary.slug if primary else "",
        "city": profile.city.title if profile.city_id else "",
        "about": profile.about,
        "arts": list(profile.arts or []),
        "art_titles": [art_title(slug) for slug in _art_order() if slug in set(profile.arts or [])],
        "skills": [
            {"label": link.skill.label, "level": link.level}
            for link in profile.skill_links.all()
        ],
        "credits": [
            {"title": credit.title, "role": credit.role_name, "year": credit.year}
            for credit in profile.credits.all()
        ],
        "status": profile.status,
        "media": [
            {"kind": MEDIA_LABEL.get(item.kind, item.kind), "label": item.label}
            for item in profile.media_items.all()
        ],
    }


def _testimonial_dict(item):
    if item.profile_id and (item.profile.name or item.profile.first_name):
        name = item.profile.name or f"{item.profile.first_name} {item.profile.last_name}".strip()
    else:
        name = item.name
    role = item.role.title if item.role_id else item.role_label
    project = item.project if item.project_id else None
    return {
        "quote": item.quote,
        "name": name,
        "role": role,
        "project_slug": project.slug if project else "",
        "project_title": project.title if project else "",
    }


def _profile_name(profile):
    if profile is None:
        return ""
    full = f"{profile.first_name} {profile.last_name}".strip()
    return full or profile.name


def _project_dict(project):
    art = project.art_category.art if project.art_category_id else ""
    return {
        "slug": project.slug,
        "title": project.title,
        "city": project.city.title if project.city_id else "",
        "lead": _profile_name(project.owner),
        "lead_role": project.lead_role.slug if project.lead_role_id else "",
        "art": art,
        "art_title": project.art_category.get_art_display() if project.art_category_id else "",
        "production": project.art_category.title if project.art_category_id else "",
        "summary": project.summary,
        "status": project.get_status_display(),
        "testimonials": [_testimonial_dict(item) for item in project.testimonials.all()],
    }


def _opportunity_dict(item):
    return {
        "slug": item.slug,
        "title": item.title,
        "project": item.project.slug,
        "role": item.role.slug,
        "art": item.art_category.art if item.art_category_id else "",
        "art_title": item.art_category.get_art_display() if item.art_category_id else "",
        "production": item.art_category.title if item.art_category_id else "",
        "city": item.city.title if item.city_id else "",
        "age_min": item.age_min,
        "age_max": item.age_max,
        "gender": item.gender,
        "count": item.count,
        "paid": item.paid,
        "featured": item.featured,
        "pay_note": item.pay_note,
        "dates": format_date_range(item.start_date, item.end_date),
        "deadline": format_date(item.deadline),
        "description": item.description,
        "requirements": item.requirements or [],
        "status": item.status,
    }


def _artists():
    from ejranow.models import Profile

    profiles = (
        Profile.objects.filter(profile_roles__isnull=False)
        .select_related("city")
        .prefetch_related("profile_roles__role", "credits", "media_items", "skill_links__skill")
        .distinct()
    )
    return [_artist_dict(item) for item in profiles]


def _projects():
    from django.db.models import Prefetch

    from ejranow.models import Project, Testimonial

    quotes = Testimonial.objects.select_related("profile", "role", "project")
    projects = Project.objects.select_related("owner", "art_category", "lead_role", "city").prefetch_related(
        Prefetch("testimonials", queryset=quotes)
    )
    return [_project_dict(item) for item in projects]


def _opportunities():
    from ejranow.models import Opportunity

    items = Opportunity.objects.select_related("project", "project__art_category", "role", "city", "art_category")
    return [_opportunity_dict(item) for item in items]


def project_by_slug(slug):
    return next((item for item in _projects() if item["slug"] == slug), None)


def artist_by_slug(slug):
    return next((item for item in _artists() if item["slug"] == slug), None)


def opportunity_by_slug(slug):
    return next((item for item in _opportunities() if item["slug"] == slug), None)


def opportunities_for_project(slug):
    return [item for item in _opportunities() if item["project"] == slug]


def _artist_text(artist):
    credit = " ".join(item["title"] for item in artist["credits"])
    return " ".join(
        [
            artist["name"],
            artist["city"],
            role_title(artist["role"]),
            " ".join(artist["art_titles"]),
            " ".join(item["label"] for item in artist["skills"]),
            credit,
        ]
    )


def artist_arts():
    present = set()
    for artist in _artists():
        present.update(artist["arts"])
    return [{"slug": slug, "title": art_title(slug)} for slug in _art_order() if slug in present]


def list_artists(q="", city="", role="", art=""):
    items = _artists()
    if city:
        items = [item for item in items if item["city"] == city]
    if role:
        items = [item for item in items if item["role"] == role]
    if art:
        items = [item for item in items if art in item["arts"]]
    if q:
        items = [item for item in items if _contains(_artist_text(item), q)]
    return items


def _opportunity_matches(item, query, city, paid, gender, production, role, age, art):
    project = project_by_slug(item["project"])
    if city and item["city"] != city:
        return False
    if art and item["art"] != art:
        return False
    if paid == "paid" and not item["paid"]:
        return False
    if paid == "unpaid" and item["paid"]:
        return False
    if gender and item["gender"] not in {"any", gender}:
        return False
    if production and item["production"] != production:
        return False
    if role and item["role"] != role:
        return False
    if age is not None:
        start = item["age_min"] if item["age_min"] is not None else 0
        end = item["age_max"] if item["age_max"] is not None else 200
        if not start <= age <= end:
            return False
    if query:
        text = " ".join(
            [
                item["title"],
                project["title"] if project else "",
                item["city"],
                item["production"],
                item["dates"],
                item["deadline"],
                gender_label(item["gender"]),
                role_title(item["role"]),
                item["description"],
                project["art_title"] if project else "",
            ]
        )
        if not _contains(text, query):
            return False
    return True


def list_opportunities(q="", city="", paid="", gender="", production="", role="", age=None, art=""):
    return [
        item
        for item in _opportunities()
        if _opportunity_matches(item, q, city, paid, gender, production, role, age, art)
    ]


def opportunity_facets():
    items = _opportunities()
    cities = list(dict.fromkeys(item["city"] for item in items if item["city"]))
    from ejranow.models import City

    order = {
        title: index
        for index, title in enumerate(City.objects.order_by("priority", "title").values_list("title", flat=True))
    }
    cities.sort(key=lambda title: (order.get(title, 10_000), title))

    role_slugs = list(dict.fromkeys(item["role"] for item in items if item["role"]))
    roles = sorted(
        ({"slug": slug, "title": role_title(slug)} for slug in role_slugs),
        key=lambda item: item["title"],
    )
    from ejranow.models import Art

    present_arts = {item["art"] for item in items if item["art"]}
    arts = [{"slug": value, "title": label} for value, label in Art.choices if value in present_arts]
    productions = list(dict.fromkeys(item["production"] for item in items if item["production"]))
    present_genders = {item["gender"] for item in items if item["gender"]}
    genders = [
        {"value": value, "label": gender_label(value)}
        for value in ("male", "female", "any")
        if value in present_genders
    ]
    paid = []
    if any(item["paid"] for item in items):
        paid.append(("paid", "پرداختی"))
    if any(not item["paid"] for item in items):
        paid.append(("unpaid", "غیرپرداختی"))
    return {
        "cities": cities,
        "roles": roles,
        "arts": arts,
        "productions": productions,
        "genders": genders,
        "paid": paid,
    }


def opportunity_quick(facets):
    cities = set(facets["cities"])
    roles = {item["slug"] for item in facets["roles"]}
    productions = set(facets["productions"])
    genders = {item["value"] for item in facets["genders"]}
    paid = {value for value, _label in facets["paid"]}
    allowed = {"city": cities, "role": roles, "production": productions, "gender": genders, "paid": paid}
    art_chips = [(item["title"], {"art": item["slug"]}) for item in facets["arts"]]
    chips = []
    placed_arts = False
    for label, params in OPPORTUNITY_QUICK:
        if all(str(value) in allowed.get(key, ()) for key, value in params.items()):
            chips.append((label, params))
            if not placed_arts and set(params) == {"city"}:
                chips.extend(art_chips)
                placed_arts = True
    if not placed_arts:
        chips = art_chips + chips
    return chips


def _project_text(project):
    return " ".join(
        [
            project["title"],
            project["city"],
            project["art_title"],
            project["summary"],
            project["status"],
        ]
    )


def list_projects(q="", city="", art=""):
    items = _projects()
    if city:
        items = [item for item in items if item["city"] == city]
    if art:
        items = [item for item in items if item["art"] == art]
    if q:
        items = [item for item in items if _contains(_project_text(item), q)]
    return items


OPPORTUNITY_QUICK = [
    ("تهران", {"city": "تهران"}),
    ("مرد", {"gender": "male"}),
    ("زن", {"gender": "female"}),
    ("پرداختی", {"paid": "paid"}),
    ("بازیگر", {"role": "actor"}),
    ("دستیار کارگردان", {"role": "assistant-director"}),
    ("هنرجو", {"role": "student"}),
    ("آهنگساز", {"role": "composer"}),
    ("نمایش صحنه‌ای", {"production": "نمایش صحنه‌ای"}),
]

ARTIST_QUICK = [
    ("تهران", {"city": "تهران"}),
    ("بازیگر", {"role": "actor"}),
    ("دستیار کارگردان", {"role": "assistant-director"}),
    ("هنرجو", {"role": "student"}),
    ("آهنگساز", {"role": "composer"}),
]


def artist_quick():
    art_chips = [(item["title"], {"art": item["slug"]}) for item in artist_arts()]
    chips = []
    placed = False
    for label, params in ARTIST_QUICK:
        chips.append((label, params))
        if not placed and set(params) == {"city"}:
            chips.extend(art_chips)
            placed = True
    if not placed:
        chips = art_chips + chips
    return chips


def arts():
    return arts_in_use()


def choice_group(name, label, pairs, selected):
    selected = "" if selected is None else str(selected)
    options = [{"value": "", "label": "همه", "selected": selected == ""}]
    selected_index = None
    for value, text in pairs:
        value = str(value)
        is_selected = bool(selected) and value == selected
        options.append({"value": value, "label": text, "selected": is_selected})
        if is_selected:
            selected_index = len(options) - 1
    return {
        "name": name,
        "label": label,
        "kind": "choice",
        "options": options,
        "open": selected_index is not None,
        "more": selected_index is not None and selected_index >= 6,
        "selected": 1 if selected_index else 0,
    }


def text_group(name, label, value, placeholder):
    value = "" if value is None else str(value)
    return {
        "name": name,
        "label": label,
        "kind": "text",
        "value": value,
        "placeholder": placeholder,
        "open": bool(value),
        "more": False,
        "options": [],
        "selected": 1 if value else 0,
    }


def filter_chips(request, specs):
    chips = []
    for label, params in specs:
        query = request.GET.copy()
        active = all(query.get(key, "") == str(value) for key, value in params.items())
        if active:
            for key in params:
                query.pop(key, None)
        else:
            for key, value in params.items():
                query[key] = str(value)
        encoded = query.urlencode()
        chips.append(
            {
                "label": label,
                "active": active,
                "href": f"?{encoded}" if encoded else request.path,
            }
        )
    return chips


def clear_filters_href(request, keep=("q",)):
    query = request.GET.copy()
    for key in list(query.keys()):
        if key not in keep:
            query.pop(key, None)
    encoded = query.urlencode()
    return f"?{encoded}" if encoded else request.path


def cities():
    from ejranow.models import City

    return list(City.objects.values_list("title", flat=True))


def persian_number(value):
    return str(value).translate(_PERSIAN_DIGITS)


def round_up_five(value):
    if value <= 0:
        return 0
    return ((value + 4) // 5) * 5


def hero_roles():
    from ejranow.models import Role

    titles = {
        item.slug: item.title
        for item in Role.objects.filter(profile_roles__isnull=False).distinct()
    }
    ordered = [titles[item["slug"]] for item in ROLES if item["slug"] in titles]
    return ordered or list(titles.values())


def hire_stats():
    from ejranow.models import Profile, ProfileRole, ProfileSkill

    artists = Profile.objects.count()
    roles = ProfileRole.objects.values("role_id").distinct().count()
    cities = Profile.objects.exclude(city=None).values("city_id").distinct().count()
    skills = ProfileSkill.objects.values("skill_id").distinct().count()
    return [
        {"value": persian_number(round_up_five(artists)), "label": "هنرمند فعال"},
        {"value": persian_number(round_up_five(roles)), "label": "نقش تخصصی"},
        {"value": persian_number(round_up_five(cities)), "label": "شهر"},
        {"value": persian_number(round_up_five(skills)), "label": "مهارت"},
    ]


def hero_fields():
    return [item["title"] for item in arts_in_use()]


def talent_stats():
    from django.db.models import Q

    from ejranow.models import City, Opportunity, OpportunityStatus, Project, ProjectStatus, Role

    live = [ProjectStatus.CASTING, ProjectStatus.OPEN_CALL]
    calls = Opportunity.objects.filter(status=OpportunityStatus.OPEN).count()
    projects = Project.objects.filter(status__in=live).count()
    roles = (
        Role.objects.filter(
            Q(opportunities__status=OpportunityStatus.OPEN)
            | Q(profile_roles__isnull=False)
            | Q(led_projects__status__in=live)
        )
        .distinct()
        .count()
    )
    cities = (
        City.objects.filter(
            Q(opportunities__status=OpportunityStatus.OPEN) | Q(projects__status__in=live)
        )
        .distinct()
        .count()
    )
    return [
        {"value": persian_number(round_up_five(calls)), "label": "فراخوان همکاری"},
        {"value": persian_number(round_up_five(projects)), "label": "پروژه در حال جذب"},
        {"value": persian_number(round_up_five(roles)), "label": "نقش تخصصی"},
        {"value": persian_number(round_up_five(cities)), "label": "شهر"},
    ]


def featured_opportunities():
    return [item for item in _opportunities() if item["featured"]]


def featured_testimonials():
    from ejranow.models import Testimonial

    items = Testimonial.objects.filter(featured=True).select_related("project", "profile", "role")
    return [_testimonial_dict(item) for item in items]


def featured_cities():
    from ejranow.models import City

    return list(City.objects.filter(featured=True).values_list("title", flat=True))


def search_modal_arts():
    from ejranow.models import Art

    titles = dict(Art.choices)
    shown = (
        ("theatre", False),
        ("music", False),
        ("film", True),
        ("painting", True),
    )
    return [{"slug": slug, "title": titles[slug], "soon": soon} for slug, soon in shown]


def search_shortcuts():
    from ejranow.models import Role

    roles = {item.slug: item.title for item in Role.objects.all()}
    return {
        "search_arts": search_modal_arts(),
        "search_roles": [
            {"slug": item["slug"], "title": roles[item["slug"]]}
            for item in ROLES
            if item["slug"] in roles
        ],
    }


def footer_shortcuts():
    from ejranow.models import City, ArtCategory, Project, Role

    cities = list(City.objects.order_by("priority", "title").values_list("title", flat=True)[:3])
    by_slug = {item.slug: item for item in Role.objects.all()}
    roles = [
        {"slug": item["slug"], "title": by_slug[item["slug"]].title}
        for item in ROLES
        if item["slug"] in by_slug
    ]
    projects = [
        {"slug": item.slug, "title": item.title}
        for item in Project.objects.order_by("-pk")[:7]
    ]
    productions = []
    seen = set()
    for title in ArtCategory.objects.filter(opportunities__isnull=False).order_by("priority", "title").values_list("title", flat=True):
        if title in seen:
            continue
        seen.add(title)
        productions.append(title)
        if len(productions) == 3:
            break
    if not productions:
        productions = list(ArtCategory.objects.order_by("priority", "title").values_list("title", flat=True)[:3])
    return {
        "footer_cities": cities,
        "footer_roles": roles,
        "footer_projects": projects,
        "footer_productions": productions,
        "footer_socials": SOCIALS,
    }


def search(query):
    if not query:
        return [], [], []
    return list_artists(q=query), list_opportunities(q=query), list_projects(q=query)


def seed():
    from ejranow.models import (
        City,
        Credit,
        Opportunity,
        Profile,
        ProfileMedia,
        ProfileRole,
        ProfileSkill,
        Project,
        ArtCategory,
        Role,
        Skill,
    )

    skills_by_slug = {}
    for item in SKILLS:
        skills_by_slug[item["slug"]], _created = Skill.objects.get_or_create(
            slug=item["slug"],
            defaults={"title": item["title"], "group": item["group"]},
        )

    productions_by_title = {}
    productions_by_slug = {}
    for item in PRODUCTIONS:
        art_category, _created = ArtCategory.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "art": item["art"],
                "priority": item["priority"],
            },
        )
        productions_by_title[item["title"]] = art_category
        productions_by_slug[item["slug"]] = art_category
    roles_by_slug = {}
    for item in ROLES:
        roles_by_slug[item["slug"]], _created = Role.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "art_category": productions_by_slug[item.get("production", "stage-play")],
            },
        )
    cities_by_title = {}
    for item in CITIES:
        cities_by_title[item["title"]], _created = City.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "province": item["province"],
                "priority": item["priority"],
                "featured": item["featured"],
            },
        )
    for item in ARTISTS:
        profile, _created = Profile.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "name": item["name"],
                "city": cities_by_title[item["city"]],
                "about": item["about"],
                "status": item["status"],
            },
        )
        for title in item["skills"]:
            slug = LEGACY_SKILL_TITLES[title]
            ProfileSkill.objects.get_or_create(
                profile=profile,
                skill=skills_by_slug[slug],
                defaults={"level": SAMPLE_SKILL_LEVELS.get(item["slug"], {}).get(title, 2)},
            )
        ProfileRole.objects.get_or_create(
            profile=profile,
            role=roles_by_slug[item["role"]],
            defaults={"is_primary": True},
        )
        for credit in item["credits"]:
            Credit.objects.get_or_create(
                profile=profile,
                title=credit["title"],
                role_name=credit["role"],
                defaults={"year": credit["year"]},
            )
        for media in item["media"]:
            ProfileMedia.objects.get_or_create(
                profile=profile,
                label=media["label"],
                defaults={"kind": MEDIA_KIND.get(media["kind"], "photo")},
            )
    projects = {}
    for item in PROJECTS:
        projects[item["slug"]], _created = Project.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "city": cities_by_title[item["city"]],
                "art_category": productions_by_title[item["production"]],
                "lead_role": roles_by_slug[item["lead_role"]],
                "summary": item["summary"],
                "status": PROJECT_STATUS[item["status"]],
            },
        )
    for item in OPPORTUNITIES:
        Opportunity.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "project": projects[item["project"]],
                "role": roles_by_slug[item["role"]],
                "art_category": productions_by_title[item["production"]],
                "city": cities_by_title[item["city"]],
                "age_min": item["age_min"],
                "age_max": item["age_max"],
                "gender": item["gender"],
                "count": item["count"],
                "paid": item["paid"],
                "featured": item.get("featured", False),
                "pay_note": item["pay_note"],
                "start_date": item["start_date"],
                "end_date": item["end_date"],
                "deadline": item["deadline"],
                "description": item["description"],
                "requirements": item["requirements"],
                "status": "open",
            },
        )
