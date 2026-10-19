from django.db import migrations, models


def promote_board_drafts(apps, schema_editor):
    """Draft projects that already have board tasks move into lifecycle CREATE."""
    Project = apps.get_model("honaryaar", "Project")
    Project.objects.filter(status="draft", tasks__isnull=False).distinct().update(status="create")


def undo_promote(apps, schema_editor):
    Project = apps.get_model("honaryaar", "Project")
    Project.objects.filter(status="create").update(status="draft")


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0067_seed_art_categories"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "پیش‌نویس"),
                    ("casting", "در حال جذب"),
                    ("completed", "اتمام"),
                    ("create", "خلق"),
                    ("develop", "توسعه"),
                    ("produce", "تولید"),
                    ("perform", "اجرا"),
                    ("after", "پس‌اجرا"),
                ],
                default="draft",
                max_length=20,
            ),
        ),
        migrations.RunPython(promote_board_drafts, undo_promote),
    ]
