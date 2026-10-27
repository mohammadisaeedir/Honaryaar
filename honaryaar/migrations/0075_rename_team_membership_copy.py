from django.db import migrations


def update_copy(apps, schema_editor):
    NotificationTemplate = apps.get_model("honaryaar", "NotificationTemplate")
    NotificationTemplate.objects.filter(code="project.member_invited", channel="push").update(
        name="عضویت در تیم بورد",
        title="عضویت در تیم",
        body="{{ inviter_name }} پیشنهاد عضویت شما در تیم پروژه «{{ project_title }}» را فرستاد.",
        available_vars="inviter_name, project_title, project_slug, member_id",
    )


def revert_copy(apps, schema_editor):
    NotificationTemplate = apps.get_model("honaryaar", "NotificationTemplate")
    NotificationTemplate.objects.filter(code="project.member_invited", channel="push").update(
        name="دعوت به بورد پروژه",
        title="دعوت به پروژه",
        body="{{ inviter_name }} شما را به بورد پروژه «{{ project_title }}» دعوت کرد.",
        available_vars="inviter_name, project_title, project_slug, member_id",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0074_in_app_notifications"),
    ]

    operations = [
        migrations.RunPython(update_copy, revert_copy),
    ]
