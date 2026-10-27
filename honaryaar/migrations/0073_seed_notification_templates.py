from django.db import migrations


PUSH = "push"

DEFAULT_TEMPLATES = [
    {
        "code": "invite.sent",
        "channel": PUSH,
        "name": "دعوت به فراخوان",
        "title": "دعوت جدید",
        "body": "{{ owner_name }} شما را به «{{ opportunity_title }}» در پروژه «{{ project_title }}» دعوت کرد.",
        "deep_link": "/me/invites/{{ invite_id }}/",
        "available_vars": "owner_name, opportunity_title, project_title, invite_id, artist_name",
    },
    {
        "code": "invite.replied",
        "channel": PUSH,
        "name": "پاسخ به دعوت",
        "title": "پاسخ دعوت",
        "body": "{{ artist_name }} دعوت «{{ opportunity_title }}» را {{ decision_label }} کرد.",
        "deep_link": "/me/projects/{{ project_slug }}/?step=opportunities&invite={{ opportunity_id }}",
        "available_vars": "artist_name, opportunity_title, project_title, project_slug, opportunity_id, decision, decision_label",
    },
    {
        "code": "application.submitted",
        "channel": PUSH,
        "name": "درخواست جدید",
        "title": "درخواست جدید",
        "body": "{{ artist_name }} برای «{{ opportunity_title }}» درخواست فرستاد.",
        "deep_link": "/me/projects/{{ project_slug }}/?step=opportunities",
        "available_vars": "artist_name, opportunity_title, project_title, project_slug, application_id",
    },
    {
        "code": "application.status_changed",
        "channel": PUSH,
        "name": "تغییر وضعیت درخواست",
        "title": "وضعیت درخواست",
        "body": "وضعیت درخواست شما برای «{{ opportunity_title }}» به «{{ status_label }}» تغییر کرد.",
        "deep_link": "/me/applications/{{ application_id }}/",
        "available_vars": "opportunity_title, project_title, status, status_label, application_id",
    },
    {
        "code": "collaboration.started",
        "channel": PUSH,
        "name": "شروع همکاری",
        "title": "همکاری جدید",
        "body": "همکاری شما در «{{ opportunity_title }}» (پروژه «{{ project_title }}») شروع شد.",
        "deep_link": "/me/collaborations/{{ match_id }}/",
        "available_vars": "opportunity_title, project_title, match_id, artist_name, owner_name",
    },
    {
        "code": "project.member_invited",
        "channel": PUSH,
        "name": "عضویت در تیم بورد",
        "title": "عضویت در تیم",
        "body": "{{ inviter_name }} پیشنهاد عضویت شما در تیم پروژه «{{ project_title }}» را فرستاد.",
        "deep_link": "/me/project-invites/",
        "available_vars": "inviter_name, project_title, project_slug, member_id",
    },
]


def seed(apps, schema_editor):
    NotificationTemplate = apps.get_model("honaryaar", "NotificationTemplate")
    for row in DEFAULT_TEMPLATES:
        NotificationTemplate.objects.update_or_create(
            code=row["code"],
            channel=row["channel"],
            defaults={
                "name": row["name"],
                "title": row["title"],
                "body": row["body"],
                "deep_link": row["deep_link"],
                "available_vars": row["available_vars"],
                "is_active": True,
            },
        )


def unseed(apps, schema_editor):
    NotificationTemplate = apps.get_model("honaryaar", "NotificationTemplate")
    codes = [row["code"] for row in DEFAULT_TEMPLATES]
    NotificationTemplate.objects.filter(code__in=codes, channel=PUSH).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0072_notification_templates_and_logs"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
