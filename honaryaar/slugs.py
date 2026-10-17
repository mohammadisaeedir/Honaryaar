"""Readable ASCII slugs for Persian and Latin titles.

The result is at most 40 characters. A collision with the target model gets
-2, -3, and so on. Studio-style random slugs (p- or o- plus hex) are never
returned.
"""

import re

_MAX = 40
_RANDOM = re.compile(r"^[po]-[0-9a-f]{8,16}$")
_ASCII = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

_LETTERS = {
    "ا": "a",
    "آ": "a",
    "أ": "a",
    "إ": "a",
    "ٱ": "a",
    "ب": "b",
    "پ": "p",
    "ت": "t",
    "ط": "t",
    "ث": "s",
    "س": "s",
    "ص": "s",
    "ج": "j",
    "چ": "ch",
    "ح": "h",
    "ه": "h",
    "ة": "h",
    "ۀ": "h",
    "خ": "kh",
    "د": "d",
    "ذ": "z",
    "ز": "z",
    "ض": "z",
    "ظ": "z",
    "ر": "r",
    "ژ": "zh",
    "ش": "sh",
    "ع": "a",
    "غ": "gh",
    "ق": "gh",
    "ف": "f",
    "ک": "k",
    "ك": "k",
    "گ": "g",
    "ل": "l",
    "م": "m",
    "ن": "n",
    "و": "v",
    "ؤ": "v",
    "ی": "i",
    "ي": "i",
    "ئ": "i",
    "ى": "i",
}
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_WORDS = {
    "فراخوان": "call",
    "بازیگر": "actor",
    "نمایش": "play",
    "فیلم": "film",
    "کوتاه": "short",
    "سریال": "series",
}


def _word(token):
    key = token.replace("\u200c", "").replace("\u200d", "")
    key = key.replace("ي", "ی").replace("ك", "ک")
    return _WORDS.get(key)


def _piece(token):
    known = _word(token)
    if known:
        return known
    chars = []
    for char in token.translate(_DIGITS):
        lower = char.lower()
        if "a" <= lower <= "z" or lower.isdigit():
            chars.append(lower)
        elif char in _LETTERS:
            chars.append(_LETTERS[char])
    return "".join(chars)


def slugify(title, *, fallback):
    text = (title or "").replace("\u200c", " ").replace("\u200d", " ")
    parts = []
    token = []

    def flush():
        if not token:
            return
        piece = _piece("".join(token))
        token.clear()
        if piece:
            parts.append(piece)

    for char in text:
        if char.isspace() or char in "-_–—/\\.,،؛:|+'\"()[]":
            flush()
        else:
            token.append(char)
    flush()
    slug = _fit("-".join(parts))
    if not slug:
        slug = fallback
    return _avoid(slug, fallback)


def unique_slug(model, title, *, fallback, exclude_pk=None):
    return _unique(model, slugify(title, fallback=fallback), fallback=fallback, exclude_pk=exclude_pk)


def opportunity_slug(project_slug, *, role_slug="", role_title="", model, exclude_pk=None):
    role = (role_slug or "").strip().lower()
    if role and _ASCII.fullmatch(role) is None:
        role = slugify(role, fallback="")
    if not role:
        role = slugify(role_title, fallback="")
    if not role:
        base = "opportunity"
    else:
        prefix = _fit(project_slug or "") or "project"
        room = _MAX - len(role) - 1
        if room < 1:
            role = role[: _MAX - 2].rstrip("-")
            room = _MAX - len(role) - 1
        prefix = (prefix[:room].rstrip("-") or "project")
        base = _fit(f"{prefix}-{role}")
    return _unique(model, _avoid(base, "opportunity"), fallback="opportunity", exclude_pk=exclude_pk)


def _fit(slug):
    slug = re.sub(r"-{2,}", "-", slug or "").strip("-")
    if len(slug) > _MAX:
        slug = slug[:_MAX].rstrip("-")
    return slug


def _avoid(slug, fallback):
    if _RANDOM.match(slug):
        slug = _fit(f"{fallback}-{slug}")
    if not slug or _RANDOM.match(slug):
        return fallback
    return slug


def _unique(model, base, *, fallback, exclude_pk):
    base = _avoid(_fit(base) or fallback, fallback)
    slug = base
    number = 2
    while _taken(model, slug, exclude_pk):
        suffix = f"-{number}"
        trimmed = _fit(base[: _MAX - len(suffix)])
        slug = _avoid(f"{trimmed}{suffix}", fallback)
        if _taken(model, slug, exclude_pk) and slug == fallback:
            slug = _fit(f"{fallback}{suffix}")
        number += 1
    return slug


def _taken(model, slug, exclude_pk):
    rows = model.objects.filter(slug=slug)
    if exclude_pk:
        rows = rows.exclude(pk=exclude_pk)
    return rows.exists()
