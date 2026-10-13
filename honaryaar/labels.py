from django.utils.html import format_html

APPLICATION_LABELS = {
    "submitted": "ارسال‌شده",
    "rejected": "رد شده",
    "shortlisted": "فهرست کوتاه",
    "conversation": "گفتگو",
    "matched": "مچ",
}

INVITE_LABELS = {
    "sent": "در انتظار پاسخ",
    "declined": "رد شده",
    "accepted": "پذیرفته",
}

MATCH_LABELS = {
    "active": "فعال",
    "closed": "بسته",
}

STATUS_LABELS = {
    "indexed": "از منبع عمومی",
    "claimed": "در اختیار شما",
}

CHIP_LABELS = {
    **APPLICATION_LABELS,
    **INVITE_LABELS,
    **MATCH_LABELS,
    "indexed": "از منبع عمومی",
    "claimed": "در اختیار خود هنرمند",
    "draft": "پیش‌نویس",
    "casting": "در حال جذب",
    "completed": "اتمام",
    "open": "باز",
    "answered": "پاسخ‌داده‌شده",
    "closed": "بسته",
}

STATUS_TONE = {
    "rejected": "muted",
    "declined": "muted",
    "closed": "muted",
    "draft": "progress",
    "casting": "progress",
    "indexed": "progress",
    "open": "progress",
    "submitted": "progress",
    "shortlisted": "progress",
    "conversation": "progress",
    "sent": "progress",
    "active": "progress",
    "answered": "progress",
    "completed": "done",
    "claimed": "done",
    "matched": "done",
    "accepted": "done",
}

CHIP_COLORS = {
    "muted": ("#eef0f3", "#5c6570"),
    "progress": ("#e7f2fc", "#2a6fad"),
    "done": ("#e6f6ee", "#1e7a4c"),
}

MEDIA_LABELS = {
    "photo": "عکس",
    "video": "ویدیو",
    "audio": "صوت",
}

COLLABORATION_TYPES = [
    ("project_hire", "استخدام پروژه‌ای"),
    ("contractor", "پیمانکاری"),
    ("salary", "دستمزدی"),
    ("daily", "روزمزد"),
    ("hourly", "ساعتی"),
    ("session", "جلسه‌ای"),
    ("percentage", "درصدی"),
    ("partnership", "مشارکتی"),
    ("equity", "سرمایه‌گذاری در ازای سهم"),
    ("honorary", "افتخاری"),
    ("internship", "کارآموزی"),
    ("volunteer", "داوطلبانه"),
    ("long_term", "همکاری بلندمدت"),
    ("temporary", "همکاری موقت"),
]

EXPERIENCE_LEVELS = [
    ("beginner", "مبتدی"),
    ("intermediate", "متوسط"),
    ("professional", "حرفه‌ای"),
]

SPECIAL_CONDITIONS = [
    ("urgent", "فوری"),
    ("no_test", "بدون تست"),
    ("test_required", "تست الزامی"),
    ("paid", "دارای پرداخت"),
    ("student", "پروژه دانشجویی"),
    ("sponsored", "اسپانسری"),
]

SKILL_LEVEL_LABELS = {
    1: "۱",
    2: "۲",
    3: "۳",
    4: "۴",
    5: "۵",
}


def status_chip_html(code, label):
    tone = STATUS_TONE.get(code, "progress")
    background, color = CHIP_COLORS[tone]
    return format_html(
        '<span style="display:inline-flex;align-items:center;min-height:22px;padding:0 8px;border-radius:999px;background:{};color:{};font-size:12px;font-weight:700;line-height:16px;white-space:nowrap;">{}</span>',
        background,
        color,
        label,
    )
