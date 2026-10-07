import django.db.models.deletion
from django.db import migrations, models


PRODUCTIONS = [
    {"slug": "short-film", "title": "فیلم کوتاه", "category": "film", "priority": 1},
    {"slug": "feature-film", "title": "فیلم سینمایی", "category": "film", "priority": 2},
    {"slug": "series", "title": "سریال", "category": "film", "priority": 3},
    {"slug": "commercial", "title": "تبلیغات", "category": "film", "priority": 4},
    {"slug": "content", "title": "تولید محتوا", "category": "film", "priority": 5},
    {"slug": "industrial", "title": "صنعتی", "category": "film", "priority": 6},
    {"slug": "stage-play", "title": "نمایش صحنه‌ای", "category": "theatre", "priority": 7},
    {"slug": "reading", "title": "خوانش", "category": "theatre", "priority": 8},
    {"slug": "student-theatre", "title": "تئاتر دانشجویی", "category": "theatre", "priority": 9},
]


def link_productions(apps, schema_editor):
    ArtCategory = apps.get_model("ejranow", "ArtCategory")
    Production = apps.get_model("ejranow", "Production")
    Opportunity = apps.get_model("ejranow", "Opportunity")
    by_title = {}
    for item in PRODUCTIONS:
        category = ArtCategory.objects.filter(slug=item["category"]).first()
        if category is None:
            continue
        production, _created = Production.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "category": category,
                "priority": item["priority"],
            },
        )
        by_title[item["title"]] = production
    for opportunity in Opportunity.objects.all():
        production = by_title.get(opportunity.production_label)
        if production is None:
            continue
        opportunity.production = production
        opportunity.save(update_fields=["production"])


def unlink_productions(apps, schema_editor):
    Production = apps.get_model("ejranow", "Production")
    Opportunity = apps.get_model("ejranow", "Opportunity")
    by_id = {item.id: item.title for item in Production.objects.all()}
    for opportunity in Opportunity.objects.exclude(production_id=None):
        opportunity.production_label = by_id.get(opportunity.production_id, "")
        opportunity.save(update_fields=["production_label"])
    Production.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("ejranow", "0011_credit_role"),
    ]

    operations = [
        migrations.CreateModel(
            name="Production",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(unique=True)),
                ("title", models.CharField(max_length=80)),
                ("priority", models.PositiveSmallIntegerField(default=100)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="productions",
                        to="ejranow.artcategory",
                    ),
                ),
            ],
            options={"ordering": ["priority", "title"]},
        ),
        migrations.RenameField(
            model_name="opportunity",
            old_name="production",
            new_name="production_label",
        ),
        migrations.AddField(
            model_name="opportunity",
            name="production",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="opportunities",
                to="ejranow.production",
            ),
        ),
        migrations.RunPython(link_productions, unlink_productions),
        migrations.RemoveField(
            model_name="opportunity",
            name="production_label",
        ),
    ]
