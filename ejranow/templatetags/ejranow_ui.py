from datetime import date, datetime

from django import template
from django.utils import timezone

from ejranow import catalog
from ejranow.accounts import current_profile
from ejranow.labels import (
    APPLICATION_LABELS,
    INVITE_LABELS,
    MATCH_LABELS,
    MEDIA_LABELS,
    SKILL_LEVEL_LABELS,
    STATUS_LABELS,
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


@register.filter
def media_label(value):
    return MEDIA_LABELS.get(value, value)


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
def profile_first_name(user):
    profile = current_profile(user)
    if profile is None:
        return ""
    return profile.first_name or ""


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
        else:
            picked = next((option for option in group["options"] if option["selected"] and option["value"]), None)
            if picked is None:
                continue
            label = picked["label"]
        query = request.GET.copy()
        query.pop(group["name"], None)
        encoded = query.urlencode()
        items.append({"label": label, "href": f"?{encoded}" if encoded else request.path})
    return items
