from django.db import migrations


def load_catalogue(apps, schema_editor):
    from ejranow.catalog import (
        ART_CATEGORIES,
        ARTISTS,
        MEDIA_KIND,
        OPPORTUNITIES,
        PROJECT_STATUS,
        PROJECTS,
        ROLES,
    )

    Role = apps.get_model("ejranow", "Role")
    ArtCategory = apps.get_model("ejranow", "ArtCategory")
    Profile = apps.get_model("ejranow", "Profile")
    ProfileRole = apps.get_model("ejranow", "ProfileRole")
    Credit = apps.get_model("ejranow", "Credit")
    ProfileMedia = apps.get_model("ejranow", "ProfileMedia")
    Project = apps.get_model("ejranow", "Project")
    Opportunity = apps.get_model("ejranow", "Opportunity")

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
        projects[item["slug"]], _created = Project.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "city": item["city"],
                "category": categories[item["category"]],
                "lead_name": item["lead"],
                "lead_role": roles_by_slug[item["lead_role"]],
                "summary": item["summary"],
                "status": PROJECT_STATUS[item["status"]],
            },
        )
    for item in OPPORTUNITIES:
        Opportunity.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "project": projects[item["project"]],
                "role": roles_by_slug[item["role"]],
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
        ("ejranow", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(load_catalogue, migrations.RunPython.noop),
    ]
