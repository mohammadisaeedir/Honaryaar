from django.db import migrations, models


def load_roles(apps, schema_editor):
    Role = apps.get_model("honaryaar", "Role")
    ArtCategory = apps.get_model("honaryaar", "ArtCategory")
    ProfileRole = apps.get_model("honaryaar", "ProfileRole")
    Credit = apps.get_model("honaryaar", "Credit")
    Project = apps.get_model("honaryaar", "Project")
    Opportunity = apps.get_model("honaryaar", "Opportunity")
    Testimonial = apps.get_model("honaryaar", "Testimonial")

    from honaryaar.catalog import role_catalog

    fallback = (
        ArtCategory.objects.filter(slug="stage-play").first()
        or ArtCategory.objects.order_by("priority", "id").first()
    )
    if fallback is None:
        return

    wanted = {}
    for item in role_catalog():
        role, created = Role.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "group": item["group"],
                "art_category": fallback,
            },
        )
        if not created:
            role.title = item["title"]
            role.group = item["group"]
            if role.art_category_id is None:
                role.art_category = fallback
            role.save()
        wanted[role.slug] = role

    def role_for(group, title):
        for role in wanted.values():
            if role.group == group and role.title == title:
                return role
        return None

    stage_manager = role_for("تئاتر و اجرای زنده", "مدیر صحنه")
    publicist = role_for("تئاتر و اجرای زنده", "مسئول روابط عمومی")
    actor = wanted["actor"]
    replacements = {
        "publicist": publicist or actor,
        "venue-manager": stage_manager or actor,
        "rehearsal-manager": stage_manager or actor,
        "student": actor,
        "teacher": actor,
    }

    def move_profile_roles(old, new):
        for link in ProfileRole.objects.filter(role_id=old.pk):
            clash = ProfileRole.objects.filter(profile_id=link.profile_id, role_id=new.pk).exclude(pk=link.pk)
            if clash.exists():
                link.delete()
            else:
                link.role_id = new.pk
                link.save(update_fields=["role"])

    for old in list(Role.objects.exclude(slug__in=wanted)):
        new = replacements.get(old.slug, actor)
        move_profile_roles(old, new)
        Credit.objects.filter(role_id=old.pk).update(role_id=new.pk)
        Project.objects.filter(lead_role_id=old.pk).update(lead_role_id=new.pk)
        Opportunity.objects.filter(role_id=old.pk).update(role_id=new.pk)
        Testimonial.objects.filter(role_id=old.pk).update(role_id=new.pk)
        old.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0023_profile_arts"),
    ]

    operations = [
        migrations.AddField(
            model_name="role",
            name="group",
            field=models.CharField(default="", max_length=80),
            preserve_default=False,
        ),
        migrations.RunPython(load_roles, migrations.RunPython.noop),
    ]
