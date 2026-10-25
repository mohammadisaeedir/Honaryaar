import re
import secrets
import string

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction

from honaryaar.models import Profile, ProfileStatus

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_PHONE = re.compile(r"^09\d{9}$")
_USERNAME_ALPHABET = string.ascii_lowercase + string.digits


def display_phone(phone):
    return (phone or "").translate(_PERSIAN_DIGITS)


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


def _username_is_free(username):
    return not User.objects.filter(username=username).exists() and not Profile.objects.filter(slug=username).exists()


def _new_username():
    for _ in range(10):
        username = "".join(secrets.choice(_USERNAME_ALPHABET) for _ in range(5))
        if _username_is_free(username):
            return username
    raise RuntimeError("Could not allocate a unique username.")


def _user_by_mobile(phone):
    profile = Profile.objects.select_related("user").filter(mobile=phone).first()
    if profile is None:
        return None
    return profile.user


def user_for_phone(phone):
    """Find or create the account for a phone number entered at registration.

    The phone is stored on the profile. The username is a separate unique handle,
    and the profile address uses that same handle.
    """
    existing = _user_by_mobile(phone)
    if existing is not None:
        return existing
    username = _new_username()
    try:
        with transaction.atomic():
            user = User(username=username, is_staff=False, is_superuser=False)
            user.set_unusable_password()
            user.save()
            Profile.objects.create(
                user=user,
                slug=username,
                mobile=phone,
                status=ProfileStatus.CLAIMED,
            )
    except IntegrityError:
        existing = _user_by_mobile(phone)
        if existing is not None:
            return existing
        raise
    return user


def sync_profile_slug(sender, instance, **kwargs):
    Profile.objects.filter(user_id=instance.pk).exclude(slug=instance.username).update(slug=instance.username)


def connect_user_signals():
    from django.contrib.auth import get_user_model
    from django.db.models.signals import post_save

    post_save.connect(
        sync_profile_slug,
        sender=get_user_model(),
        dispatch_uid="honaryaar.profile_slug_matches_username",
    )


def current_profile(user):
    if not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.profile
    except Profile.DoesNotExist:
        return None


def ready_profile(user):
    profile = current_profile(user)
    if profile and user.first_name and user.last_name:
        return profile
    return None


def professional_profile_ready(user):
    profile = ready_profile(user)
    if profile is None:
        return False
    return profile.profile_roles.exists()


def ensure_profile(user):
    """Artist account for someone using the public site. Staff can stay without one."""
    try:
        return user.profile
    except Profile.DoesNotExist:
        if getattr(user, "is_staff", False):
            return None
        return Profile.objects.create(
            user=user,
            slug=user.username,
            status=ProfileStatus.CLAIMED,
        )
