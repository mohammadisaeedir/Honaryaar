import re
import secrets

from django.db import migrations, models

_PHONE = re.compile(r"^09\d{9}$")
_SLUG = re.compile(r"^[-a-zA-Z0-9_]+$")


def _free_username(User, Profile, candidate, user_pk):
    if (
        candidate
        and len(candidate) <= 150
        and _SLUG.match(candidate)
        and not _PHONE.match(candidate)
        and not User.objects.filter(username=candidate).exclude(pk=user_pk).exists()
        and not Profile.objects.filter(slug=candidate).exclude(user_id=user_pk).exists()
    ):
        return candidate
    for _ in range(8):
        username = f"u-{secrets.token_hex(4)}"
        if not User.objects.filter(username=username).exists() and not Profile.objects.filter(slug=username).exists():
            return username
    return f"u-{secrets.token_hex(8)}"


def split_username_and_mobile(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Profile = apps.get_model("honaryaar", "Profile")
    for user in User.objects.all().order_by("id"):
        profile = Profile.objects.filter(user_id=user.pk).first()
        if _PHONE.match(user.username):
            phone = user.username
            username = _free_username(User, Profile, profile.slug if profile else "", user.pk)
            if username != user.username:
                user.username = username
                user.save(update_fields=["username"])
            if profile is None:
                Profile.objects.create(
                    user_id=user.pk,
                    slug=user.username,
                    mobile=phone,
                    status="claimed",
                )
                continue
            profile.mobile = phone
            profile.slug = user.username
            profile.save(update_fields=["mobile", "slug"])
            continue
        if profile is None or profile.slug == user.username:
            continue
        if not _SLUG.match(user.username) or len(user.username) > 150:
            continue
        holder = Profile.objects.filter(slug=user.username).exclude(pk=profile.pk).first()
        if holder is not None:
            holder.slug = f"tmp-{holder.pk}"
            holder.save(update_fields=["slug"])
        profile.slug = user.username
        profile.save(update_fields=["slug"])


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0042_profile_pictures"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="mobile",
            field=models.CharField(
                blank=True,
                help_text="Phone number from registration. Separate from the username.",
                max_length=11,
                null=True,
                unique=True,
                verbose_name="Mobile",
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="slug",
            field=models.SlugField(
                help_text="Public address. Always the same as the user's username.",
                max_length=150,
                unique=True,
            ),
        ),
        migrations.RunPython(split_username_and_mobile, migrations.RunPython.noop),
    ]
