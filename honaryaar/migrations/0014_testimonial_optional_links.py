import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0013_project_production"),
    ]

    operations = [
        migrations.AddField(
            model_name="testimonial",
            name="profile",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="testimonials",
                to="honaryaar.profile",
            ),
        ),
        migrations.AddField(
            model_name="testimonial",
            name="role",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="testimonials",
                to="honaryaar.role",
            ),
        ),
        migrations.AlterField(
            model_name="testimonial",
            name="name",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AlterField(
            model_name="testimonial",
            name="project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="testimonials",
                to="honaryaar.project",
            ),
        ),
    ]
