from django.apps import AppConfig


class HonaryaarConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "honaryaar"

    def ready(self):
        from . import admin  # noqa: F401
        from .admin_dates import install
        from .error_pages import install as install_error_pages

        install()
        install_error_pages()
        from . import media_signals  # noqa: F401
