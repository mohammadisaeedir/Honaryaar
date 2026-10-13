from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0019_production_art_enum"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Production",
            new_name="ArtCategory",
        ),
        migrations.AlterModelOptions(
            name="artcategory",
            options={
                "ordering": ["priority", "title"],
                "verbose_name": "art category",
                "verbose_name_plural": "art categories",
            },
        ),
        migrations.RenameField(
            model_name="project",
            old_name="production",
            new_name="art_category",
        ),
        migrations.RenameField(
            model_name="opportunity",
            old_name="production",
            new_name="art_category",
        ),
        migrations.RenameField(
            model_name="role",
            old_name="production",
            new_name="art_category",
        ),
    ]
