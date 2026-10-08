from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ejranow", "0037_project_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunity",
            name="collaboration_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("project_hire", "Project hire"),
                    ("contractor", "Contractor"),
                    ("salary", "Wage"),
                    ("daily", "Daily rate"),
                    ("hourly", "Hourly"),
                    ("session", "Per session"),
                    ("percentage", "Percentage"),
                    ("partnership", "Partnership"),
                    ("equity", "Equity share"),
                    ("honorary", "Honorary"),
                    ("internship", "Internship"),
                    ("volunteer", "Volunteer"),
                    ("long_term", "Long-term"),
                    ("temporary", "Temporary"),
                ],
                max_length=20,
                verbose_name="Collaboration type",
            ),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="experience_level",
            field=models.CharField(
                blank=True,
                choices=[
                    ("beginner", "Beginner"),
                    ("intermediate", "Intermediate"),
                    ("professional", "Professional"),
                ],
                max_length=20,
                verbose_name="Experience",
            ),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="special_conditions",
            field=models.JSONField(blank=True, default=list, verbose_name="Special conditions"),
        ),
    ]
