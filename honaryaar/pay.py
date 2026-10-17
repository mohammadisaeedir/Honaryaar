"""Pay type rules shared by the model, the seed, and the public pages."""

import re

PAY_TYPES = ("negotiable", "gift", "box_office", "fixed")
PAY_LABELS = {
    "negotiable": "توافقی",
    "gift": "در حد هدیه",
    "box_office": "درصدی از گیشه",
    "fixed": "مبلغ مشخص",
}
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_PERSIAN = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def classify_legacy_pay(note):
    """Map an old pay note to (pay_type, pay_amount, fell_back_from_fixed)."""
    text = note or ""
    folded = text.translate(_DIGITS)
    if "توافقی" in text:
        return "negotiable", None, False
    if "هدیه" in text:
        return "gift", None, False
    if "درصد" in text or "گیشه" in text:
        return "box_office", None, False
    amount = _tomans(folded)
    looks_fixed = any(word in text for word in ("تومان", "ریال", "مبلغ"))
    if amount is not None:
        return "fixed", amount, False
    if looks_fixed:
        return "gift", None, True
    return "gift", None, False


def _tomans(folded):
    spaced = folded.replace("٬", "").replace(",", "").replace("،", "")
    million = re.search(r"(\d+(?:[./]\d+)?)\s*میلیون", spaced)
    if million:
        value = int(round(float(million.group(1).replace("/", ".")) * 1_000_000))
        return value if value > 0 else None
    thousand = re.search(r"(\d+(?:[./]\d+)?)\s*هزار", spaced)
    if thousand:
        value = int(round(float(thousand.group(1).replace("/", ".")) * 1_000))
        return value if value > 0 else None
    if "تومان" not in folded and "ریال" not in folded:
        return None
    numbers = [int(item) for item in re.findall(r"\d+", spaced)]
    numbers = [item for item in numbers if item > 0]
    if not numbers:
        return None
    amount = max(numbers)
    if "ریال" in folded and "تومان" not in folded:
        amount = amount // 10
    return amount if amount > 0 else None


def pay_problems(paid, pay_type, pay_amount):
    """Field errors for a pay combination. Empty when the combination is valid."""
    pay_type = "" if pay_type is None else str(pay_type).strip()
    amount = _clean_amount(pay_amount)
    problems = {}
    if amount == "bad":
        problems["pay_amount"] = "مبلغ را به تومان وارد کنید."
        return problems
    if not paid:
        if pay_type or amount is not None:
            problems["paid"] = "فرصت بدون دستمزد نوع و مبلغ ندارد."
        return problems
    if pay_type not in PAY_TYPES:
        problems["pay_type"] = "نوع دستمزد را انتخاب کنید."
        return problems
    if pay_type == "fixed":
        if amount is None:
            problems["pay_amount"] = "مبلغ را به تومان وارد کنید."
        elif amount <= 0:
            problems["pay_amount"] = "مبلغ باید بیشتر از صفر باشد."
    elif amount is not None:
        problems["pay_amount"] = "مبلغ فقط برای مبلغ مشخص است."
    return problems


def normalize_pay(paid, pay_type, pay_amount):
    problems = pay_problems(paid, pay_type, pay_amount)
    if problems:
        return bool(paid), "" if pay_type is None else str(pay_type).strip(), _clean_amount(pay_amount), problems
    if not paid:
        return False, "", None, {}
    pay_type = str(pay_type).strip()
    if pay_type != "fixed":
        return True, pay_type, None, {}
    return True, pay_type, _clean_amount(pay_amount), {}


def _clean_amount(pay_amount):
    if pay_amount in (None, ""):
        return None
    if isinstance(pay_amount, bool):
        return "bad"
    try:
        return int(pay_amount)
    except (TypeError, ValueError):
        return "bad"


def pay_label(paid, pay_type, pay_amount):
    if not paid:
        return "بدون دستمزد"
    if pay_type == "fixed" and isinstance(pay_amount, int) and pay_amount > 0:
        return format_tomans(pay_amount)
    return PAY_LABELS.get(pay_type, "")


def format_tomans(amount):
    if amount >= 1_000_000 and amount % 1_000_000 == 0:
        body = f"{_persian(amount // 1_000_000)} میلیون"
    else:
        body = _persian(f"{amount:,}".replace(",", "٬"))
    return f"{body} تومان"


def _persian(value):
    return str(value).translate(_PERSIAN)
