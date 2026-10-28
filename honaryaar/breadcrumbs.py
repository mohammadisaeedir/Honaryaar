from django.urls import reverse


def _text(value, *keys):
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in keys:
            found = value.get(key)
            if found:
                return str(found).strip()
        return ""
    for key in keys:
        found = getattr(value, key, None)
        if found:
            return str(found).strip()
    return ""


def _trail(home, *parts):
    items = [home]
    for part in parts:
        if not part:
            continue
        label, href = part
        label = str(label or "").strip()
        if not label:
            continue
        items.append({"label": label, "href": href or ""})
    if len(items) > 1:
        items[-1]["href"] = ""
    return items


def crumbs(context):
    request = context.get("request")
    match = getattr(request, "resolver_match", None) if request else None
    if match is None or match.url_name in {None, "home"}:
        return []
    name = match.url_name
    home = {"label": "خانه", "href": reverse("home")}
    page_title = str(context.get("page_title") or "").strip()
    title = str(context.get("title") or "").strip()

    pages = {
        "artists": "هنرمندان",
        "opportunities": "فراخوان‌ها",
        "projects": "پروژه‌ها",
        "search": "جستجو",
        "login": "ورود",
        "about": "درباره ما",
        "post-call": "ثبت رایگان فراخوان",
        "magazine": "مجله هنری",
        "terms": "قوانین و مقررات",
        "contact": "تماس با ما",
        "sitemap": "سایت مپ",
        "me-profile": "پروفایل",
    }
    if name in pages:
        label = page_title or pages[name]
        if name == "search" and context.get("query"):
            return _trail(home, ("جستجو", reverse("search")), (context["query"], ""))
        return _trail(home, (label, ""))

    if name == "login-code":
        return _trail(home, ("ورود", reverse("login")), ("کد ورود", ""))

    if name == "artist":
        artist = context.get("artist") or {}
        label = _text(artist, "legal_name", "name") or "هنرمند"
        return _trail(home, ("هنرمندان", reverse("artists")), (label, ""))

    if name == "project":
        project = context.get("project") or {}
        return _trail(home, ("پروژه‌ها", reverse("projects")), (_text(project, "title") or "پروژه", ""))

    if name == "opportunity":
        opportunity = context.get("opportunity") or {}
        project = context.get("project") or {}
        project_part = None
        if project.get("slug"):
            project_part = (project.get("title") or "پروژه", reverse("project", args=[project["slug"]]))
        return _trail(
            home,
            ("فراخوان‌ها", reverse("opportunities")),
            project_part,
            (_text(opportunity, "title") or "فراخوان", ""),
        )

    profile = ("پروفایل", reverse("me-profile"))
    account_lists = {
        "me-projects": "پروژه‌ها",
        "me-applications": "درخواست‌های من",
        "me-invites": "دعوت‌ها",
        "me-collaborations": "همکاری‌ها",
        "me-tickets": "پشتیبانی",
    }
    if name in account_lists:
        return _trail(home, profile, (page_title or account_lists[name], ""))

    account_details = {
        "me-application": ("درخواست‌های من", "me-applications"),
        "me-invite": ("دعوت‌ها", "me-invites"),
        "me-collaboration": ("همکاری‌ها", "me-collaborations"),
    }
    if name in account_details:
        label, parent = account_details[name]
        return _trail(home, profile, (label, reverse(parent)), (title or "جزئیات", ""))

    if name == "me-project-new":
        return _trail(home, profile, ("پروژه‌ها", reverse("me-projects")), ("ساخت پروژه", ""))

    if name == "me-project":
        project = context.get("project")
        return _trail(
            home,
            profile,
            ("پروژه‌ها", reverse("me-projects")),
            (_text(project, "title") or "پروژه", ""),
        )

    if name == "me-ticket":
        ticket = context.get("ticket")
        label = _text(ticket, "kind_reason_label") or "تیکت"
        return _trail(home, profile, ("پشتیبانی", reverse("me-tickets")), (label, ""))

    reports = {
        "report-artist": ("هنرمندان", "artists"),
        "report-opportunity": ("فراخوان‌ها", "opportunities"),
        "report-project": ("پروژه‌ها", "projects"),
    }
    if name in reports:
        label, parent = reports[name]
        subject = title or context.get("report_title") or ""
        back = context.get("back") or reverse(parent)
        return _trail(home, (label, reverse(parent)), (subject, back) if subject else None, ("گزارش", ""))

    return _trail(home, (page_title or title or "صفحه", ""))
