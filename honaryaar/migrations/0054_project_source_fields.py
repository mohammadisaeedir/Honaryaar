from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0053_align_index_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="lead_name",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="project",
            name="source_channel",
            field=models.CharField(blank=True, max_length=60),
        ),
        migrations.AddField(
            model_name="project",
            name="source_post_id",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="project",
            name="source_posted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="project",
            name="source_url",
            field=models.URLField(blank=True, max_length=300),
        ),
        migrations.AddConstraint(
            model_name="project",
            constraint=models.UniqueConstraint(
                condition=models.Q(("source_post_id__isnull", False)),
                fields=("source_channel", "source_post_id"),
                name="unique_project_source_post",
            ),
        ),
    ]
