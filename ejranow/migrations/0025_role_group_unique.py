from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ejranow", "0024_role_group"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="role",
            constraint=models.UniqueConstraint(fields=("group", "title"), name="unique_role_group_title"),
        ),
        migrations.AlterModelOptions(
            name="role",
            options={"ordering": ["group", "title"]},
        ),
    ]
