from datetime import date, datetime

from django import template
from django.utils import timezone

from ejranow import catalog
from ejranow.accounts import current_profile
from ejranow.labels import (
    APPLICATION_LABELS,
    CHIP_LABELS,
    INVITE_LABELS,
    MATCH_LABELS,
    MEDIA_LABELS,
    SKILL_LEVEL_LABELS,
    STATUS_LABELS,
    STATUS_TONE,
)

register = template.Library()


@register.filter
def jalali(value):
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return catalog.format_datetime(value)
    if isinstance(value, date):
        return catalog.format_date(value)
    return value


@register.filter
def phone_fa(value):
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) == 11:
        text = f"{digits[:4]} {digits[4:7]} {digits[7:]}"
    else:
        text = digits or str(value or "")
    return text.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


@register.filter
def application_label(value):
    return APPLICATION_LABELS.get(value, value)


@register.filter
def invite_label(value):
    return INVITE_LABELS.get(value, value)


@register.filter
def match_label(value):
    return MATCH_LABELS.get(value, value)


@register.filter
def status_label(value):
    return STATUS_LABELS.get(value, value)


@register.inclusion_tag("components/status_chip.html")
def status_chip(code, label=""):
    code = "" if code is None else str(code)
    return {
        "show": bool(code),
        "label": label or CHIP_LABELS.get(code, code),
        "tone": STATUS_TONE.get(code, "progress"),
    }


@register.filter
def media_label(value):
    return MEDIA_LABELS.get(value, value)


@register.simple_tag
def media_src(key, public=False, public_acl=False, fallback="", kind="photo"):
    from ejranow.media_service import url_for_key

    chosen = key or fallback or ""
    return url_for_key(
        chosen,
        public=str(public).lower() in {"1", "true", "yes", "on"},
        public_acl=str(public_acl).lower() in {"1", "true", "yes", "on"},
        kind=kind or "photo",
    )


@register.simple_tag
def media_limit(kind):
    from django.conf import settings

    return {
        "photo": settings.MEDIA_MAX_IMAGE_BYTES,
        "video": settings.MEDIA_MAX_VIDEO_BYTES,
        "audio": settings.MEDIA_MAX_AUDIO_BYTES,
    }.get(kind, 0)


@register.simple_tag
def media_start_url():
    from django.urls import reverse

    return reverse("media-upload-start")


@register.filter
def skill_level_label(value):
    try:
        return SKILL_LEVEL_LABELS.get(int(value), value)
    except (TypeError, ValueError):
        return value


@register.filter
def contains_id(values, item):
    if not values:
        return False
    text = str(item)
    return text in {str(value) for value in values}


@register.filter
def gender_label(value):
    return catalog.gender_label(value)


@register.filter
def collaboration_label(value):
    return catalog.collaboration_label(value)


@register.filter
def experience_label(value):
    return catalog.experience_label(value)


@register.filter
def special_label(value):
    return catalog.special_label(value)


@register.filter
def role_title(slug):
    return catalog.role_title(slug)


@register.filter
def art_title(slug):
    return catalog.art_title(slug)


@register.filter
def age_label(item):
    return catalog.age_label(item)


@register.filter
def project_of(slug):
    return catalog.project_by_slug(slug)


@register.simple_tag
def account_photo(user):
    from ejranow.media_service import url_for_key

    profile = current_profile(user)
    if profile is None:
        return ""
    key = profile.list_thumb.name or profile.list_image.name
    if not key:
        return ""
    return url_for_key(key, public=True, public_acl=bool(profile.list_public_acl), kind="photo")


@register.simple_tag
def account_name(user):
    profile = current_profile(user)
    if profile is not None:
        shown = profile.public_name()
        if shown and shown != profile.slug and shown != getattr(profile.user, "username", ""):
            return shown
    full = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
    return full or "کاربر هنریار"


@register.simple_tag
def profile_first_name(user):
    if not getattr(user, "is_authenticated", False):
        return ""
    return user.first_name or ""


@register.simple_tag
def query_string(request, **kwargs):
    params = request.GET.copy()
    for key, value in kwargs.items():
        if value is None or value == "":
            params.pop(key, None)
        else:
            params[key] = value
    encoded = params.urlencode()
    return f"?{encoded}" if encoded else request.path


@register.simple_tag(takes_context=True)
def applied_filters(context, groups):
    request = context["request"]
    items = []
    for group in groups:
        if group["kind"] == "text":
            if not group["value"]:
                continue
            label = group["value"]
        elif group["kind"] == "age":
            if not group["selected"]:
                continue
            query = request.GET.copy()
            query.pop("age_from", None)
            query.pop("age_to", None)
            encoded = query.urlencode()
            items.append({"label": f"{group['start']} تا {group['end']}", "href": f"?{encoded}" if encoded else request.path})
            continue
        else:
            picked = [option for option in group["options"] if option["selected"] and option["value"]]
            for option in picked:
                query = request.GET.copy()
                values = [item for item in query.getlist(group["name"]) if item != option["value"]]
                query.setlist(group["name"], values)
                encoded = query.urlencode()
                items.append({"label": option["label"], "href": f"?{encoded}" if encoded else request.path})
            continue
        query = request.GET.copy()
        query.pop(group["name"], None)
        encoded = query.urlencode()
        items.append({"label": label, "href": f"?{encoded}" if encoded else request.path})
    return items
