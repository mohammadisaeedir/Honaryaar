"""In-app notification inbox and push device registration."""

from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from honaryaar.fcm import web_config
from honaryaar.models import InAppNotification, PushDevice
from honaryaar.notifications import register_push_device


def _safe_next(value: str, fallback: str = "/me/notifications/") -> str:
    if value.startswith("/") and not value.startswith("//"):
        return value
    return fallback


@login_required
def my_notifications(request):
    rows = list(
        InAppNotification.objects.filter(user=request.user).order_by("-created_at", "-pk")[:100]
    )
    unread = sum(1 for row in rows if not row.is_read)
    return render(
        request,
        "pages/me_notifications.html",
        {
            "page_title": "اعلان‌ها",
            "notifications": rows,
            "unread_count": unread,
        },
    )


@login_required
@require_POST
def notification_open(request, pk):
    item = get_object_or_404(InAppNotification, pk=pk, user=request.user)
    if not item.is_read:
        item.is_read = True
        item.read_at = timezone.now()
        item.save(update_fields=["is_read", "read_at"])
    target = _safe_next(item.deep_link or "", "/me/notifications/")
    return redirect(target)


@login_required
@require_POST
def notifications_read_all(request):
    InAppNotification.objects.filter(user=request.user, is_read=False).update(
        is_read=True,
        read_at=timezone.now(),
    )
    return redirect("me-notifications")


@login_required
@require_GET
def push_config(request):
    config = web_config()
    return JsonResponse(
        {
            "enabled": bool(config),
            "firebase": config or {},
        }
    )


@login_required
@require_http_methods(["POST", "DELETE"])
def push_devices(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    token = (payload.get("token") or "").strip()
    if not token:
        return JsonResponse({"ok": False, "error": "token_required"}, status=400)

    if request.method == "DELETE":
        updated = PushDevice.objects.filter(user=request.user, token=token).update(is_active=False)
        return JsonResponse({"ok": True, "deactivated": updated})

    platform = (payload.get("platform") or PushDevice.Platform.WEB).strip()
    try:
        device = register_push_device(request.user, token, platform=platform)
    except ValueError:
        return JsonResponse({"ok": False, "error": "token_required"}, status=400)
    return JsonResponse(
        {
            "ok": True,
            "id": device.pk,
            "platform": device.platform,
        }
    )


@login_required
@require_POST
def notification_mark_read(request, pk):
    item = get_object_or_404(InAppNotification, pk=pk, user=request.user)
    if not item.is_read:
        item.is_read = True
        item.read_at = timezone.now()
        item.save(update_fields=["is_read", "read_at"])
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        unread = InAppNotification.objects.filter(user=request.user, is_read=False).count()
        return JsonResponse({"ok": True, "unread": unread})
    raise Http404
