import django.db.models.deletion
from django.db import migrations, models


def assign_production(apps, schema_editor):
    Role = apps.get_model("honaryaar", "Role")
    Production = apps.get_model("honaryaar", "Production")
    fallback = Production.objects.filter(slug="stage-play").first() or Production.objects.order_by("priority", "id").first()
    if fallback is None:
        return
    Role.objects.filter(production_id=None).update(production_id=fallback.id)


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0017_skill_group_enum"),
    ]

    operations = [
        migrations.AddField(
            model_name="role",
            name="production",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="roles",
                to="honaryaar.production",
            ),
        ),
        migrations.RunPython(assign_production, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="role",
            name="production",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="roles",
                to="honaryaar.production",
            ),
        ),
    ]
