from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("ejranow", "0015_production_is_the_category_link"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="project",
            name="lead_name",
        ),
    ]
