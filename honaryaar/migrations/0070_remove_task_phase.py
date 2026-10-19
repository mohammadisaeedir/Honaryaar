from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0069_task_status_update"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="task",
            name="phase",
        ),
    ]
