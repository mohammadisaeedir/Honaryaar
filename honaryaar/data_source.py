import os
from contextvars import ContextVar

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

_preview = ContextVar("production_preview", default=False)
SESSION_KEY = "data_source"


def preview_active():
    return _preview.get()


def production_configured():
    return "production" in settings.DATABASES


def switch_visible(request):
    user = getattr(request, "user", None)
    return bool(
        user
        and user.is_authenticated
        and user.is_superuser
        and os.environ.get("VERCEL") != "1"
    )


class ProductionPreviewRouter:
    def db_for_read(self, model, **hints):
        return _route(model)

    def db_for_write(self, model, **hints):
        return _route(model)

    def allow_relation(self, obj1, obj2, **hints):
        return None


def _route(model):
    if not preview_active():
        return None
    if model._meta.app_label == "sessions":
        return "default"
    if not production_configured():
        return None
    return "production"


class ProductionPreviewMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        active = (
            switch_visible(request)
            and request.session.get(SESSION_KEY) == "production"
            and production_configured()
        )
        token = _preview.set(active)
        try:
            return self.get_response(request)
        finally:
            _preview.reset(token)


@require_POST
def switch_data_source(request):
    if not switch_visible(request):
        raise PermissionDenied
    source = request.POST.get("source")
    if source == "production":
        if production_configured():
            request.session[SESSION_KEY] = "production"
        else:
            messages.error(request, "Add PROD_DATABASE_URL to .env.local and restart.")
    else:
        request.session.pop(SESSION_KEY, None)
    return HttpResponseRedirect(_next_url(request))


def _next_url(request):
    target = request.POST.get("next") or ""
    if url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return target
    return reverse("admin:index")
