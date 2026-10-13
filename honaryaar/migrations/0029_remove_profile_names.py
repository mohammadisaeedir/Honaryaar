from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0028_user_names_from_profile"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="profile",
            name="first_name",
        ),
        migrations.RemoveField(
            model_name="profile",
            name="last_name",
        ),
    ]
