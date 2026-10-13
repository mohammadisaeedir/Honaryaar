import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from honaryaar.media_files import BAD_REQUEST, MediaError
from honaryaar.media_service import complete_upload, start_upload


def _payload(request):
    try:
        payload = json.loads(request.body.decode() or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise MediaError(BAD_REQUEST) from None
    if not isinstance(payload, dict):
        raise MediaError(BAD_REQUEST)
    return payload


def _guard(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "برای بارگذاری وارد شوید."}, status=401)
    return None


@require_POST
def media_upload_start(request):
    denied = _guard(request)
    if denied:
        return denied
    try:
        return JsonResponse(start_upload(request.user, _payload(request)))
    except MediaError as exc:
        return JsonResponse({"error": exc.message}, status=exc.status)


@require_POST
def media_upload_complete(request, upload_id):
    denied = _guard(request)
    if denied:
        return denied
    try:
        return JsonResponse(complete_upload(request.user, upload_id))
    except MediaError as exc:
        return JsonResponse({"error": exc.message}, status=exc.status)
