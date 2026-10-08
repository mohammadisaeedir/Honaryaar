"""Show the designed error pages while DEBUG is on.

Django only uses templates/400.html, 403.html, 404.html, and 500.html when
DEBUG is false. Local runserver stays in debug, so a missing URL otherwise
renders the technical page.
"""

import logging

from django.views import debug
from django.views.defaults import bad_request, page_not_found, server_error

logger = logging.getLogger("django.request")

_technical_404 = debug.technical_404_response
_technical_500 = debug.technical_500_response


def install():
    debug.technical_404_response = _not_found
    debug.technical_500_response = _server_error


def _is_admin(request):
    path = request.path_info or "/"
    return path == "/admin" or path.startswith("/admin/")


def _not_found(request, exception):
    if _is_admin(request):
        return _technical_404(request, exception)
    return page_not_found(request, exception)


def _server_error(request, exc_type, exc_value, tb, status_code=500):
    if _is_admin(request):
        return _technical_500(
            request, exc_type, exc_value, tb, status_code=status_code
        )
    if status_code == 400:
        return bad_request(request, exc_value)
    logger.error(
        "Unhandled exception at %s",
        request.path,
        exc_info=(exc_type, exc_value, tb),
    )
    return server_error(request)
