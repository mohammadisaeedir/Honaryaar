from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0060_opportunity_pay_constraint"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="budget",
            field=models.CharField(blank=True, max_length=80, verbose_name="Budget"),
        ),
        migrations.AddField(
            model_name="project",
            name="contract",
            field=models.CharField(
                blank=True,
                choices=[
                    ("signed", "دارای قرارداد"),
                    ("drafting", "در حال تنظیم قرارداد"),
                    ("none", "بدون قرارداد / نیاز نیست"),
                    ("waiting", "در انتظار"),
                ],
                max_length=20,
                verbose_name="Contract",
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Publication date"),
        ),
        migrations.AddField(
            model_name="project",
            name="end_date",
            field=models.DateField(blank=True, null=True, verbose_name="Production end"),
        ),
        migrations.AddField(
            model_name="project",
            name="permit",
            field=models.CharField(
                blank=True,
                choices=[
                    ("pending", "در حال دریافت مجوز"),
                    ("received", "دریافت شده"),
                    ("none", "ندارد"),
                ],
                max_length=20,
                verbose_name="Permit",
            ),
        ),
        migrations.AlterField(
            model_name="project",
            name="start_date",
            field=models.DateField(blank=True, null=True, verbose_name="Production start"),
        ),
    ]
