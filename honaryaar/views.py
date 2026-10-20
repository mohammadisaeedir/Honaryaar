import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import mark_safe

from honaryaar import catalog
from honaryaar.accounts import professional_profile_ready
from honaryaar.support_views import report_page_state


def _join_cta(user):
    if not user.is_authenticated:
        return {"href": reverse("login"), "label": "ورود/ثبت نام"}
    if professional_profile_ready(user):
        return {"href": reverse("opportunities"), "label": "مشاهده فراخوان‌های باز"}
    return {"href": f"{reverse('me-profile')}?edit=hero", "label": "ساخت پروفایل حرفه‌ای"}


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

    from honaryaar.models import Bookmark, Opportunity, Profile, Project

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
            links = list(target.profile_roles.all())
            primary = next((link for link in links if link.is_primary), None)
            if primary is None and links:
                primary = links[0]
            role = primary.role.title if primary else ""
            meta = " · ".join(link.role.title for link in links)
            url = reverse("artist", args=[target.slug])
        elif kind == "project":
            from honaryaar.media_service import project_image_url

            title = target.title
            meta = "پروژه"
            url = reverse("project", args=[target.slug])
            image = project_image_url(target)
        else:
            title = target.title
            meta = "فراخوان"
            url = reverse("opportunity", args=[target.slug])
        rows.append(
            {
                "title": title,
                "meta": meta,
                "role": role if kind == "profile" else "",
                "status_code": target.status,
                "url": url,
                "slug": target.slug,
                "kind": kind,
                "image": image if kind == "project" else "",
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

    from honaryaar.models import Bookmark

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

    from honaryaar.models import Bookmark

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


def _invite_board(user):
    from honaryaar.accounts import current_profile
    from honaryaar.media_service import project_image_url
    from honaryaar.models import Opportunity, Project

    profile = current_profile(user)
    if profile is None:
        return []
    projects = Project.objects.filter(owner=profile).prefetch_related(
        Prefetch(
            "opportunities",
            queryset=Opportunity.objects.select_related("role").annotate(invite_count=Count("invites")),
        )
    )
    return [
        {
            "slug": project.slug,
            "title": project.title,
            "image": project_image_url(project),
            "opportunities": [
                {
                    "id": item.pk,
                    "title": item.title,
                    "role": item.role.title,
                    "invites": item.invite_count,
                }
                for item in project.opportunities.all()
            ],
        }
        for project in projects
    ]


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
    sort, sort_label, sort_options = catalog.sort_state(request, "artists")
    filters["sort"] = sort
    partial = request.headers.get("X-Requested-With") == "fetch" and "offset" in request.GET
    if partial:
        offset = min(max(_safe_int(request.GET.get("offset"), 0), 0), 10_000)
        limit = min(max(_safe_int(request.GET.get("limit"), 1), 1), _ROW_CAP)
        artists, total = catalog.page_artists(**filters, offset=offset, limit=limit)
        return render(
            request,
            "components/catalog/artist_page.html",
            {"artists": artists, "bookmarked": _bookmarked_slugs(request.user)},
        )
    artists, total = catalog.page_artists(**filters, offset=0, limit=_PAGE_SIZE)
    shown = len(artists)
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
                        "role": row["role"],
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
            "role",
            "نقش",
            [(role["slug"], role["title"], role.get("group", "")) for role in catalog.roles_on_artists()],
            filters["role"],
        ),
        ]
    )
    if age:
        groups.append(age)
    return render(
        request,
        "pages/artists.html",
        {
            "artists": artists,
            "page_total": total,
            "page_shown": shown,
            "sort_label": sort_label,
            "sort_options": sort_options,
            "filters": filters,
            "groups": [group for group in groups if group["kind"] in {"text", "age"} or group["options"]],
            "filters_on": any(group.get("selected") for group in groups),
            "art_quick": catalog.art_quick(request, catalog.artist_arts()),
            "quick": catalog.filter_chips(request, catalog.artist_quick()),
            "invite_board": _invite_board(request.user),
            "clear_href": catalog.clear_filters_href(request),
            "bookmarked": _bookmarked_slugs(request.user),
            "intro_stats": catalog.listing_stats()["artists"],
        },
    )


@login_required
@require_POST
def artist_invite(request):
    from honaryaar.accounts import current_profile
    from honaryaar.models import Invite, Opportunity, Profile

    owner = current_profile(request.user)
    artist = get_object_or_404(Profile, slug=request.POST.get("artist", ""))
    if owner is None or artist.pk == owner.pk:
        return JsonResponse({"error": "این دعوت ممکن نیست."}, status=403)
    opportunity = get_object_or_404(
        Opportunity.objects.filter(project__owner=owner),
        pk=request.POST.get("opportunity") or 0,
    )
    _invite, created = Invite.objects.get_or_create(profile=artist, opportunity=opportunity)
    return JsonResponse(
        {
            "ok": True,
            "created": created,
            "invites": opportunity.invites.count(),
        }
    )


def _bookmark_many(request, model):
    from django.contrib.contenttypes.models import ContentType

    from honaryaar.models import Bookmark

    slugs = [slug for slug in request.POST.getlist("slug") if slug][:50]
    content_type = ContentType.objects.get_for_model(model)
    saved = []
    for obj in model.objects.filter(slug__in=slugs):
        _bookmark, created = Bookmark.objects.get_or_create(
            user=request.user,
            content_type=content_type,
            object_id=obj.pk,
        )
        if created:
            saved.append(obj.slug)
    count = len(saved)
    shown = str(count).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
    if count:
        message = f"{shown} مورد نشان شد."
    elif slugs:
        message = "این موردها قبلاً نشان شده بودند."
    else:
        message = "موردی انتخاب نشده."
    return JsonResponse({"ok": True, "saved": saved, "message": message})


@login_required
@require_POST
def bookmark_artists(request):
    from honaryaar.models import Profile

    return _bookmark_many(request, Profile)


@login_required
@require_POST
def bookmark_opportunities(request):
    from honaryaar.models import Opportunity

    return _bookmark_many(request, Opportunity)


@login_required
@require_POST
def apply_many(request):
    from honaryaar.accounts import ensure_profile
    from honaryaar.models import Application, Opportunity, OpportunityStatus

    profile = ensure_profile(request.user)
    if profile is None:
        return JsonResponse({"error": "برای درخواست، پروفایل لازم است."}, status=403)
    slugs = [slug for slug in request.POST.getlist("slug") if slug][:50]
    created = 0
    for opportunity in Opportunity.objects.filter(slug__in=slugs, status=OpportunityStatus.OPEN).select_related("project"):
        if opportunity.project.owner_id == profile.pk:
            continue
        _row, was_created = Application.objects.get_or_create(profile=profile, opportunity=opportunity)
        if was_created:
            created += 1
    shown = str(created).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
    if created:
        message = f"{shown} درخواست ثبت شد."
    elif slugs:
        message = "درخواستی برای ثبت نماند."
    else:
        message = "موردی انتخاب نشده."
    return JsonResponse({"ok": True, "created": created, "message": message})


@login_required
@require_POST
def bookmark_artist(request, slug):
    from honaryaar.models import Profile

    return _toggle_bookmark(request, Profile, slug, reverse("artists"))


@login_required
@require_POST
def bookmark_project(request, slug):
    from honaryaar.models import Project

    return _toggle_bookmark(request, Project, slug, reverse("projects"))


@login_required
@require_POST
def bookmark_opportunity(request, slug):
    from honaryaar.models import Opportunity

    return _toggle_bookmark(request, Opportunity, slug, reverse("opportunities"))


@login_required
@require_POST
def bookmark_remove(request, pk):
    from honaryaar.models import Bookmark

    bookmark = get_object_or_404(Bookmark, pk=pk, user=request.user)
    name = _bookmark_name(bookmark.target, bookmark.content_type.model)
    bookmark.delete()
    return _bookmark_result(request, False, f"{name} از نشان‌شده‌ها حذف شد.", reverse("me-collaborations"))


def artist_detail(request, slug):
    from honaryaar.accounts import current_profile
    from honaryaar.models import Profile

    artist = catalog.artist_by_slug(slug)
    if artist is None:
        raise Http404
    artist["views"] = catalog.note_view(request, Profile, artist["pk"])
    viewer = current_profile(request.user)
    return render(
        request,
        "pages/artist.html",
        {
            "artist": artist,
            "saved": _is_bookmarked(request.user, Profile, slug),
            "can_invite": viewer is None or viewer.slug != slug,
            "invite_board": _invite_board(request.user),
            "report_title": artist["name"],
            "report_action": reverse("report-artist", args=[slug]),
            **report_page_state(request, f"artist:{slug}"),
        },
    )


def _age(raw):
    normalized = raw.strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    return int(normalized) if normalized.isdigit() else None


_PAGE_SIZE = 12
_OPPORTUNITY_PAGE = 8
_PROJECT_PAGE = 6
_ROW_CAP = 4


def _safe_int(raw, default):
    normalized = str(raw or "").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    return int(normalized) if normalized.isdigit() else default


def _catalog_window(request, items, page_size=_PAGE_SIZE):
    """First paint is two full rows. A scroll asks for one more row."""
    total = len(items)
    if request.headers.get("X-Requested-With") == "fetch" and "offset" in request.GET:
        offset = min(max(_safe_int(request.GET.get("offset"), 0), 0), total)
        limit = min(max(_safe_int(request.GET.get("limit"), 1), 1), _ROW_CAP)
        return items[offset:offset + limit], total, offset + limit, True
    shown = items[:page_size]
    return shown, total, len(shown), False


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
        "pay_type": _picked(request, "pay_type"),
        "gender": _picked(request, "gender"),
        "production": _picked(request, "production"),
        "role": _picked(request, "role"),
        "art": _picked(request, "art"),
        "status": _picked(request, "status"),
        "age_from": start if age_active else None,
        "age_to": end if age_active else None,
    }
    sort, sort_label, sort_options = catalog.sort_state(request, "opportunities")
    filters["sort"] = sort
    opportunities, total, shown, partial = _catalog_window(
        request, catalog.list_opportunities(**filters), page_size=_OPPORTUNITY_PAGE
    )
    if partial:
        return render(
            request,
            "components/catalog/opportunity_page.html",
            {"opportunities": opportunities, "bookmarked_opportunities": _bookmarked_slugs(request.user, "opportunity")},
        )
    facets = catalog.opportunity_facets()
    groups = [
        catalog.choice_group("status", "وضعیت", [("open", "باز"), ("closed", "بسته")], filters["status"]),
        catalog.choice_group("city", "شهر", [(city, city) for city in facets["cities"]], filters["city"]),
        catalog.choice_group("role", "نقش", [(role["slug"], role["title"], role.get("group", "")) for role in facets["roles"]], filters["role"]),
        catalog.choice_group("production", "نوع", [(item, item) for item in facets["productions"]], filters["production"]),
        catalog.choice_group("gender", "جنسیت", [(item["value"], item["label"]) for item in facets["genders"]], filters["gender"]),
        catalog.choice_group("paid", "دستمزد", facets["paid"], filters["paid"]),
        catalog.choice_group("pay_type", "نوع دستمزد", facets["pay_type"], filters["pay_type"]),
    ]
    if bounds:
        groups.append(catalog.age_group(floor, ceiling, start, end, age_active))
    return render(
        request,
        "pages/opportunities.html",
        {
            "opportunities": opportunities,
            "page_total": total,
            "page_shown": shown,
            "sort_label": sort_label,
            "sort_options": sort_options,
            "filters": filters,
            "groups": [group for group in groups if group["kind"] in {"text", "age"} or group["options"]],
            "filters_on": any(group.get("selected") for group in groups),
            "art_quick": catalog.art_quick(request, facets["arts"]),
            "quick": catalog.filter_chips(request, catalog.opportunity_quick(facets)),
            "clear_href": catalog.clear_filters_href(request),
            "bookmarked_opportunities": _bookmarked_slugs(request.user, "opportunity"),
            "intro_stats": catalog.listing_stats()["opportunities"],
        },
    )


def opportunity_detail(request, slug):
    from honaryaar.accounts import current_profile
    from honaryaar.models import Application, Opportunity

    opportunity = catalog.opportunity_by_slug(slug)
    if opportunity is None:
        raise Http404
    opportunity["views"] = catalog.note_view(request, Opportunity, opportunity["pk"])
    project = catalog.project_by_slug(opportunity["project"])

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
            "related": catalog.related_opportunities(opportunity),
            "bookmarked_opportunities": _bookmarked_slugs(request.user, "opportunity"),
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
        "production": _picked(request, "production"),
        "status": _picked(request, "status"),
        "start": catalog.parse_user_date(request.GET.get("start", "")),
    }
    filters["start"] = filters["start"].isoformat() if filters["start"] else ""
    sort, sort_label, sort_options = catalog.sort_state(request, "projects")
    filters["sort"] = sort
    projects, total, shown, partial = _catalog_window(
        request, catalog.list_projects(**filters), page_size=_PROJECT_PAGE
    )
    if partial:
        return render(
            request,
            "components/catalog/project_page.html",
            {"projects": projects, "bookmarked_projects": _bookmarked_slugs(request.user, "project")},
        )
    groups = [
        catalog.choice_group("status", "وضعیت", [("casting", "در حال جذب"), ("completed", "اتمام")], filters["status"]),
        {**catalog.choice_group("production", "نوع", [(title, title) for title in catalog.project_categories()], filters["production"]), "plain": True, "open": True},
        catalog.choice_group("city", "شهر", [(city, city) for city in catalog.cities()], filters["city"]),
        catalog.date_group("start", "تاریخ شروع از", filters["start"]),
    ]
    return render(
        request,
        "pages/projects.html",
        {
            "projects": projects,
            "page_total": total,
            "page_shown": shown,
            "sort_label": sort_label,
            "sort_options": sort_options,
            "filters": filters,
            "groups": groups,
            "filters_on": any(group.get("selected") for group in groups),
            "art_quick": catalog.art_quick(request, catalog.arts()),
            "quick": catalog.filter_chips(request, [("تهران", {"city": "تهران"})]),
            "clear_href": catalog.clear_filters_href(request),
            "bookmarked_projects": _bookmarked_slugs(request.user, "project"),
            "intro_stats": catalog.listing_stats()["projects"],
        },
    )


def project_detail(request, slug):
    from honaryaar.models import Application, Project

    project = catalog.project_by_slug(slug)
    if project is None:
        raise Http404
    project["views"] = catalog.note_view(request, Project, project["pk"])
    calls = catalog.opportunities_for_project(slug)
    applied = Application.objects.filter(opportunity__project__slug=slug).count()
    return render(
        request,
        "pages/project.html",
        {
            "project": project,
            "saved": _is_bookmarked(request.user, Project, slug),
            "opportunities": [item for item in calls if item["status"] == "open"],
            "open_calls": sum(item["status"] == "open" for item in calls),
            "closed_calls": sum(item["status"] == "closed" for item in calls),
            "applications": catalog.persian_number(catalog.round_up_five(applied)),
            "timeline": catalog.project_timeline(project, calls),
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
    path = settings.BASE_DIR / "honaryaar" / "static" / "manifest.webmanifest"
    response = FileResponse(path.open("rb"), content_type="application/manifest+json")
    # Tiny static PWA file — let browsers, Vercel, and Cloudflare keep it.
    response["Cache-Control"] = "public, max-age=86400, s-maxage=604800, stale-while-revalidate=86400"
    response["CDN-Cache-Control"] = "public, max-age=604800"
    return response


def service_worker(request):
    path = settings.BASE_DIR / "honaryaar" / "static" / "sw.js"
    response = FileResponse(path.open("rb"), content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response
