from django.db import migrations, models
import django.db.models.deletion


def copy_production(apps, schema_editor):
    Project = apps.get_model("ejranow", "Project")
    Opportunity = apps.get_model("ejranow", "Opportunity")
    for project in Project.objects.filter(production_id=None):
        production_id = (
            Opportunity.objects.filter(project_id=project.id)
            .exclude(production_id=None)
            .order_by("id")
            .values_list("production_id", flat=True)
            .first()
        )
        if production_id is None:
            continue
        project.production_id = production_id
        project.save(update_fields=["production"])


class Migration(migrations.Migration):
    dependencies = [
        ("ejranow", "0012_production"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="production",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="projects",
                to="ejranow.production",
            ),
        ),
        migrations.RunPython(copy_production, migrations.RunPython.noop),
    ]
