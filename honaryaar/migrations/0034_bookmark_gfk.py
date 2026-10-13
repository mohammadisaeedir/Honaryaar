import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def copy_bookmarks(apps, schema_editor):
    Old = apps.get_model("honaryaar", "BookmarkProfile")
    New = apps.get_model("honaryaar", "Bookmark")
    ContentType = apps.get_model("contenttypes", "ContentType")
    profile_type = ContentType.objects.get(app_label="honaryaar", model="profile")
    for row in Old.objects.all():
        created = New.objects.create(
            user_id=row.user_id,
            content_type_id=profile_type.id,
            object_id=row.profile_id,
        )
        New.objects.filter(pk=created.pk).update(created_at=row.created_at)


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("honaryaar", "0033_bookmark_profile"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Bookmark",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("object_id", models.PositiveBigIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "content_type",
                    models.ForeignKey(
                        limit_choices_to={
                            "app_label": "honaryaar",
                            "model__in": ["profile", "project", "opportunity"],
                        },
                        on_delete=django.db.models.deletion.PROTECT,
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bookmarks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "content_type", "object_id"),
                        name="unique_bookmark_target",
                    )
                ],
            },
        ),
        migrations.RunPython(copy_bookmarks, migrations.RunPython.noop),
        migrations.DeleteModel(name="BookmarkProfile"),
    ]
