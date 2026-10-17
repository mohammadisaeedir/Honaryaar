from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0057_alter_profilecontact_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunity",
            name="pay_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("negotiable", "توافقی"),
                    ("gift", "در حد هدیه"),
                    ("box_office", "درصدی از گیشه"),
                    ("fixed", "مبلغ مشخص"),
                ],
                default="",
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="opportunity",
            name="pay_amount",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
