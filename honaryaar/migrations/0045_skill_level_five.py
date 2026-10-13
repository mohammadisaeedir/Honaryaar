from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0044_short_profile_slug"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profileskill",
            name="level",
            field=models.PositiveSmallIntegerField(
                choices=[(1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")],
                default=2,
            ),
        ),
    ]
