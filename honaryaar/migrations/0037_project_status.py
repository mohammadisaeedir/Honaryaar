from django.db import migrations, models


def close_open_calls(apps, schema_editor):
    Project = apps.get_model("honaryaar", "Project")
    Project.objects.filter(status="open_call").update(status="casting")


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0036_profile_gender"),
    ]

    operations = [
        migrations.RunPython(close_open_calls, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="project",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "پیش‌نویس"),
                    ("casting", "در حال جذب"),
                    ("completed", "اتمام"),
                ],
                default="draft",
                max_length=20,
            ),
        ),
    ]
