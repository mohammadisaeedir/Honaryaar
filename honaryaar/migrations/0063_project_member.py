import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0062_project_personnage_count"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "permission",
                    models.CharField(
                        choices=[("owner", "مالک"), ("admin", "مدیر"), ("member", "عضو")],
                        default="member",
                        max_length=10,
                    ),
                ),
                (
                    "invite_status",
                    models.CharField(
                        choices=[
                            ("invited", "دعوت‌شده"),
                            ("accepted", "پذیرفته‌شده"),
                            ("removed", "حذف‌شده"),
                        ],
                        default="invited",
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "invited_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sent_project_invites",
                        to="honaryaar.profile",
                    ),
                ),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="project_memberships",
                        to="honaryaar.profile",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="members",
                        to="honaryaar.project",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="honaryaar.role",
                    ),
                ),
            ],
            options={
                "verbose_name": "عضو پروژه",
                "verbose_name_plural": "اعضای پروژه",
            },
        ),
        migrations.AddConstraint(
            model_name="projectmember",
            constraint=models.UniqueConstraint(fields=("project", "profile"), name="unique_project_member"),
        ),
    ]
