from django.db import migrations


def load_catalogue(apps, schema_editor):
    from honaryaar.catalog import (
        ART_CATEGORIES,
        ARTISTS,
        MEDIA_KIND,
        OPPORTUNITIES,
        PROJECT_STATUS,
        PROJECTS,
        ROLES,
    )

    Role = apps.get_model("honaryaar", "Role")
    ArtCategory = apps.get_model("honaryaar", "ArtCategory")
    Profile = apps.get_model("honaryaar", "Profile")
    ProfileRole = apps.get_model("honaryaar", "ProfileRole")
    Credit = apps.get_model("honaryaar", "Credit")
    ProfileMedia = apps.get_model("honaryaar", "ProfileMedia")
    Project = apps.get_model("honaryaar", "Project")
    Opportunity = apps.get_model("honaryaar", "Opportunity")

    roles_by_slug = {}
    for item in ROLES:
        roles_by_slug[item["slug"]], _created = Role.objects.get_or_create(
            slug=item["slug"],
            defaults={"title": item["title"]},
        )
    categories = {}
    for item in ART_CATEGORIES:
        categories[item["slug"]], _created = ArtCategory.objects.get_or_create(
            slug=item["slug"],
            defaults={"title": item["title"], "active": item["active"]},
        )
    for item in ARTISTS:
        profile, _created = Profile.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "name": item["name"],
                "city": item["city"],
                "about": item["about"],
                "skills": item["skills"],
                "status": item["status"],
            },
        )
        ProfileRole.objects.get_or_create(
            profile=profile,
            role=roles_by_slug[item["role"]],
            defaults={"is_primary": True},
        )
        for credit in item["credits"]:
            Credit.objects.get_or_create(
                profile=profile,
                title=credit["title"],
                role_name=credit["role"],
                defaults={"year": credit["year"]},
            )
        for media in item["media"]:
            ProfileMedia.objects.get_or_create(
                profile=profile,
                label=media["label"],
                defaults={"kind": MEDIA_KIND.get(media["kind"], "photo")},
            )
    projects = {}
    for item in PROJECTS:
        category = categories.get(item.get("category") or item.get("art"))
        role = roles_by_slug.get(item.get("lead_role"))
        if category is None or role is None:
            continue
        status = PROJECT_STATUS.get(item.get("status"), "casting")
        if status not in {"casting", "open_call"}:
            status = "casting"
        projects[item["slug"]], _created = Project.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "city": item.get("city", ""),
                "category": category,
                "lead_name": item.get("lead", ""),
                "lead_role": role,
                "summary": item.get("summary", ""),
                "status": status,
            },
        )
    for item in OPPORTUNITIES:
        project = projects.get(item.get("project"))
        role = roles_by_slug.get(item.get("role"))
        if project is None or role is None:
            continue
        Opportunity.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "project": project,
                "role": role,
                "production": item["production"],
                "city": item["city"],
                "age_min": item["age_min"],
                "age_max": item["age_max"],
                "gender": item["gender"],
                "count": item["count"],
                "paid": item["paid"],
                "pay_note": item["pay_note"],
                "dates": "",
                "deadline": item["deadline"].isoformat() if item["deadline"] else "",
                "description": item["description"],
                "requirements": item["requirements"],
                "status": "open",
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(load_catalogue, migrations.RunPython.noop),
    ]
