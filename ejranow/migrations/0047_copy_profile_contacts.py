from django.core.exceptions import ValidationError
from django.db import migrations

LEGACY_FIELDS = (
    ("collab_phone", "phone"),
    ("whatsapp", "whatsapp"),
    ("telegram", "telegram"),
    ("instagram", "instagram"),
    ("website", "website"),
    ("youtube", "youtube"),
    ("aparat", "aparat"),
    ("twitch", "twitch"),
    ("imdb", "imdb"),
    ("linkedin", "linkedin"),
    ("pinterest", "pinterest"),
)


def copy_profile_contacts(apps, schema_editor):
    from ejranow.contacts import normalize_contact

    Profile = apps.get_model("ejranow", "Profile")
    ProfileContact = apps.get_model("ejranow", "ProfileContact")
    field_names = {field.name for field in Profile._meta.fields}
    copied = 0
    for profile in Profile.objects.all().iterator():
        position = 0
        for field_name, kind in LEGACY_FIELDS:
            if field_name not in field_names:
                continue
            raw = getattr(profile, field_name) or ""
            if not str(raw).strip():
                continue
            try:
                value = normalize_contact(kind, raw)
            except ValidationError:
                print(f"skip profile {profile.pk} {field_name} invalid")
                continue
            _, created = ProfileContact.objects.get_or_create(
                profile_id=profile.pk,
                kind=kind,
                value=value,
                defaults={"is_public": True, "position": position, "source": "legacy"},
            )
            if created:
                copied += 1
            position += 1
    print(f"profile_contacts_copied={copied}")


class Migration(migrations.Migration):

    dependencies = [
        ("ejranow", "0046_profile_contact"),
    ]

    operations = [
        migrations.RunPython(copy_profile_contacts, migrations.RunPython.noop),
    ]
