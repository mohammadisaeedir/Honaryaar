from django.db import migrations, models


SAMPLE_GENDERS = {
    "sara-mohammadi": "female",
    "kian-rezaei": "male",
    "niloufar-ahmadi": "female",
    "armin-kazemi": "male",
    "hasti-moradi": "female",
    "pouria-nemati": "male",
    "maryam-soleimani": "female",
    "reza-ghasemi": "male",
}


def set_sample_genders(apps, schema_editor):
    Profile = apps.get_model("honaryaar", "Profile")
    for slug, gender in SAMPLE_GENDERS.items():
        Profile.objects.filter(slug=slug, gender="").update(gender=gender)


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0035_profile_birth_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="gender",
            field=models.CharField(
                blank=True,
                choices=[("male", "Male"), ("female", "Female")],
                max_length=20,
                verbose_name="Gender",
            ),
        ),
        migrations.RunPython(set_sample_genders, migrations.RunPython.noop),
    ]
