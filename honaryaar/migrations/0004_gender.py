from django.db import migrations, models


def set_gender_codes(apps, schema_editor):
    Opportunity = apps.get_model("honaryaar", "Opportunity")
    codes = {
        "مرد": "male",
        "زن": "female",
        "": "any",
        "male": "male",
        "female": "female",
        "any": "any",
    }
    for row in Opportunity.objects.all():
        row.gender = codes.get(row.gender, "any")
        row.save(update_fields=["gender"])


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0003_city"),
    ]

    operations = [
        migrations.RunPython(set_gender_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="opportunity",
            name="gender",
            field=models.CharField(
                choices=[("male", "Male"), ("female", "Female"), ("any", "No difference")],
                default="any",
                max_length=20,
            ),
        ),
    ]
