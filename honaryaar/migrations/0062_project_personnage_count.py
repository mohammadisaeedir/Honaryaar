from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0061_project_budget_dates"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="personnage_count",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="تعداد پرسوناژ",
            ),
        ),
    ]
