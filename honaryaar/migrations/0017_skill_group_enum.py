from django.db import migrations, models


AREAS = [
    ("acting", "بازیگری"),
    ("technique", "تکنیک بازیگری"),
    ("singing", "آواز"),
    ("dance", "رقص"),
    ("comedy", "کمدی"),
    ("sports", "ورزش"),
    ("language", "زبان و گویش"),
    ("production", "تولید"),
    ("general", "مهارت‌های عمومی"),
]


def copy_group(apps, schema_editor):
    Skill = apps.get_model("honaryaar", "Skill")
    for skill in Skill.objects.select_related("group"):
        skill.area = skill.group.slug if skill.group_id else "general"
        skill.save(update_fields=["area"])


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0016_project_lead_from_owner"),
    ]

    operations = [
        migrations.AddField(
            model_name="skill",
            name="area",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.RunPython(copy_group, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="skill",
            name="group",
        ),
        migrations.RenameField(
            model_name="skill",
            old_name="area",
            new_name="group",
        ),
        migrations.AlterField(
            model_name="skill",
            name="group",
            field=models.CharField(choices=AREAS, max_length=20),
        ),
        migrations.AlterModelOptions(
            name="skill",
            options={"ordering": ["group", "title"]},
        ),
        migrations.AlterModelOptions(
            name="profileskill",
            options={"ordering": ["skill__group", "skill__title"]},
        ),
        migrations.DeleteModel(
            name="SkillGroup",
        ),
    ]
