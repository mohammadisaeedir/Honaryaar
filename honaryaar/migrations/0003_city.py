import django.db.models.deletion
from django.db import migrations, models


def seed_cities(apps, schema_editor):
    from honaryaar.catalog import CITIES

    City = apps.get_model("honaryaar", "City")
    for item in CITIES:
        City.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "province": item["province"],
                "priority": item["priority"],
                "featured": item["featured"],
            },
        )


def link_cities(apps, schema_editor):
    City = apps.get_model("honaryaar", "City")
    by_title = {city.title: city for city in City.objects.all()}
    for model_name in ("Profile", "Project", "Opportunity"):
        Model = apps.get_model("honaryaar", model_name)
        for row in Model.objects.all():
            match = by_title.get(row.city)
            if match is None:
                continue
            row.city_ref = match
            row.save(update_fields=["city_ref"])


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0002_seed_catalogue"),
    ]

    operations = [
        migrations.CreateModel(
            name="City",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(unique=True)),
                ("title", models.CharField(max_length=80)),
                ("province", models.CharField(blank=True, max_length=80)),
                ("priority", models.PositiveSmallIntegerField(default=100)),
                ("featured", models.BooleanField(default=False)),
            ],
            options={
                "verbose_name_plural": "cities",
                "ordering": ["priority", "title"],
            },
        ),
        migrations.RunPython(seed_cities, migrations.RunPython.noop),
        migrations.AddField(
            model_name="profile",
            name="city_ref",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="profiles",
                to="honaryaar.city",
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="city_ref",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="projects",
                to="honaryaar.city",
            ),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="city_ref",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="opportunities",
                to="honaryaar.city",
            ),
        ),
        migrations.RunPython(link_cities, migrations.RunPython.noop),
        migrations.RemoveField(model_name="profile", name="city"),
        migrations.RemoveField(model_name="project", name="city"),
        migrations.RemoveField(model_name="opportunity", name="city"),
        migrations.RenameField(model_name="profile", old_name="city_ref", new_name="city"),
        migrations.RenameField(model_name="project", old_name="city_ref", new_name="city"),
        migrations.RenameField(model_name="opportunity", old_name="city_ref", new_name="city"),
    ]
