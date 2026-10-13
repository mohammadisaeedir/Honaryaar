from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0020_rename_production_artcategory"),
    ]

    operations = [
        migrations.RenameField(
            model_name="artcategory",
            old_name="category",
            new_name="art",
        ),
    ]
