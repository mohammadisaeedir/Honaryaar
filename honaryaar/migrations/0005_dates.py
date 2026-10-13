from datetime import date

from django.db import migrations, models


PERSIAN_DEADLINES = {
    "۱۵ آبان ۱۴۰۵": date(2026, 11, 6),
    "۱ آذر ۱۴۰۵": date(2026, 11, 22),
    "۲۰ آبان ۱۴۰۵": date(2026, 11, 11),
    "۳۰ آبان ۱۴۰۵": date(2026, 11, 21),
    "۱۰ آذر ۱۴۰۵": date(2026, 12, 1),
    "۵ آذر ۱۴۰۵": date(2026, 11, 26),
}


def fill_dates(apps, schema_editor):
    from honaryaar.catalog import OPPORTUNITIES

    Opportunity = apps.get_model("honaryaar", "Opportunity")
    by_slug = {item["slug"]: item for item in OPPORTUNITIES}
    for row in Opportunity.objects.all():
        item = by_slug.get(row.slug)
        if item:
            row.start_date = item["start_date"]
            row.end_date = item["end_date"]
            row.deadline_on = item["deadline"]
        else:
            raw = (row.deadline or "").strip()
            if raw in PERSIAN_DEADLINES:
                row.deadline_on = PERSIAN_DEADLINES[raw]
            else:
                try:
                    row.deadline_on = date.fromisoformat(raw[:10])
                except ValueError:
                    row.deadline_on = None
        row.save(update_fields=["start_date", "end_date", "deadline_on"])


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0004_gender"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunity",
            name="start_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="end_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="deadline_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(fill_dates, migrations.RunPython.noop),
        migrations.RemoveField(model_name="opportunity", name="dates"),
        migrations.RemoveField(model_name="opportunity", name="deadline"),
        migrations.RenameField(model_name="opportunity", old_name="deadline_on", new_name="deadline"),
    ]
