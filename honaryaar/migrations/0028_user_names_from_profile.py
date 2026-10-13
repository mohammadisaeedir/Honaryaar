from django.db import migrations


def copy_names(apps, schema_editor):
    Profile = apps.get_model("honaryaar", "Profile")
    for profile in Profile.objects.select_related("user"):
        user = profile.user
        updates = []
        if profile.first_name and profile.first_name != user.first_name:
            user.first_name = profile.first_name[:150]
            updates.append("first_name")
        if profile.last_name and profile.last_name != user.last_name:
            user.last_name = profile.last_name[:150]
            updates.append("last_name")
        if updates:
            user.save(update_fields=updates)


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0027_profile_user_protect"),
    ]

    operations = [
        migrations.RunPython(copy_names, migrations.RunPython.noop),
    ]
