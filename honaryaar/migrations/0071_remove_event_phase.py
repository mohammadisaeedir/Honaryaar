from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0070_remove_task_phase"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="event",
            name="phase",
        ),
    ]
