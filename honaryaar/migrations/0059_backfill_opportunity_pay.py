from django.db import migrations


def backfill_pay(apps, schema_editor):
    from honaryaar.pay import classify_legacy_pay

    Opportunity = apps.get_model("honaryaar", "Opportunity")
    counts = {"untouched": 0, "negotiable": 0, "gift": 0, "box_office": 0, "fixed": 0}
    nonempty = 0
    fallbacks = []
    for row in Opportunity.objects.all().order_by("id"):
        note = row.pay_note or ""
        if note.strip():
            nonempty += 1
        if not row.paid:
            counts["untouched"] += 1
            continue
        pay_type, pay_amount, fell_back = classify_legacy_pay(note)
        if fell_back:
            fallbacks.append((row.slug, note))
        row.pay_type = pay_type
        row.pay_amount = pay_amount
        row.save(update_fields=["pay_type", "pay_amount"])
        counts[pay_type] += 1
    print(
        "pay backfill "
        f"nonempty_notes={nonempty} "
        f"untouched={counts['untouched']} "
        f"negotiable={counts['negotiable']} "
        f"gift={counts['gift']} "
        f"box_office={counts['box_office']} "
        f"fixed={counts['fixed']}"
    )
    if not fallbacks:
        print("pay backfill fixed_without_amount=0")
    for slug, note in fallbacks:
        print(f"pay backfill fixed_without_amount\t{slug}\t{note}")


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0058_opportunity_pay_fields"),
    ]

    operations = [
        migrations.RunPython(backfill_pay, migrations.RunPython.noop),
    ]
