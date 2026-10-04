import re
import secrets

from django.contrib.auth.models import User

from ejranow.models import Profile, ProfileStatus

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_PHONE = re.compile(r"^09\d{9}$")


def normalize_phone(raw):
    text = (raw or "").strip().translate(_DIGITS)
    text = re.sub(r"[\s\-()]", "", text)
    if text.startswith("+98"):
        text = "0" + text[3:]
    elif text.startswith("0098"):
        text = "0" + text[4:]
    elif text.startswith("98") and len(text) == 12:
        text = "0" + text[2:]
    elif len(text) == 10 and text.startswith("9"):
        text = "0" + text
    if _PHONE.match(text):
        return text
    return ""


def code_matches(phone, raw):
    """Temporary check until an SMS provider is connected."""
    code = (raw or "").strip().translate(_DIGITS)
    return bool(phone) and code == phone[-4:]


def _new_slug():
    for _ in range(5):
        slug = f"u-{secrets.token_hex(4)}"
        if not Profile.objects.filter(slug=slug).exists():
            return slug
    return f"u-{secrets.token_hex(8)}"


def user_for_phone(phone):
    user, created = User.objects.get_or_create(
        username=phone,
        defaults={"is_staff": False, "is_superuser": False},
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    ensure_profile(user)
    return user


def current_profile(user):
    if not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.profile
    except Profile.DoesNotExist:
        return None


def ready_profile(user):
    profile = current_profile(user)
    if profile and profile.first_name and profile.last_name:
        return profile
    return None


def ensure_profile(user):
    try:
        return user.profile
    except Profile.DoesNotExist:
        return Profile.objects.create(
            user=user,
            slug=_new_slug(),
            status=ProfileStatus.CLAIMED,
        )
