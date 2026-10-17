from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0056_project_contact"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="profilecontact",
            options={
                "ordering": ["profile_id", "position", "id"],
                "verbose_name": "contact",
                "verbose_name_plural": "contacts",
            },
        ),
    ]
