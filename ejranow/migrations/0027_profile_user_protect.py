import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ejranow", "0026_profile_requires_user"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="user",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="profile",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="name",
            field=models.CharField(blank=True, max_length=120, verbose_name="Art name"),
        ),
    ]
