import django.db.models.deletion
from django.db import migrations, models


def fill_production(apps, schema_editor):
    Project = apps.get_model("ejranow", "Project")
    Opportunity = apps.get_model("ejranow", "Opportunity")
    Production = apps.get_model("ejranow", "Production")
    fallback = Production.objects.order_by("priority", "id").first()
    if fallback is None:
        return
    for project in Project.objects.filter(production_id=None):
        match = Production.objects.filter(category_id=project.category_id).order_by("priority", "id").first()
        project.production_id = (match or fallback).id
        project.save(update_fields=["production"])
    for opportunity in Opportunity.objects.filter(production_id=None).select_related("project"):
        opportunity.production_id = opportunity.project.production_id or fallback.id
        opportunity.save(update_fields=["production"])


class Migration(migrations.Migration):
    dependencies = [
        ("ejranow", "0014_testimonial_optional_links"),
    ]

    operations = [
        migrations.RunPython(fill_production, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="project",
            name="production",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="projects",
                to="ejranow.production",
            ),
        ),
        migrations.AlterField(
            model_name="opportunity",
            name="production",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="opportunities",
                to="ejranow.production",
            ),
        ),
        migrations.RemoveField(
            model_name="project",
            name="category",
        ),
    ]
