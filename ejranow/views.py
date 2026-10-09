import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import mark_safe

from ejranow import catalog
from ejranow.accounts import professional_profile_ready
from ejranow.support_views import report_page_state


def _join_cta(user):
    if not user.is_authenticated:
        return {"href": reverse("login"), "label": "ورود/ثبت نام"}
    if professional_profile_ready(user):
        return {"href": reverse("opportunities"), "label": "مشاهده فراخوان‌های باز"}
    return {"href": f"{reverse('me-profile')}?edit=1", "label": "ساخت پروفایل حرفه‌ای"}


def home(request):
    opportunities = catalog.featured_opportunities()
    origin = request.build_absolute_uri("/").rstrip("/")
    payload = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "name": "هنریار",
                "url": origin + "/",
                "email": "hello@honaryaar.ir",
                "logo": request.build_absolute_uri(static("icons/apple-touch-icon.png")),
            },
            {
                "@type": "WebSite",
                "name": "هنریار",
                "url": origin + "/",
                "inLanguage": "fa",
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": origin + "/search/?q={search_term_string}",
                    "query-input": "required name=search_term_string",
                },
            },
            {
                "@type": "ItemList",
                "name": "فراخوان‌های ویژه",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": index,
                        "name": item["title"],
                        "url": request.build_absolute_uri(f"/opportunities/{item['slug']}/"),
                    }
                    for index, item in enumerate(opportunities, start=1)
                ],
            },
        ],
    }
    return render(
        request,
        "pages/home.html",
        {
            "opportunities": opportunities,
            "talent_stats": catalog.talent_stats(),
            "hire_stats": catalog.hire_stats(),
            "hero_fields": catalog.hero_fields(),
            "hero_roles": catalog.hero_roles(),
            "posts": catalog.HOME_POSTS,
            "latest_projects": catalog.latest_projects(),
            "bookmarked_projects": _bookmarked_slugs(request.user, "project"),
            "bookmarked_opportunities": _bookmarked_slugs(request.user, "opportunity"),
            "testimonials": catalog.featured_testimonials(),
            "home_json_ld": mark_safe(json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")),
            "join_cta": _join_cta(request.user),
        },
    )


def about(request):
    return render(request, "about.html")


def _bookmark_name(target, kind):
    if target is None:
        return "این مورد"
    if kind == "profile":
        full = f"{target.user.first_name} {target.user.last_name}".strip()
        return full or target.public_name()
    return getattr(target, "title", "") or "این مورد"


def _picked(request, key):
    return [value for value in request.GET.getlist(key) if value]


def bookmark_rows(user):
    if not getattr(user, "is_authenticated", False):
        return []
    from django.contrib.contenttypes.models import ContentType

    from ejranow.models import Bookmark, Opportunity, Profile, Project

    bookmarks = list(Bookmark.objects.filter(user=user).select_related("content_type"))
    profile_ids = [row.object_id for row in bookmarks if row.content_type.model == "profile"]
    project_ids = [row.object_id for row in bookmarks if row.content_type.model == "project"]
    opportunity_ids = [row.object_id for row in bookmarks if row.content_type.model == "opportunity"]
    profiles = {
        item.pk: item
        for item in Profile.objects.filter(pk__in=profile_ids).select_related("user").prefetch_related("profile_roles__role")
    }
    projects = {item.pk: item for item in Project.objects.filter(pk__in=project_ids)}
    opportunities = {item.pk: item for item in Opportunity.objects.filter(pk__in=opportunity_ids)}
    rows = []
    for bookmark in bookmarks:
        kind = bookmark.content_type.model
        target = {"profile": profiles, "project": projects, "opportunity": opportunities}.get(kind, {}).get(bookmark.object_id)
        if target is None:
            continue
        if kind == "profile":
            full = f"{target.user.first_name} {target.user.last_name}".strip()
            title = full or target.public_name()
            meta = " · ".join(link.role.title for link in target.profile_roles.all())
            url = reverse("artist", args=[target.slug])
        elif kind == "project":
            title = target.title
            meta = "پروژه"
            url = reverse("project", args=[target.slug])
        else:
            title = target.title
            meta = "فراخوان"
            url = reverse("opportunity", args=[target.slug])
        rows.append(
            {
                "title": title,
                "meta": meta,
                "status_code": target.status,
                "url": url,
                "slug": target.slug,
                "kind": kind,
                "remove": reverse("bookmark-remove", args=[bookmark.pk]),
            }
        )
    return rows


def _bookmarked_slugs(user, kind="profile"):
    return [row["slug"] for row in bookmark_rows(user) if row["kind"] == kind]


def _is_bookmarked(user, model, slug):
    if not getattr(user, "is_authenticated", False):
        return False
    from django.contrib.contenttypes.models import ContentType

    from ejranow.models import Bookmark

    obj = model.objects.filter(slug=slug).only("pk").first()
    if obj is None:
        return False
    return Bookmark.objects.filter(
        user=user,
        content_type=ContentType.objects.get_for_model(model),
        object_id=obj.pk,
    ).exists()


def _bookmark_wants_json(request):
    return request.headers.get("X-Requested-With") == "fetch"


def _bookmark_result(request, saved, message, fallback):
    if _bookmark_wants_json(request):
        return JsonResponse({"saved": saved, "message": message})
    messages.success(request, message)
    nxt = request.POST.get("next", "")
    if not nxt.startswith("/") or nxt.startswith("//"):
        nxt = fallback
    return redirect(nxt)


def _toggle_bookmark(request, model, slug, fallback):
    from django.contrib.contenttypes.models import ContentType

    from ejranow.models import Bookmark

    obj = get_object_or_404(model, slug=slug)
    content_type = ContentType.objects.get_for_model(model)
    bookmark = Bookmark.objects.filter(
        user=request.user,
        content_type=content_type,
        object_id=obj.pk,
    ).first()
    name = _bookmark_name(obj, content_type.model)
    if bookmark:
        bookmark.delete()
        return _bookmark_result(request, False, f"{name} از نشان‌شده‌ها حذف شد.", fallback)
    Bookmark.objects.create(user=request.user, content_type=content_type, object_id=obj.pk)
    return _bookmark_result(request, True, f"{name} به نشان‌شده‌ها اضافه شد.", fallback)


def _age_filter(request, bounds):
    if not bounds:
        return None, None, None
    floor, ceiling = bounds
    start = _age(request.GET.get("age_from", ""))
    end = _age(request.GET.get("age_to", ""))
    start = floor if start is None else min(max(start, floor), ceiling)
    end = ceiling if end is None else min(max(end, floor), ceiling)
    if start > end:
        start, end = end, start
    active = start > floor or end < ceiling
    return (
        start if active else None,
        end if active else None,
        catalog.age_group(floor, ceiling, start, end, active),
    )


def artist_list(request):
    age_from, age_to, age = _age_filter(request, catalog.artist_age_bounds())
    saved = [row for row in bookmark_rows(request.user) if row["kind"] == "profile"]
    filters = {
        "q": request.GET.get("q", "").strip(),
        "city": _picked(request, "city"),
        "role": _picked(request, "role"),
        "art": _picked(request, "art"),
        "gender": _picked(request, "gender"),
        "bookmark": _picked(request, "bookmark"),
        "age_from": age_from,
        "age_to": age_to,
    }
    groups = []
    if saved:
        picked = set(filters["bookmark"])
        groups.append(
            {
                "name": "bookmark",
                "label": "نشان‌شده‌ها",
                "kind": "saved",
                "open": bool(picked),
                "more": False,
                "selected": sum(1 for row in saved if row["slug"] in picked),
                "options": [
                    {
                        "value": row["slug"],
                        "label": row["title"],
                        "status_code": row["status_code"],
                        "selected": row["slug"] in picked,
                    }
                    for row in saved
                ],
            }
        )
    groups.extend(
        [
        catalog.choice_group("city", "شهر", [(city, city) for city in catalog.cities()], filters["city"]),
        catalog.choice_group("gender", "جنسیت", [("male", "مرد"), ("female", "زن")], filters["gender"]),
        catalog.choice_group(
            "art",
            "هنر",
            [(item["slug"], item["title"]) for item in catalog.artist_arts()],
            filters["art"],
        ),
        catalog.choice_group("role", "نقش", [(role["slug"], role["title"]) for role in catalog.roles()], filters["role"]),
        ]
    )
    if age:
        groups.append(age)
    sort, sort_label, sort_options = catalog.sort_state(request, "artists")
    filters["sort"] = sort
    return render(
        request,
        "pages/artists.html",
        {
            "artists": catalog.list_artists(**filters),
            "sort_label": sort_label,
            "sort_options": sort_options,
            "filters": filters,
            "groups": [group for group in groups if group["kind"] in {"text", "age"} or group["options"]],
            "filters_on": any(group.get("selected") for group in groups),
            "quick": catalog.filter_chips(request, catalog.artist_quick()),
            "clear_href": catalog.clear_filters_href(request),
            "bookmarked": _bookmarked_slugs(request.user),
        },
    )


@login_required
@require_POST
def bookmark_artist(request, slug):
    from ejranow.models import Profile

    return _toggle_bookmark(request, Profile, slug, reverse("artists"))


@login_required
@require_POST
def bookmark_project(request, slug):
    from ejranow.models import Project

    return _toggle_bookmark(request, Project, slug, reverse("projects"))


@login_required
@require_POST
def bookmark_opportunity(request, slug):
    from ejranow.models import Opportunity

    return _toggle_bookmark(request, Opportunity, slug, reverse("opportunities"))


@login_required
@require_POST
def bookmark_remove(request, pk):
    from ejranow.models import Bookmark

    bookmark = get_object_or_404(Bookmark, pk=pk, user=request.user)
    name = _bookmark_name(bookmark.target, bookmark.content_type.model)
    bookmark.delete()
    return _bookmark_result(request, False, f"{name} از نشان‌شده‌ها حذف شد.", reverse("me-collaborations"))


def artist_detail(request, slug):
    from ejranow.models import Profile

    artist = catalog.artist_by_slug(slug)
    if artist is None:
        raise Http404
    return render(
        request,
        "pages/artist.html",
        {
            "artist": artist,
            "saved": _is_bookmarked(request.user, Profile, slug),
            "report_title": artist["name"],
            "report_action": reverse("report-artist", args=[slug]),
            **report_page_state(request, f"artist:{slug}"),
        },
    )


def _age(raw):
    normalized = raw.strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    return int(normalized) if normalized.isdigit() else None


def opportunity_list(request):
    bounds = catalog.age_bounds()
    floor, ceiling = bounds if bounds else (None, None)
    start = _age(request.GET.get("age_from", ""))
    end = _age(request.GET.get("age_to", ""))
    if bounds:
        start = floor if start is None else min(max(start, floor), ceiling)
        end = ceiling if end is None else min(max(end, floor), ceiling)
        if start > end:
            start, end = end, start
        age_active = start > floor or end < ceiling
    else:
        age_active = False
    filters = {
        "q": request.GET.get("q", "").strip(),
        "city": _picked(request, "city"),
        "paid": _picked(request, "paid"),
        "gender": _picked(request, "gender"),
        "production": _picked(request, "production"),
        "role": _picked(request, "role"),
        "art": _picked(request, "art"),
        "status": _picked(request, "status"),
        "age_from": start if age_active else None,
        "age_to": end if age_active else None,
    }
    facets = catalog.opportunity_facets()
    groups = [
        catalog.choice_group("status", "وضعیت", [("open", "باز"), ("closed", "بسته")], filters["status"]),
        catalog.choice_group("city", "شهر", [(city, city) for city in facets["cities"]], filters["city"]),
        catalog.choice_group("art", "هنر", [(item["slug"], item["title"]) for item in facets["arts"]], filters["art"]),
        catalog.choice_group("role", "نقش", [(role["slug"], role["title"]) for role in facets["roles"]], filters["role"]),
        catalog.choice_group("production", "نوع", [(item, item) for item in facets["productions"]], filters["production"]),
        catalog.choice_group("gender", "جنسیت", [(item["value"], item["label"]) for item in facets["genders"]], filters["gender"]),
        catalog.choice_group("paid", "پرداخت", facets["paid"], filters["paid"]),
    ]
    if bounds:
        groups.append(catalog.age_group(floor, ceiling, start, end, age_active))
    sort, sort_label, sort_options = catalog.sort_state(request, "opportunities")
    filters["sort"] = sort
    return render(
        request,
        "pages/opportunities.html",
        {
            "opportunities": catalog.list_opportunities(**filters),
            "sort_label": sort_label,
            "sort_options": sort_options,
            "filters": filters,
            "groups": [group for group in groups if group["kind"] in {"text", "age"} or group["options"]],
            "filters_on": any(group.get("selected") for group in groups),
            "quick": catalog.filter_chips(request, catalog.opportunity_quick(facets)),
            "clear_href": catalog.clear_filters_href(request),
            "bookmarked_opportunities": _bookmarked_slugs(request.user, "opportunity"),
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
            "saved": _is_bookmarked(request.user, Opportunity, slug),
            "report_title": opportunity["title"],
            "report_action": reverse("report-opportunity", args=[slug]),
            **report_page_state(request, f"opportunity:{slug}"),
        },
    )


def project_list(request):
    filters = {
        "q": request.GET.get("q", "").strip(),
        "city": _picked(request, "city"),
        "art": _picked(request, "art"),
        "status": _picked(request, "status"),
    }
    sort, sort_label, sort_options = catalog.sort_state(request, "projects")
    filters["sort"] = sort
    groups = [
        catalog.choice_group("status", "وضعیت", [("casting", "در حال جذب"), ("completed", "اتمام")], filters["status"]),
        catalog.choice_group("city", "شهر", [(city, city) for city in catalog.cities()], filters["city"]),
        catalog.choice_group(
            "art",
            "هنر",
            [(item["slug"], item["title"]) for item in catalog.arts()],
            filters["art"],
        ),
    ]
    return render(
        request,
        "pages/projects.html",
        {
            "projects": catalog.list_projects(**filters),
            "sort_label": sort_label,
            "sort_options": sort_options,
            "filters": filters,
            "groups": groups,
            "filters_on": any(group.get("selected") for group in groups),
            "quick": catalog.filter_chips(
                request,
                [("تهران", {"city": "تهران"})]
                + [(item["title"], {"art": item["slug"]}) for item in catalog.arts()],
            ),
            "clear_href": catalog.clear_filters_href(request),
            "bookmarked_projects": _bookmarked_slugs(request.user, "project"),
        },
    )


def project_detail(request, slug):
    from ejranow.models import Project

    project = catalog.project_by_slug(slug)
    if project is None:
        raise Http404
    return render(
        request,
        "pages/project.html",
        {
            "project": project,
            "saved": _is_bookmarked(request.user, Project, slug),
            "opportunities": catalog.opportunities_for_project(slug),
            "bookmarked_opportunities": _bookmarked_slugs(request.user, "opportunity"),
            "report_title": project["title"],
            "report_action": reverse("report-project", args=[slug]),
            **report_page_state(request, f"project:{slug}"),
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
                {"href": "/opportunities/", "label": "فراخوان‌ها"},
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


def robots_txt(request):
    origin = request.build_absolute_uri("/").rstrip("/")
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /me/",
        "Disallow: /login/",
        "Disallow: /logout/",
        f"Sitemap: {origin}/sitemap.xml",
        "",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    origin = request.build_absolute_uri("/").rstrip("/")
    paths = [
        "/",
        "/opportunities/",
        "/artists/",
        "/projects/",
        "/about-us/",
        "/magazine/",
        "/terms/",
        "/contact/",
        "/sitemap/",
    ]
    paths.extend(f"/opportunities/{item['slug']}/" for item in catalog.list_opportunities())
    paths.extend(f"/artists/{item['slug']}/" for item in catalog.list_artists())
    paths.extend(f"/projects/{item['slug']}/" for item in catalog.list_projects())
    body = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path in paths:
        body.append("  <url>")
        body.append(f"    <loc>{origin}{path}</loc>")
        body.append("  </url>")
    body.append("</urlset>")
    return HttpResponse("\n".join(body), content_type="application/xml; charset=utf-8")


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
            "bookmarked": _bookmarked_slugs(request.user),
            "bookmarked_projects": _bookmarked_slugs(request.user, "project"),
            "bookmarked_opportunities": _bookmarked_slugs(request.user, "opportunity"),
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
