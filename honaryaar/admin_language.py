from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

SESSION_KEY = "admin_lang"


class AdminLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        active = request.path.startswith("/admin") and request.session.get(SESSION_KEY) == "fa"
        if active:
            translation.activate("fa")
            request.LANGUAGE_CODE = translation.get_language()
        try:
            return self.get_response(request)
        finally:
            if active:
                translation.deactivate()


@require_POST
def switch_admin_language(request):
    if request.POST.get("language") == "fa":
        request.session[SESSION_KEY] = "fa"
    else:
        request.session.pop(SESSION_KEY, None)
    return HttpResponseRedirect(_next_url(request))


def _next_url(request):
    target = request.POST.get("next") or ""
    if url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}) and target.startswith("/admin"):
        return target
    return reverse("admin:index")
