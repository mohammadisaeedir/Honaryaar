from django.db import migrations


def attach_users(apps, schema_editor):
    Profile = apps.get_model("ejranow", "Profile")
    User = apps.get_model("auth", "User")
    for profile in Profile.objects.filter(user__isnull=True):
        base = (profile.slug or f"profile-{profile.pk}")[:140]
        username = base
        number = 2
        while True:
            taken = User.objects.filter(username=username).first()
            if taken is None:
                break
            if not Profile.objects.filter(user=taken).exists():
                profile.user = taken
                profile.save(update_fields=["user"])
                username = ""
                break
            username = f"{base}-{number}"[:150]
            number += 1
        if not username:
            continue
        user = User(
            username=username,
            first_name=(profile.first_name or "")[:150],
            last_name=(profile.last_name or "")[:150],
            is_staff=False,
            is_superuser=False,
            password="!",
        )
        user.save()
        profile.user = user
        profile.save(update_fields=["user"])


class Migration(migrations.Migration):
    dependencies = [
        ("ejranow", "0025_role_group_unique"),
    ]

    operations = [
        migrations.RunPython(attach_users, migrations.RunPython.noop),
    ]
