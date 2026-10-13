import datetime

from django import forms
from django.utils.safestring import mark_safe

from honaryaar.catalog import format_jalali_numeric, parse_user_date


class JalaliDateWidget(forms.DateInput):
    template_name = "widgets/jalali_date.html"
    input_type = "text"

    def __init__(self, attrs=None, format=None):
        attrs = {"autocomplete": "off", **(attrs or {})}
        super().__init__(attrs=attrs, format="%Y-%m-%d")

    def format_value(self, value):
        parsed = parse_user_date(value)
        if parsed:
            return parsed.isoformat()
        if isinstance(value, datetime.date):
            return value.isoformat()
        return "" if value in (None, "") else str(value)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        iso = context["widget"].get("value") or ""
        parsed = parse_user_date(iso)
        context["widget"]["jalali"] = format_jalali_numeric(parsed) if parsed else ""
        if parsed:
            context["widget"]["value"] = parsed.isoformat()
        return context

    def render(self, name, value, attrs=None, renderer=None):
        markup = super().render(name, value, attrs, renderer)
        return mark_safe(markup)


class JalaliAdminDateWidget(JalaliDateWidget):
    def __init__(self, attrs=None, format=None):
        from unfold.widgets import DATETIME_CLASSES

        extra = (attrs or {}).get("class", "")
        classes = " ".join([*DATETIME_CLASSES, "jalali-date__text", extra]).strip()
        attrs = {**(attrs or {}), "class": classes}
        super().__init__(attrs=attrs, format=format)


class JalaliSplitDateTimeWidget(forms.MultiWidget):
    template_name = "unfold/widgets/split_datetime.html"

    def __init__(self, attrs=None):
        from unfold.widgets import UnfoldAdminTimeWidget

        widgets = [
            JalaliAdminDateWidget(),
            UnfoldAdminTimeWidget(attrs={"placeholder": "Time"}),
        ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if isinstance(value, datetime.datetime):
            return [value.date(), value.time().replace(microsecond=0)]
        if isinstance(value, datetime.date):
            return [value, None]
        return [None, None]
