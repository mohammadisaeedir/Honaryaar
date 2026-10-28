"""Idempotent seed of push NotificationTemplate rows (same as migration 0073)."""

from django.core.management.base import BaseCommand

from honaryaar.models import NotificationChannel, NotificationTemplate

# Keep in sync with honaryaar/migrations/0073_seed_notification_templates.py
DEFAULT_TEMPLATES = [
    {
        "code": "invite.sent",
        "name": "دعوت به فراخوان",
        "title": "دعوت جدید",
        "body": "{{ owner_name }} شما را به «{{ opportunity_title }}» در پروژه «{{ project_title }}» دعوت کرد.",
        "deep_link": "/me/invites/{{ invite_id }}/",
        "available_vars": "owner_name, opportunity_title, project_title, invite_id, artist_name",
    },
    {
        "code": "invite.replied",
        "name": "پاسخ به دعوت",
        "title": "پاسخ دعوت",
        "body": "{{ artist_name }} دعوت «{{ opportunity_title }}» را {{ decision_label }} کرد.",
        "deep_link": "/me/projects/{{ project_slug }}/?step=opportunities&invite={{ opportunity_id }}",
        "available_vars": "artist_name, opportunity_title, project_title, project_slug, opportunity_id, decision, decision_label",
    },
    {
        "code": "application.submitted",
        "name": "درخواست جدید",
        "title": "درخواست جدید",
        "body": "{{ artist_name }} برای «{{ opportunity_title }}» درخواست فرستاد.",
        "deep_link": "/me/projects/{{ project_slug }}/?step=opportunities",
        "available_vars": "artist_name, opportunity_title, project_title, project_slug, application_id",
    },
    {
        "code": "application.status_changed",
        "name": "تغییر وضعیت درخواست",
        "title": "وضعیت درخواست",
        "body": "وضعیت درخواست شما برای «{{ opportunity_title }}» به «{{ status_label }}» تغییر کرد.",
        "deep_link": "/me/applications/{{ application_id }}/",
        "available_vars": "opportunity_title, project_title, status, status_label, application_id",
    },
    {
        "code": "collaboration.started",
        "name": "شروع همکاری",
        "title": "همکاری جدید",
        "body": "همکاری شما در «{{ opportunity_title }}» (پروژه «{{ project_title }}») شروع شد.",
        "deep_link": "/me/collaborations/{{ match_id }}/",
        "available_vars": "opportunity_title, project_title, match_id, artist_name, owner_name",
    },
    {
        "code": "project.member_invited",
        "name": "عضویت در تیم بورد",
        "title": "عضویت در تیم",
        "body": "{{ inviter_name }} پیشنهاد عضویت شما در تیم پروژه «{{ project_title }}» را فرستاد.",
        "deep_link": "/me/project-invites/",
        "available_vars": "inviter_name, project_title, project_slug, member_id",
    },
]


class Command(BaseCommand):
    help = "Create or update the default push NotificationTemplate rows."

    def handle(self, *args, **options):
        channel = NotificationChannel.PUSH
        created = updated = 0
        for row in DEFAULT_TEMPLATES:
            _, was_created = NotificationTemplate.objects.update_or_create(
                code=row["code"],
                channel=channel,
                defaults={
                    "name": row["name"],
                    "title": row["title"],
                    "body": row["body"],
                    "deep_link": row["deep_link"],
                    "available_vars": row["available_vars"],
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"notification templates: created={created} updated={updated} total={len(DEFAULT_TEMPLATES)}"
            )
        )
