import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0022_city_province_choices"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="arts",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ("theatre", "تئاتر"),
                        ("music", "موسیقی"),
                        ("film", "سینما"),
                        ("painting", "نقاشی"),
                        ("architecture", "معماری"),
                        ("sculpture", "مجسمه‌سازی"),
                        ("literature", "ادبیات"),
                    ],
                    max_length=20,
                ),
                blank=True,
                default=list,
                help_text="Arts this person works in or is interested in.",
                size=None,
                verbose_name="arts",
            ),
        ),
    ]
