import calendar
import datetime

from django.contrib.admin.templatetags.admin_list import date_hierarchy as _date_hierarchy
from django.contrib.admin.templatetags.base import InclusionAdminNode
from django.db import models
from django.utils import timezone
from django.utils.text import capfirst
from django.utils.translation import gettext as _

from ejranow.catalog import format_date, format_datetime, format_jalali_period, format_time


def _local(value):
    if isinstance(value, datetime.datetime) and timezone.is_aware(value):
        return timezone.localtime(value)
    return value


def _persian_value(value):
    value = _local(value)
    if isinstance(value, datetime.datetime):
        return format_datetime(value)
    if isinstance(value, datetime.date):
        return format_date(value)
    if isinstance(value, datetime.time):
        return format_time(value)
    return None


def _wrap_display_for_value(original):
    def display_for_value(value, empty_value_display, boolean=False):
        if not boolean:
            formatted = _persian_value(value)
            if formatted is not None:
                return formatted
        return original(value, empty_value_display, boolean)

    return display_for_value


def _wrap_display_for_field(original):
    def display_for_field(value, field, empty_value_display):
        if value not in (None, ""):
            if isinstance(field, models.DateTimeField):
                return format_datetime(_local(value))
            if isinstance(field, models.DateField):
                return format_date(value)
            if isinstance(field, models.TimeField):
                return format_time(value)
        return original(value, field, empty_value_display)

    return display_for_field


def _month_bounds(year, month):
    last_day = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, 1), datetime.date(year, month, last_day)


def _year_label(year):
    return format_jalali_period(datetime.date(year, 1, 1), datetime.date(year, 12, 31))


def _month_label(year, month):
    return format_jalali_period(*_month_bounds(year, month))


def _query_value(link, field_name, part):
    marker = f"{field_name}__{part}="
    if marker not in link:
        return None
    return link.split(marker, 1)[1].split("&", 1)[0]


def _choice_title(choice, field_name, selected):
    link = choice.get("link") or ""
    year = _query_value(link, field_name, "year") or selected[0]
    month = _query_value(link, field_name, "month") or selected[1]
    day = _query_value(link, field_name, "day") or (selected[2] if not link else None)
    if year and month and day:
        return format_date(datetime.date(int(year), int(month), int(day)))
    if year and month:
        return _month_label(int(year), int(month))
    if year:
        return _year_label(int(year))
    return choice.get("title")


def date_hierarchy(cl):
    result = _date_hierarchy(cl)
    if not result:
        return result
    field_name = cl.date_hierarchy
    year = cl.params.get(f"{field_name}__year")
    month = cl.params.get(f"{field_name}__month")
    day = cl.params.get(f"{field_name}__day")
    back = result.get("back")
    if back and back.get("title") and back["title"] != capfirst(_("All dates")):
        if year and month and day:
            back["title"] = _month_label(int(year), int(month))
        elif year and month:
            back["title"] = _year_label(int(year))
        elif year:
            back["title"] = capfirst(_("All dates"))
    selected = (year, month, day)
    result["choices"] = [
        {**choice, "title": _choice_title(choice, field_name, selected)}
        for choice in result.get("choices") or []
    ]
    return result


def _install_date_hierarchy():
    from django.contrib.admin.templatetags import admin_list

    def date_hierarchy_tag(parser, token):
        return InclusionAdminNode(
            "date_hierarchy",
            parser,
            token,
            func=date_hierarchy,
            template_name="date_hierarchy.html",
            takes_context=False,
        )

    admin_list.register.tag(name="date_hierarchy", compile_function=date_hierarchy_tag)
    admin_list.date_hierarchy = date_hierarchy


def install():
    import django.contrib.admin.helpers as admin_helpers
    import django.contrib.admin.templatetags.admin_list as admin_list
    import django.contrib.admin.utils as admin_utils
    import unfold.fields
    import unfold.sections
    import unfold.templatetags.unfold_list as unfold_list
    import unfold.utils as unfold_utils

    unfold_utils.display_for_value = _wrap_display_for_value(unfold_utils.display_for_value)
    unfold_utils.display_for_field = _wrap_display_for_field(unfold_utils.display_for_field)
    unfold_list.display_for_value = unfold_utils.display_for_value
    unfold_list.display_for_field = unfold_utils.display_for_field
    unfold.fields.display_for_field = unfold_utils.display_for_field
    unfold.sections.display_for_field = unfold_utils.display_for_field

    admin_utils.display_for_value = _wrap_display_for_value(admin_utils.display_for_value)
    admin_utils.display_for_field = _wrap_display_for_field(admin_utils.display_for_field)
    admin_list.display_for_value = admin_utils.display_for_value
    admin_list.display_for_field = admin_utils.display_for_field
    admin_helpers.display_for_field = admin_utils.display_for_field
    _install_date_hierarchy()
