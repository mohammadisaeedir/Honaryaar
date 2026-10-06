from django.db import migrations, models


def mark_featured(apps, schema_editor):
    from ejranow.catalog import OPPORTUNITIES

    Opportunity = apps.get_model("ejranow", "Opportunity")
    slugs = [item["slug"] for item in OPPORTUNITIES if item.get("featured")]
    Opportunity.objects.filter(slug__in=slugs).update(featured=True)


def unmark_featured(apps, schema_editor):
    Opportunity = apps.get_model("ejranow", "Opportunity")
    Opportunity.objects.update(featured=False)


class Migration(migrations.Migration):
    dependencies = [
        ("ejranow", "0009_testimonial"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunity",
            name="featured",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(mark_featured, unmark_featured),
    ]
