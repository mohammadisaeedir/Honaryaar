import django.db.models.deletion
from django.db import migrations, models


def seed_testimonials(apps, schema_editor):
    Project = apps.get_model("honaryaar", "Project")
    Testimonial = apps.get_model("honaryaar", "Testimonial")
    rows = [
        (
            "room-six",
            "متن نقش روشن بود و جلسه آشنا کوتاه. همان روز فهمیدم این پروژه به درد من می‌خورد.",
            "سارا محمدی",
            "بازیگر",
            True,
            1,
        ),
        (
            "passengers",
            "به جای توضیح طولانی، یک صحنه کوتاه خواستند. انتخاب بازیگر برایم قابل فهم شد.",
            "کیان رضایی",
            "بازیگر",
            True,
            2,
        ),
        (
            "last-rehearsal",
            "از همین صفحه درخواست دادم و جواب را بدون پیگیری تلفنی گرفتم.",
            "نرگس کاظمی",
            "بازیگر",
            True,
            3,
        ),
        (
            "shadows",
            "برای کارگاه دانشجویی، توضیح دستمزد و شهر از اول معلوم بود.",
            "امیر حسینی",
            "بازیگر",
            True,
            4,
        ),
    ]
    for slug, quote, name, role_label, featured, priority in rows:
        project = Project.objects.filter(slug=slug).first()
        if project is None:
            continue
        Testimonial.objects.get_or_create(
            project=project,
            name=name,
            defaults={
                "quote": quote,
                "role_label": role_label,
                "featured": featured,
                "priority": priority,
            },
        )


def unseed_testimonials(apps, schema_editor):
    Testimonial = apps.get_model("honaryaar", "Testimonial")
    Testimonial.objects.filter(
        name__in=["سارا محمدی", "کیان رضایی", "نرگس کاظمی", "امیر حسینی"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0008_skills"),
    ]

    operations = [
        migrations.CreateModel(
            name="Testimonial",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quote", models.TextField()),
                ("name", models.CharField(max_length=120)),
                ("role_label", models.CharField(blank=True, max_length=80)),
                ("featured", models.BooleanField(default=False)),
                ("priority", models.PositiveSmallIntegerField(default=100)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="testimonials",
                        to="honaryaar.project",
                    ),
                ),
            ],
            options={
                "ordering": ["priority", "id"],
            },
        ),
        migrations.RunPython(seed_testimonials, unseed_testimonials),
    ]
