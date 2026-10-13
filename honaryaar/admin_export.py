import csv
import datetime

from django.db.models.fields.files import FieldFile
from django.http import HttpResponse
from django.utils import timezone


def csv_response(queryset):
    model = queryset.model
    fields = _export_fields(model)
    forward = [field.name for field in fields if field.is_relation and field.many_to_one]
    many = [field.name for field in fields if field.many_to_many]
    if forward:
        queryset = queryset.select_related(*forward)
    if many:
        queryset = queryset.prefetch_related(*many)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{model._meta.model_name}.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow([str(field.verbose_name) for field in fields])
    for obj in queryset:
        writer.writerow([_cell(obj, field) for field in fields])
    return response


def _export_fields(model):
    fields = [field for field in model._meta.fields if field.name != "password"]
    fields.extend(model._meta.many_to_many)
    return fields


def _cell(obj, field):
    if field.many_to_many:
        return _plain(", ".join(str(item) for item in getattr(obj, field.name).all()))
    if field.is_relation:
        related = getattr(obj, field.name)
        return "" if related is None else _plain(related)
    value = field.value_from_object(obj)
    if value in (None, ""):
        return ""
    if isinstance(value, FieldFile):
        return value.name or ""
    if isinstance(value, (list, tuple)):
        return _plain(", ".join(str(item) for item in value))
    if isinstance(value, dict):
        return _plain(str(value))
    if isinstance(value, datetime.datetime) and timezone.is_aware(value):
        value = timezone.localtime(value).replace(tzinfo=None)
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, bool):
        return "yes" if value else "no"
    return _plain(value)


def _plain(value):
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text
