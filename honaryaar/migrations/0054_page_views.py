from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0053_align_index_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="views",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="project",
            name="views",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="views",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
