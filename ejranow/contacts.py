"""Normalize a contact value. No model imports."""

import re
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_TELEGRAM_NAME = re.compile(r"^[A-Za-z0-9_]+$")
_INSTAGRAM_HANDLE = re.compile(r"^[A-Za-z0-9._]{1,30}$")
_TELEGRAM_MARKERS = (
    "https://www.t.me/",
    "http://www.t.me/",
    "https://t.me/",
    "http://t.me/",
    "www.t.me/",
    "t.me/",
)
_INSTAGRAM_MARKERS = (
    "https://www.instagram.com/",
    "http://www.instagram.com/",
    "https://instagram.com/",
    "http://instagram.com/",
    "www.instagram.com/",
    "instagram.com/",
)
_PLATFORM_BASES = {
    "youtube": ("youtube.com", "youtu.be"),
    "aparat": ("aparat.com",),
    "twitch": ("twitch.tv",),
    "spotify": ("spotify.com", "spotify.link", "open.spotify.com"),
    "soundcloud": ("soundcloud.com",),
    "imdb": ("imdb.com",),
    "linkedin": ("linkedin.com",),
    "pinterest": ("pinterest.com", "pin.it"),
}
_PLATFORM_BRAND = {
    "youtube": "youtube",
    "aparat": "aparat",
    "twitch": "twitch",
    "spotify": "spotify",
    "soundcloud": "soundcloud",
    "imdb": "imdb",
    "linkedin": "linkedin",
    "pinterest": "pinterest",
}
_PLATFORM_PREFIX = {
    "youtube": "https://youtube.com/@",
    "aparat": "https://aparat.com/",
    "twitch": "https://twitch.tv/",
    "spotify": "https://open.spotify.com/artist/",
    "soundcloud": "https://soundcloud.com/",
    "imdb": "https://imdb.com/name/",
    "linkedin": "https://linkedin.com/in/",
    "pinterest": "https://pinterest.com/",
}


def normalize_contact(kind, raw):
    text = (raw or "").strip()
    if not text:
        raise ValidationError("Enter a value.")
    if kind in {"phone", "whatsapp"}:
        return _normalize_phone(text, kind)
    if kind == "telegram":
        return _normalize_handle(text, _TELEGRAM_MARKERS, _TELEGRAM_NAME, "Enter a Telegram username.")
    if kind == "instagram":
        return _normalize_handle(text, _INSTAGRAM_MARKERS, _INSTAGRAM_HANDLE, "Enter an Instagram handle.")
    if kind == "email":
        lowered = text.lower()
        try:
            validate_email(lowered)
        except ValidationError as exc:
            raise ValidationError("Enter a valid email address.") from exc
        return lowered
    if kind == "website":
        return _normalize_website(text)
    if kind in _PLATFORM_BASES:
        return _normalize_platform(text, kind)
    raise ValidationError("Unknown contact kind.")


def _normalize_phone(text, kind):
    from ejranow.accounts import normalize_phone

    mobile = normalize_phone(text)
    if mobile:
        return mobile
    if kind == "phone":
        landline = _landline(text)
        if landline:
            return landline
    if kind == "whatsapp":
        raise ValidationError("Enter a mobile number like 09123456789.")
    raise ValidationError("Enter a phone number.")


def _landline(raw):
    text = (raw or "").strip().translate(_DIGITS)
    lowered = text.lower()
    if lowered.startswith("tel:"):
        text = text[4:]
    text = re.sub(r"[\s\-()]", "", text)
    if text.startswith("+98"):
        text = "0" + text[3:]
    elif text.startswith("0098"):
        text = "0" + text[4:]
    if text.isdigit() and text.startswith("0") and 10 <= len(text) <= 11:
        return text
    return ""


def _normalize_handle(text, markers, pattern, message):
    cleaned = text.split("#", 1)[0].split("?", 1)[0].strip().rstrip("/")
    lowered = cleaned.lower()
    for marker in markers:
        if lowered.startswith(marker):
            cleaned = cleaned[len(marker):]
            break
    handle = cleaned.strip().lstrip("@").split("/", 1)[0]
    if not pattern.fullmatch(handle):
        raise ValidationError(message)
    return handle


def _normalize_website(text):
    candidate = _prefix_https(text)
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError("Enter an http or https address.")
    return candidate


def _normalize_platform(text, kind):
    bases = _PLATFORM_BASES[kind]
    brand = _PLATFORM_BRAND[kind]
    candidate = _prefix_platform(text, bases, brand, _PLATFORM_PREFIX[kind])
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not _host_matches(parsed.hostname, bases, brand):
        raise ValidationError("Enter an address on this platform.")
    return candidate


def _prefix_https(text):
    if "://" in text:
        return text
    if ":" in text.split("/", 1)[0]:
        return text
    return "https://" + text


def _prefix_platform(text, bases, brand, bare_prefix):
    if "://" in text:
        return text
    if ":" in text.split("/", 1)[0]:
        return text
    host = text.split("/", 1)[0]
    if _host_matches(host, bases, brand):
        return "https://" + text
    if "/" not in text:
        return bare_prefix + text.lstrip("@")
    return "https://" + text


def _host_matches(hostname, bases, brand):
    host = (hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if any(host == base or host.endswith("." + base) for base in bases):
        return True
    labels = host.split(".")
    for index, label in enumerate(labels):
        if label == brand and _country_tail(labels[index + 1:]):
            return True
    return False


def _country_tail(labels):
    if len(labels) == 1 and re.fullmatch(r"[a-z]{2}", labels[0]):
        return True
    if len(labels) == 2 and all(re.fullmatch(r"[a-z]{2}", label) for label in labels):
        return True
    if len(labels) == 2 and labels[0] == "com" and re.fullmatch(r"[a-z]{2}", labels[1]):
        return True
    return False
