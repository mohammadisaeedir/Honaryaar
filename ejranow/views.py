from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render

from ejranow import catalog


def home(request):
    return render(
        request,
        "pages/home.html",
        {
            "opportunities": catalog.featured_opportunities(),
            "talent_stats": catalog.talent_stats(),
            "hire_stats": catalog.hire_stats(),
            "hero_fields": catalog.hero_fields(),
            "hero_roles": catalog.hero_roles(),
            "posts": catalog.HOME_POSTS,
            "testimonials": catalog.featured_testimonials(),
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
            "groups": [
                catalog.choice_group("city", "شهر", [(city, city) for city in catalog.cities()], filters["city"]),
                catalog.choice_group("role", "نقش", [(role["slug"], role["title"]) for role in catalog.roles()], filters["role"]),
            ],
            "quick": catalog.filter_chips(request, catalog.ARTIST_QUICK),
            "clear_href": catalog.clear_filters_href(request),
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
    facets = catalog.opportunity_facets()
    groups = [
        catalog.choice_group("city", "شهر", [(city, city) for city in facets["cities"]], filters["city"]),
        catalog.choice_group("role", "نقش", [(role["slug"], role["title"]) for role in facets["roles"]], filters["role"]),
        catalog.choice_group("production", "نوع", [(item, item) for item in facets["productions"]], filters["production"]),
        catalog.choice_group("gender", "جنسیت", [(item["value"], item["label"]) for item in facets["genders"]], filters["gender"]),
        catalog.choice_group("paid", "پرداخت", facets["paid"], filters["paid"]),
        catalog.text_group("age", "سن", age_raw, "مثلاً ۲۸"),
    ]
    return render(
        request,
        "pages/opportunities.html",
        {
            "opportunities": catalog.list_opportunities(**filters),
            "filters": {**filters, "age": age_raw},
            "groups": [group for group in groups if group["kind"] == "text" or len(group["options"]) > 1],
            "quick": catalog.filter_chips(request, catalog.opportunity_quick(facets)),
            "clear_href": catalog.clear_filters_href(request),
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
        },
    )


def project_list(request):
    filters = {
        "q": request.GET.get("q", "").strip(),
        "city": request.GET.get("city", ""),
        "category": request.GET.get("category", ""),
    }
    return render(
        request,
        "pages/projects.html",
        {
            "projects": catalog.list_projects(**filters),
            "filters": filters,
            "groups": [
                catalog.choice_group("city", "شهر", [(city, city) for city in catalog.cities()], filters["city"]),
                catalog.choice_group(
                    "category",
                    "موضوع",
                    [(item["slug"], item["title"]) for item in catalog.categories()],
                    filters["category"],
                ),
            ],
            "quick": catalog.filter_chips(
                request,
                [("تهران", {"city": "تهران"})]
                + [(item["title"], {"category": item["slug"]}) for item in catalog.categories()],
            ),
            "clear_href": catalog.clear_filters_href(request),
        },
    )


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


GUIDE_PAGES = {
    "magazine": {
        "page_title": "مجله هنری",
        "paragraphs": [
            "مجله هنریار جایی برای یادداشت‌های کوتاه درباره تئاتر، بازیگری و پشت صحنه است.",
            "هر شماره چند متن ساده دارد: یک نقش، یک تمرین، و یک تجربه از سالن.",
            "شماره‌های بعدی همین‌جا منتشر می‌شوند.",
        ],
    },
    "terms": {
        "page_title": "قوانین و مقررات",
        "paragraphs": [
            "با ساختن حساب در هنریار، همین قانون‌ها را می‌پذیرید.",
            "حساب با شماره موبایل ساخته می‌شود و مسئولیت ورود با همان شماره با شماست.",
            "متنی که در پروفایل یا پروژه می‌گذارید باید مال خودتان باشد.",
            "شماره و اطلاعات تماس دیگران را بدون اجازه آن‌ها منتشر نکنید.",
            "هنریار می‌تواند محتوایی را که این قانون‌ها را نقض کند بردارد.",
        ],
    },
    "contact": {
        "page_title": "تماس با ما",
        "paragraphs": [
            "برای همکاری، گزارش مشکل، یا هر حرف دیگری بنویسید.",
            "ایمیل: hello@honaryaar.ir",
        ],
    },
}


def guide(request):
    page = GUIDE_PAGES[request.resolver_match.url_name]
    return render(request, "pages/plain.html", page)


def sitemap_page(request):
    return render(
        request,
        "pages/plain.html",
        {
            "page_title": "سایت مپ",
            "paragraphs": ["صفحه‌های اصلی هنریار:"],
            "links": [
                {"href": "/", "label": "خانه"},
                {"href": "/opportunities/", "label": "فرصت‌ها"},
                {"href": "/artists/", "label": "هنرمندان"},
                {"href": "/projects/", "label": "پروژه‌ها"},
                {"href": "/search/", "label": "جستجو"},
                {"href": "/magazine/", "label": "مجله هنری"},
                {"href": "/about-us/", "label": "درباره ما"},
                {"href": "/terms/", "label": "قوانین و مقررات"},
                {"href": "/contact/", "label": "تماس با ما"},
            ],
        },
    )


def search(request):
    query = request.GET.get("q", "").strip()
    artists, opportunities, projects = catalog.search(query)
    return render(
        request,
        "pages/search.html",
        {
            "query": query,
            "artists": artists,
            "opportunities": opportunities,
            "projects": projects,
        },
    )


def web_manifest(request):
    path = settings.BASE_DIR / "ejranow" / "static" / "manifest.webmanifest"
    return FileResponse(path.open("rb"), content_type="application/manifest+json")


def service_worker(request):
    path = settings.BASE_DIR / "ejranow" / "static" / "sw.js"
    response = FileResponse(path.open("rb"), content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response
