from datetime import date

from django.db import migrations, models


SAMPLE_BIRTH_DATES = {
    "sara-mohammadi": date(1994, 9, 1),
    "kian-rezaei": date(1998, 1, 20),
    "niloufar-ahmadi": date(1991, 4, 15),
    "armin-kazemi": date(1990, 8, 9),
    "hasti-moradi": date(2004, 11, 2),
    "pouria-nemati": date(1996, 6, 18),
    "maryam-soleimani": date(1984, 12, 1),
    "reza-ghasemi": date(2007, 3, 12),
}


def set_sample_birth_dates(apps, schema_editor):
    Profile = apps.get_model("ejranow", "Profile")
    for slug, born in SAMPLE_BIRTH_DATES.items():
        Profile.objects.filter(slug=slug, birth_date__isnull=True).update(birth_date=born)


class Migration(migrations.Migration):

    dependencies = [
        ("ejranow", "0034_bookmark_gfk"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="birth_date",
            field=models.DateField(blank=True, null=True, verbose_name="Birth date"),
        ),
        migrations.RunPython(set_sample_birth_dates, migrations.RunPython.noop),
    ]
