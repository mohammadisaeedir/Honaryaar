import re
import secrets
import string

from django.db import migrations

_GENERATED = re.compile(r"^u-[0-9a-f]+$")
_ALPHABET = string.ascii_lowercase + string.digits


def _allocate(User, Profile):
    for _ in range(30):
        code = "".join(secrets.choice(_ALPHABET) for _ in range(5))
        if not User.objects.filter(username=code).exists() and not Profile.objects.filter(slug=code).exists():
            return code
    raise RuntimeError("Could not allocate a unique profile address.")


def shorten_generated_slugs(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Profile = apps.get_model("honaryaar", "Profile")
    for user in list(User.objects.all().order_by("id")):
        if not _GENERATED.match(user.username):
            continue
        code = _allocate(User, Profile)
        User.objects.filter(pk=user.pk).update(username=code)
        Profile.objects.filter(user_id=user.pk).update(slug=code)


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0043_profile_mobile"),
    ]

    operations = [
        migrations.RunPython(shorten_generated_slugs, migrations.RunPython.noop),
    ]
