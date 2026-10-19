from django.db import migrations

# Existing catalogue already has short-film (فیلم کوتاه). Skip by slug or title.
NEW_CATEGORIES = (
    {
        "slug": "street_theatre",
        "title": "تئاتر خیابانی",
        "art": "theatre",
        "priority": 10,
    },
    {
        "slug": "puppet_theatre",
        "title": "تئاتر عروسکی",
        "art": "theatre",
        "priority": 11,
    },
    {
        "slug": "short_film",
        "title": "فیلم کوتاه",
        "art": "film",
        "priority": 1,
    },
)


def seed_categories(apps, schema_editor):
    ArtCategory = apps.get_model("honaryaar", "ArtCategory")
    for item in NEW_CATEGORIES:
        if ArtCategory.objects.filter(slug=item["slug"]).exists():
            continue
        if ArtCategory.objects.filter(title=item["title"]).exists():
            continue
        ArtCategory.objects.create(
            slug=item["slug"],
            title=item["title"],
            art=item["art"],
            priority=item["priority"],
        )


def unseed_categories(apps, schema_editor):
    ArtCategory = apps.get_model("honaryaar", "ArtCategory")
    ArtCategory.objects.filter(slug__in=[item["slug"] for item in NEW_CATEGORIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0066_event_models"),
    ]

    operations = [
        migrations.RunPython(seed_categories, unseed_categories),
    ]
