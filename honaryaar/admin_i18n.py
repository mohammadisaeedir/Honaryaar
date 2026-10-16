from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _


def _lazy(value):
    if isinstance(value, Promise):
        return value
    return _(str(value))


def translate_labels():
    from django.apps import apps

    for model in apps.get_app_config("honaryaar").get_models():
        opts = model._meta
        opts.verbose_name = _lazy(opts.verbose_name)
        opts.verbose_name_plural = _lazy(opts.verbose_name_plural)
        for field in (*opts.fields, *opts.many_to_many):
            if field.verbose_name:
                field.verbose_name = _lazy(field.verbose_name)
            if field.help_text:
                field.help_text = _lazy(field.help_text)
            if field.choices:
                field.choices = [(value, _lazy(label)) for value, label in field.choices]
