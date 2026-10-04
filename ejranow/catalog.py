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

ART_CATEGORIES = [
    {"slug": "theatre", "title": "تئاتر", "active": True},
    {"slug": "music", "title": "موسیقی", "active": False},
    {"slug": "film", "title": "سینما", "active": False},
    {"slug": "painting", "title": "نقاشی", "active": False},
]

CITIES = [
    {"slug": "tehran", "title": "تهران", "province": "تهران", "priority": 1, "featured": True},
    {"slug": "karaj", "title": "کرج", "province": "البرز", "priority": 2, "featured": True},
    {"slug": "mashhad", "title": "مشهد", "province": "خراسان رضوی", "priority": 3, "featured": True},
    {"slug": "isfahan", "title": "اصفهان", "province": "اصفهان", "priority": 4, "featured": True},
    {"slug": "shiraz", "title": "شیراز", "province": "فارس", "priority": 5, "featured": True},
    {"slug": "tabriz", "title": "تبریز", "province": "آذربایجان شرقی", "priority": 6, "featured": True},
    {"slug": "ahvaz", "title": "اهواز", "province": "خوزستان", "priority": 7, "featured": True},
    {"slug": "qom", "title": "قم", "province": "قم", "priority": 8, "featured": False},
    {"slug": "kermanshah", "title": "کرمانشاه", "province": "کرمانشاه", "priority": 9, "featured": False},
    {"slug": "rasht", "title": "رشت", "province": "گیلان", "priority": 10, "featured": True},
    {"slug": "kerman", "title": "کرمان", "province": "کرمان", "priority": 11, "featured": False},
    {"slug": "urmia", "title": "ارومیه", "province": "آذربایجان غربی", "priority": 12, "featured": False},
    {"slug": "zahedan", "title": "زاهدان", "province": "سیستان و بلوچستان", "priority": 13, "featured": False},
    {"slug": "hamadan", "title": "همدان", "province": "همدان", "priority": 14, "featured": False},
    {"slug": "yazd", "title": "یزد", "province": "یزد", "priority": 15, "featured": True},
    {"slug": "arak", "title": "اراک", "province": "مرکزی", "priority": 16, "featured": False},
    {"slug": "ardabil", "title": "اردبیل", "province": "اردبیل", "priority": 17, "featured": False},
    {"slug": "bandar-abbas", "title": "بندرعباس", "province": "هرمزگان", "priority": 18, "featured": False},
    {"slug": "zanjan", "title": "زنجان", "province": "زنجان", "priority": 19, "featured": False},
    {"slug": "sanandaj", "title": "سنندج", "province": "کردستان", "priority": 20, "featured": False},
    {"slug": "qazvin", "title": "قزوین", "province": "قزوین", "priority": 21, "featured": False},
    {"slug": "khorramabad", "title": "خرم‌آباد", "province": "لرستان", "priority": 22, "featured": False},
    {"slug": "gorgan", "title": "گرگان", "province": "گلستان", "priority": 23, "featured": False},
    {"slug": "sari", "title": "ساری", "province": "مازندران", "priority": 24, "featured": False},
    {"slug": "bushehr", "title": "بوشهر", "province": "بوشهر", "priority": 25, "featured": False},
    {"slug": "birjand", "title": "بیرجند", "province": "خراسان جنوبی", "priority": 26, "featured": False},
    {"slug": "shahrekord", "title": "شهرکرد", "province": "چهارمحال و بختیاری", "priority": 27, "featured": False},
    {"slug": "yasuj", "title": "یاسوج", "province": "کهگیلویه و بویراحمد", "priority": 28, "featured": False},
    {"slug": "semnan", "title": "سمنان", "province": "سمنان", "priority": 29, "featured": False},
    {"slug": "ilam", "title": "ایلام", "province": "ایلام", "priority": 30, "featured": False},
    {"slug": "bojnord", "title": "بجنورد", "province": "خراسان شمالی", "priority": 31, "featured": False},
    {"slug": "kashan", "title": "کاشان", "province": "اصفهان", "priority": 32, "featured": False},
    {"slug": "abadan", "title": "آبادان", "province": "خوزستان", "priority": 33, "featured": False},
    {"slug": "neyshabur", "title": "نیشابور", "province": "خراسان رضوی", "priority": 34, "featured": False},
]
GENDER_FA = {
    "male": "مرد",
    "female": "زن",
    "any": "بدون تفاوت",
}
PRODUCTIONS = ["نمایش صحنه‌ای", "خوانش", "تئاتر دانشجویی"]

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
        "lead": "مریم سلیمانی",
        "lead_role": "director",
        "category": "theatre",
        "summary": "نمایش صحنه‌ای معاصر. تمرین‌ها از آذر شروع می‌شود و اجرا برای بهمن در یک سالن کوچک تهران برنامه‌ریزی شده.",
        "status": "در حال جذب بازیگر",
    },
    {
        "slug": "passengers",
        "title": "مسافران",
        "city": "تهران",
        "lead": "گروه مستقل مسافر",
        "lead_role": "producer",
        "category": "theatre",
        "summary": "نمایشی دربارهٔ انتظار و سفر. یک نقش مرد جوان هنوز باز است.",
        "status": "در حال جذب بازیگر",
    },
    {
        "slug": "shadows",
        "title": "سایه‌ها",
        "city": "اصفهان",
        "lead": "کارگاه دانشگاه",
        "lead_role": "teacher",
        "category": "theatre",
        "summary": "خوانش و اجرای دانشجویی. دستمزد ندارد و تمرکز روی تمرین بازیگری است.",
        "status": "فراخوان باز",
    },
    {
        "slug": "last-rehearsal",
        "title": "آخرین تمرین",
        "city": "تهران",
        "lead": "آتلیهٔ صحنه",
        "lead_role": "producer",
        "category": "theatre",
        "summary": "نمایش خانوادگی با دو نقش نسل قبل. به دنبال بازیگر زن ۴۰ تا ۵۵ سال.",
        "status": "در حال جذب بازیگر",
    },
    {
        "slug": "white-line",
        "title": "خط سفید",
        "city": "کرج",
        "lead": "گروه خط",
        "lead_role": "director",
        "category": "theatre",
        "summary": "خوانش یک متن کوتاه در کرج. اگر گروه جور شود، دربارهٔ اجرای کامل جداگانه حرف می‌زنند.",
        "status": "فراخوان باز",
    },
    {
        "slug": "long-winter",
        "title": "زمستان طولانی",
        "city": "مشهد",
        "lead": "خانهٔ تئاتر مشهد",
        "lead_role": "producer",
        "category": "theatre",
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


def category_title(slug):
    from ejranow.models import ArtCategory

    match = ArtCategory.objects.filter(slug=slug).first()
    return match.title if match else slug


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
        "skills": profile.skills or [],
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


def _project_dict(project):
    return {
        "slug": project.slug,
        "title": project.title,
        "city": project.city.title if project.city_id else "",
        "lead": project.lead_name,
        "lead_role": project.lead_role.slug if project.lead_role_id else "",
        "category": project.category.slug,
        "summary": project.summary,
        "status": project.get_status_display(),
    }


def _opportunity_dict(item):
    return {
        "slug": item.slug,
        "title": item.title,
        "project": item.project.slug,
        "role": item.role.slug,
        "production": item.production,
        "city": item.city.title if item.city_id else "",
        "age_min": item.age_min,
        "age_max": item.age_max,
        "gender": item.gender,
        "count": item.count,
        "paid": item.paid,
        "pay_note": item.pay_note,
        "dates": format_date_range(item.start_date, item.end_date),
        "deadline": format_date(item.deadline),
        "description": item.description,
        "requirements": item.requirements or [],
        "status": item.status,
    }


def _artists():
    from ejranow.models import Profile

    profiles = Profile.objects.select_related("city").prefetch_related(
        "profile_roles__role",
        "credits",
        "media_items",
    )
    return [_artist_dict(item) for item in profiles]


def _projects():
    from ejranow.models import Project

    projects = Project.objects.select_related("category", "lead_role", "city")
    return [_project_dict(item) for item in projects]


def _opportunities():
    from ejranow.models import Opportunity

    items = Opportunity.objects.select_related("project", "role", "city")
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
        [artist["name"], artist["city"], role_title(artist["role"]), " ".join(artist["skills"]), credit]
    )


def list_artists(q="", city="", role=""):
    items = _artists()
    if city:
        items = [item for item in items if item["city"] == city]
    if role:
        items = [item for item in items if item["role"] == role]
    if q:
        items = [item for item in items if _contains(_artist_text(item), q)]
    return items


def _opportunity_matches(item, query, city, paid, gender, production, role, age):
    project = project_by_slug(item["project"])
    if city and item["city"] != city:
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
            ]
        )
        if not _contains(text, query):
            return False
    return True


def list_opportunities(q="", city="", paid="", gender="", production="", role="", age=None):
    return [
        item
        for item in _opportunities()
        if _opportunity_matches(item, q, city, paid, gender, production, role, age)
    ]


def list_projects():
    return _projects()


def cities():
    from ejranow.models import City

    return list(City.objects.values_list("title", flat=True))


def featured_cities():
    from ejranow.models import City

    return list(City.objects.filter(featured=True).values_list("title", flat=True))


def search(query):
    if not query:
        return [], []
    return list_artists(q=query), list_opportunities(q=query)


def seed():
    from ejranow.models import (
        ArtCategory,
        City,
        Credit,
        Opportunity,
        Profile,
        ProfileMedia,
        ProfileRole,
        Project,
        Role,
    )

    roles_by_slug = {}
    for item in ROLES:
        roles_by_slug[item["slug"]], _created = Role.objects.get_or_create(
            slug=item["slug"],
            defaults={"title": item["title"]},
        )
    categories = {}
    for item in ART_CATEGORIES:
        categories[item["slug"]], _created = ArtCategory.objects.get_or_create(
            slug=item["slug"],
            defaults={"title": item["title"], "active": item["active"]},
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
                "skills": item["skills"],
                "status": item["status"],
            },
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
                "category": categories[item["category"]],
                "lead_name": item["lead"],
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
                "production": item["production"],
                "city": cities_by_title[item["city"]],
                "age_min": item["age_min"],
                "age_max": item["age_max"],
                "gender": item["gender"],
                "count": item["count"],
                "paid": item["paid"],
                "pay_note": item["pay_note"],
                "start_date": item["start_date"],
                "end_date": item["end_date"],
                "deadline": item["deadline"],
                "description": item["description"],
                "requirements": item["requirements"],
                "status": "open",
            },
        )
