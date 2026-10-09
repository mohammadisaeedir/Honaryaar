from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ejranow", "0039_ticket_message"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="featured",
            field=models.BooleanField(default=False, verbose_name="Featured"),
        ),
        migrations.AddField(
            model_name="project",
            name="start_date",
            field=models.DateField(blank=True, null=True, verbose_name="Start date"),
        ),
    ]
