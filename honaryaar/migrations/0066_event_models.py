import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0065_task_models"),
    ]

    operations = [
        migrations.CreateModel(
            name="Event",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255, verbose_name="عنوان")),
                ("starts_at", models.DateTimeField(verbose_name="شروع")),
                ("ends_at", models.DateTimeField(blank=True, null=True, verbose_name="پایان")),
                ("location", models.CharField(blank=True, max_length=255, verbose_name="مکان")),
                (
                    "phase",
                    models.CharField(
                        choices=[
                            ("create", "خلق"),
                            ("develop", "توسعه"),
                            ("produce", "تولید"),
                            ("perform", "اجرا"),
                            ("after", "پس‌اجرا"),
                        ],
                        max_length=10,
                        verbose_name="فاز",
                    ),
                ),
                (
                    "audience_type",
                    models.CharField(
                        choices=[("all_team", "کل تیم"), ("specific", "افراد خاص")],
                        default="all_team",
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_events",
                        to="honaryaar.profile",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="honaryaar.project",
                    ),
                ),
            ],
            options={
                "verbose_name": "رویداد",
                "verbose_name_plural": "رویدادها",
                "ordering": ["starts_at"],
            },
        ),
        migrations.CreateModel(
            name="EventInvitee",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "attendance",
                    models.CharField(
                        choices=[
                            ("pending", "در انتظار"),
                            ("confirmed", "تأیید"),
                            ("rejected", "رد"),
                        ],
                        default="pending",
                        max_length=10,
                    ),
                ),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="invitees",
                        to="honaryaar.event",
                    ),
                ),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="event_invitations",
                        to="honaryaar.profile",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="eventinvitee",
            constraint=models.UniqueConstraint(fields=("event", "profile"), name="unique_event_invitee"),
        ),
    ]
