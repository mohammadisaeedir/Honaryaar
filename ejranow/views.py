from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render

from ejranow import catalog


def home(request):
    return render(
        request,
        "pages/home.html",
        {
            "opportunities": catalog.list_opportunities()[:6],
            "artists": catalog.list_artists()[:8],
            "projects": catalog.list_projects()[:6],
        },
    )


def about(request):
    return render(request, "about.html")


def artist_list(request):
    filters = {
        "q": request.GET.get("q", "").strip(),
        "city": request.GET.get("city", ""),
        "role": request.GET.get("role", ""),
    }
    return render(
        request,
        "pages/artists.html",
        {
            "artists": catalog.list_artists(**filters),
            "filters": filters,
            "cities": catalog.cities(),
            "roles": catalog.roles(),
        },
    )


def artist_detail(request, slug):
    artist = catalog.artist_by_slug(slug)
    if artist is None:
        raise Http404
    return render(request, "pages/artist.html", {"artist": artist})


def _age(raw):
    normalized = raw.strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    return int(normalized) if normalized.isdigit() else None


def opportunity_list(request):
    age_raw = request.GET.get("age", "").strip()
    filters = {
        "q": request.GET.get("q", "").strip(),
        "city": request.GET.get("city", ""),
        "paid": request.GET.get("paid", ""),
        "gender": request.GET.get("gender", ""),
        "production": request.GET.get("production", ""),
        "role": request.GET.get("role", ""),
        "age": _age(age_raw),
    }
    return render(
        request,
        "pages/opportunities.html",
        {
            "opportunities": catalog.list_opportunities(**filters),
            "filters": {**filters, "age": age_raw},
            "cities": catalog.cities(),
            "featured_cities": catalog.featured_cities(),
            "genders": catalog.genders(),
            "productions": catalog.PRODUCTIONS,
            "roles": catalog.roles(),
        },
    )


def opportunity_detail(request, slug):
    opportunity = catalog.opportunity_by_slug(slug)
    if opportunity is None:
        raise Http404
    project = catalog.project_by_slug(opportunity["project"])
    from ejranow.accounts import current_profile
    from ejranow.models import Application, Opportunity

    row = Opportunity.objects.select_related("project").filter(slug=slug).first()
    profile = current_profile(request.user)
    application = None
    is_owner = False
    if profile and row:
        is_owner = row.project.owner_id == profile.pk
        application = Application.objects.filter(profile=profile, opportunity=row).first()
    return render(
        request,
        "pages/opportunity.html",
        {
            "opportunity": opportunity,
            "project": project,
            "application": application,
            "is_owner": is_owner,
            "profile_ready": bool(profile and profile.first_name and profile.last_name),
        },
    )


def project_list(request):
    return render(request, "pages/projects.html", {"projects": catalog.list_projects()})


def project_detail(request, slug):
    project = catalog.project_by_slug(slug)
    if project is None:
        raise Http404
    return render(
        request,
        "pages/project.html",
        {
            "project": project,
            "opportunities": catalog.opportunities_for_project(slug),
        },
    )


def search(request):
    query = request.GET.get("q", "").strip()
    artists, opportunities = catalog.search(query)
    return render(
        request,
        "pages/search.html",
        {"query": query, "artists": artists, "opportunities": opportunities},
    )


def web_manifest(request):
    path = settings.BASE_DIR / "ejranow" / "static" / "manifest.webmanifest"
    return FileResponse(path.open("rb"), content_type="application/manifest+json")


def service_worker(request):
    path = settings.BASE_DIR / "ejranow" / "static" / "sw.js"
    response = FileResponse(path.open("rb"), content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response
