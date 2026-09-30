from django.apps import AppConfig


class EjranowConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ejranow"

    def ready(self):
        from . import admin  # noqa: F401
