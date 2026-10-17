import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0055_project_source_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectContact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("phone", "Phone"), ("whatsapp", "WhatsApp"), ("telegram", "Telegram"), ("instagram", "Instagram"), ("email", "Email"), ("website", "Website"), ("youtube", "YouTube"), ("aparat", "Aparat"), ("twitch", "Twitch"), ("spotify", "Spotify"), ("soundcloud", "SoundCloud"), ("imdb", "IMDb"), ("linkedin", "LinkedIn"), ("pinterest", "Pinterest")], max_length=20)),
                ("value", models.CharField(max_length=200)),
                ("is_public", models.BooleanField(default=True)),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("source", models.CharField(blank=True, max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="contacts", to="honaryaar.project")),
            ],
            options={
                "verbose_name": "Project contact",
                "verbose_name_plural": "Project contacts",
                "ordering": ["project_id", "position", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="projectcontact",
            index=models.Index(fields=["kind"], name="honaryaar_p_kind_fcef15_idx"),
        ),
        migrations.AddConstraint(
            model_name="projectcontact",
            constraint=models.UniqueConstraint(fields=("project", "kind", "value"), name="unique_project_contact"),
        ),
    ]
