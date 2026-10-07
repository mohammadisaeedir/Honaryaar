from django.db import migrations, models


ARTS = [
    ("theatre", "تئاتر"),
    ("music", "موسیقی"),
    ("film", "سینما"),
    ("painting", "نقاشی"),
    ("architecture", "معماری"),
    ("sculpture", "مجسمه‌سازی"),
    ("literature", "ادبیات"),
]


def copy_category(apps, schema_editor):
    Production = apps.get_model("ejranow", "Production")
    for item in Production.objects.select_related("category"):
        item.art = item.category.slug if item.category_id else "theatre"
        item.save(update_fields=["art"])


class Migration(migrations.Migration):
    dependencies = [
        ("ejranow", "0018_role_production"),
    ]

    operations = [
        migrations.AddField(
            model_name="production",
            name="art",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.RunPython(copy_category, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="production",
            name="category",
        ),
        migrations.RenameField(
            model_name="production",
            old_name="art",
            new_name="category",
        ),
        migrations.AlterField(
            model_name="production",
            name="category",
            field=models.CharField(choices=ARTS, max_length=20),
        ),
        migrations.DeleteModel(
            name="ArtCategory",
        ),
    ]
