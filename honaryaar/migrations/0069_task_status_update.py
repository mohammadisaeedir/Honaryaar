from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0068_extend_project_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="task",
            name="status",
            field=models.CharField(
                choices=[
                    ("todo", "انجام‌نشده"),
                    ("in_progress", "در حال انجام"),
                    ("blocked", "بلاک‌شده"),
                    ("done", "انجام‌شده"),
                ],
                default="todo",
                max_length=20,
            ),
        ),
    ]
