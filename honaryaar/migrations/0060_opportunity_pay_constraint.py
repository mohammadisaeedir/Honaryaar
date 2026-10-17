from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0059_backfill_opportunity_pay"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="opportunity",
            name="pay_note",
        ),
        migrations.AddConstraint(
            model_name="opportunity",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(paid=False, pay_type="", pay_amount__isnull=True)
                    | models.Q(
                        paid=True,
                        pay_type__in=["negotiable", "gift", "box_office"],
                        pay_amount__isnull=True,
                    )
                    | models.Q(paid=True, pay_type="fixed", pay_amount__gt=0)
                ),
                name="opportunity_pay_consistent",
            ),
        ),
    ]
