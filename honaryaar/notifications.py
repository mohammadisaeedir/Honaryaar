"""Outbound notifications: template render, push delivery, and audit logging."""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.template import Context, Engine, TemplateSyntaxError
from django.utils import timezone

from honaryaar.models import (
    InAppNotification,
    NotificationChannel,
    NotificationLog,
    NotificationLogStatus,
    NotificationTemplate,
    PushDevice,
)

logger = logging.getLogger(__name__)

_ENGINE = Engine(debug=False, string_if_invalid="")

# Event codes used by the app. Keep in sync with seeded NotificationTemplate rows.
CODE_INVITE_SENT = "invite.sent"
CODE_INVITE_REPLIED = "invite.replied"
CODE_APPLICATION_SUBMITTED = "application.submitted"
CODE_APPLICATION_STATUS = "application.status_changed"
CODE_COLLABORATION_STARTED = "collaboration.started"
CODE_PROJECT_MEMBER_INVITED = "project.member_invited"


def render_string(source: str, context: dict[str, Any] | None = None) -> str:
    if not source:
        return ""
    try:
        return _ENGINE.from_string(source).render(Context(context or {}))
    except TemplateSyntaxError:
        logger.exception("notification template render failed")
        return source


def profile_label(profile) -> str:
    if profile is None:
        return ""
    try:
        return profile.public_name()
    except Exception:
        return str(profile)


def get_template(code: str, channel: str = NotificationChannel.PUSH) -> NotificationTemplate | None:
    return (
        NotificationTemplate.objects.filter(code=code, channel=channel, is_active=True)
        .order_by("pk")
        .first()
    )


def _related_fields(related):
    if related is None or getattr(related, "pk", None) is None:
        return {"content_type": None, "object_id": None}
    return {
        "content_type": ContentType.objects.get_for_model(related, for_concrete_model=False),
        "object_id": related.pk,
    }


def _create_inbox(user, *, code: str, title: str, body: str, deep_link: str, related, log: NotificationLog):
    InAppNotification.objects.create(
        user=user,
        code=code,
        title=title or code,
        body=body,
        deep_link=deep_link,
        log=log,
        **_related_fields(related),
    )


def _deliver_push(user, title: str, body: str, deep_link: str) -> tuple[str, str, str]:
    """
    Attempt push delivery.

    Returns (status, provider, provider_ref_or_error).
    Provider is controlled by settings.PUSH_PROVIDER:
      - "log": success when at least one active device exists (dev/stub)
      - "fcm": Firebase Cloud Messaging HTTP v1
    """
    provider = (getattr(settings, "PUSH_PROVIDER", "log") or "log").strip().lower()
    devices = list(PushDevice.objects.filter(user=user, is_active=True)[:50])
    if not devices:
        return NotificationLogStatus.SKIPPED, provider, "no_device"

    if provider == "log":
        return (
            NotificationLogStatus.SENT,
            provider,
            f"devices={len(devices)}",
        )

    if provider == "fcm":
        from honaryaar.fcm import fcm_configured, send_to_token

        if not fcm_configured():
            return NotificationLogStatus.FAILED, provider, "fcm_not_configured"

        sent = 0
        errors: list[str] = []
        for device in devices:
            ok, detail, invalidate = send_to_token(
                device.token,
                title=title,
                body=body,
                deep_link=deep_link,
            )
            if ok:
                sent += 1
                device.save(update_fields=["last_seen_at"])
            else:
                errors.append(detail)
                if invalidate:
                    device.is_active = False
                    device.save(update_fields=["is_active", "last_seen_at"])

        if sent:
            ref = f"sent={sent}"
            if errors:
                ref = f"{ref}; errors={len(errors)}"
            return NotificationLogStatus.SENT, provider, ref[:200]
        return (
            NotificationLogStatus.FAILED,
            provider,
            (errors[0] if errors else "fcm_failed")[:500],
        )

    return (
        NotificationLogStatus.FAILED,
        provider,
        f"unsupported_provider:{provider}",
    )


def notify_user(
    user,
    code: str,
    context: dict[str, Any] | None = None,
    *,
    related=None,
    channels: tuple[str, ...] = (NotificationChannel.PUSH,),
) -> list[NotificationLog]:
    """
    Render templates and dispatch for each requested channel.
    Push is the supported channel today; SMS/email are skipped until wired.
    """
    if user is None:
        return []
    context = dict(context or {})
    logs: list[NotificationLog] = []

    for channel in channels:
        template = get_template(code, channel)
        if template is None:
            log = NotificationLog.objects.create(
                template=None,
                code=code,
                channel=channel,
                user=user,
                title="",
                body="",
                deep_link="",
                status=NotificationLogStatus.SKIPPED,
                provider="",
                error="no_active_template",
                context=context,
                **_related_fields(related),
            )
            logs.append(log)
            continue

        title = render_string(template.title, context)
        body = render_string(template.body, context)
        deep_link = render_string(template.deep_link, context)

        with transaction.atomic():
            log = NotificationLog.objects.create(
                template=template,
                code=code,
                channel=channel,
                user=user,
                title=title,
                body=body,
                deep_link=deep_link,
                status=NotificationLogStatus.PENDING,
                context=context,
                **_related_fields(related),
            )

            if channel == NotificationChannel.PUSH:
                _create_inbox(
                    user,
                    code=code,
                    title=title,
                    body=body,
                    deep_link=deep_link,
                    related=related,
                    log=log,
                )
                status, provider, detail = _deliver_push(user, title, body, deep_link)
                log.provider = provider
                if status == NotificationLogStatus.SENT:
                    log.status = status
                    log.provider_ref = detail
                    log.sent_at = timezone.now()
                    log.error = ""
                elif status == NotificationLogStatus.SKIPPED:
                    log.status = status
                    log.error = detail
                else:
                    log.status = NotificationLogStatus.FAILED
                    log.error = detail
                log.save(
                    update_fields=[
                        "status",
                        "provider",
                        "provider_ref",
                        "error",
                        "sent_at",
                    ]
                )
            elif channel == NotificationChannel.SMS:
                log.status = NotificationLogStatus.SKIPPED
                log.provider = "sms"
                log.error = "sms_not_configured"
                log.save(update_fields=["status", "provider", "error"])
            else:
                log.status = NotificationLogStatus.SKIPPED
                log.provider = channel
                log.error = f"{channel}_not_configured"
                log.save(update_fields=["status", "provider", "error"])

        logs.append(log)

    return logs


def notify_profile(profile, code: str, context: dict[str, Any] | None = None, **kwargs) -> list[NotificationLog]:
    if profile is None or not getattr(profile, "user_id", None):
        return []
    return notify_user(profile.user, code, context, **kwargs)


def register_push_device(user, token: str, platform: str = PushDevice.Platform.WEB) -> PushDevice:
    token = (token or "").strip()
    if not token:
        raise ValueError("empty token")
    device, _created = PushDevice.objects.update_or_create(
        token=token,
        defaults={
            "user": user,
            "platform": platform if platform in PushDevice.Platform.values else PushDevice.Platform.WEB,
            "is_active": True,
        },
    )
    return device


def purge_old_logs(*, days: int | None = None) -> int:
    from datetime import timedelta

    days = days if days is not None else int(getattr(settings, "NOTIFICATION_LOG_RETENTION_DAYS", 90))
    if days <= 0:
        return 0
    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = NotificationLog.objects.filter(created_at__lt=cutoff).delete()
    return deleted


def notify_invite_sent(invite) -> list[NotificationLog]:
    opportunity = invite.opportunity
    project = opportunity.project
    owner = project.owner
    return notify_profile(
        invite.profile,
        CODE_INVITE_SENT,
        {
            "invite_id": invite.pk,
            "opportunity_title": opportunity.title,
            "project_title": project.title,
            "owner_name": profile_label(owner),
            "artist_name": profile_label(invite.profile),
        },
        related=invite,
    )


def notify_invite_replied(invite) -> list[NotificationLog]:
    from honaryaar.labels import INVITE_LABELS
    from honaryaar.models import InviteStatus

    opportunity = invite.opportunity
    project = opportunity.project
    decision = invite.status
    if decision == InviteStatus.ACCEPTED:
        decision_label = "قبول"
    elif decision == InviteStatus.DECLINED:
        decision_label = "رد"
    else:
        decision_label = INVITE_LABELS.get(decision, decision)
    return notify_profile(
        project.owner,
        CODE_INVITE_REPLIED,
        {
            "artist_name": profile_label(invite.profile),
            "opportunity_title": opportunity.title,
            "project_title": project.title,
            "project_slug": project.slug,
            "opportunity_id": opportunity.pk,
            "decision": decision,
            "decision_label": decision_label,
        },
        related=invite,
    )


def notify_application_submitted(application) -> list[NotificationLog]:
    opportunity = application.opportunity
    project = opportunity.project
    return notify_profile(
        project.owner,
        CODE_APPLICATION_SUBMITTED,
        {
            "artist_name": profile_label(application.profile),
            "opportunity_title": opportunity.title,
            "project_title": project.title,
            "project_slug": project.slug,
            "application_id": application.pk,
        },
        related=application,
    )


def notify_application_status(application) -> list[NotificationLog]:
    from honaryaar.labels import APPLICATION_LABELS

    opportunity = application.opportunity
    project = opportunity.project
    return notify_profile(
        application.profile,
        CODE_APPLICATION_STATUS,
        {
            "opportunity_title": opportunity.title,
            "project_title": project.title,
            "status": application.status,
            "status_label": APPLICATION_LABELS.get(application.status, application.status),
            "application_id": application.pk,
        },
        related=application,
    )


def notify_collaboration_started(match) -> list[NotificationLog]:
    opportunity = match.opportunity
    project = opportunity.project
    context = {
        "opportunity_title": opportunity.title,
        "project_title": project.title,
        "match_id": match.pk,
        "artist_name": profile_label(match.profile),
        "owner_name": profile_label(project.owner),
    }
    logs = notify_profile(match.profile, CODE_COLLABORATION_STARTED, context, related=match)
    owner = project.owner
    if owner is not None and owner.pk != match.profile_id:
        logs.extend(notify_profile(owner, CODE_COLLABORATION_STARTED, context, related=match))
    return logs


def notify_project_member_invited(member) -> list[NotificationLog]:
    project = member.project
    return notify_profile(
        member.profile,
        CODE_PROJECT_MEMBER_INVITED,
        {
            "inviter_name": profile_label(member.invited_by),
            "project_title": project.title,
            "project_slug": project.slug,
            "member_id": member.pk,
        },
        related=member,
    )
