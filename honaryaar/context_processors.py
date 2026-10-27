from pathlib import Path

from django.conf import settings

from honaryaar.catalog import arts, listing_stats, page_chrome


def footer(_request):
    return page_chrome()


def assets(request):
    from honaryaar.data_source import preview_active, switch_visible

    css_dir = Path(settings.BASE_DIR) / "honaryaar" / "static" / "css"
    try:
        version = max(int(path.stat().st_mtime) for path in css_dir.glob("*.css"))
    except (OSError, ValueError):
        version = 1
    unread = 0
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        from honaryaar.models import InAppNotification

        unread = InAppNotification.objects.filter(user=user, is_read=False).count()
    from honaryaar.fcm import web_config
    import json

    firebase = web_config() if user is not None and getattr(user, "is_authenticated", False) else None
    return {
        "asset_v": version,
        "production_preview": preview_active(),
        "data_source_switch": switch_visible(request),
        "notification_unread": unread,
        "push_enabled": bool(firebase),
        "push_firebase_json": json.dumps(firebase or {}),
    }


def catalog_boot(_request):
    """Chrome for soft-nav list boots: title, stats, and art chips without waiting on cards."""
    stats = listing_stats()
    chips = [
        {"slug": item["slug"], "label": item["title"], "href": "", "active": False}
        for item in arts()
    ]

    def with_href(path):
        return [
            {**chip, "href": f"{path}?art={chip['slug']}"}
            for chip in chips
        ]

    return {
        "catalog_boot": {
            "projects": {
                "kind": "projects",
                "title": "پروژه‌ها",
                "description": "هر پروژه می‌تواند چند نقش باز داشته باشد.",
                "action": "/projects/",
                "search_label": "جستجو در پروژه‌ها",
                "placeholder": "نام پروژه یا شهر",
                "intro_stats": stats["projects"],
                "art_quick": with_href("/projects/"),
            },
            "artists": {
                "kind": "artists",
                "title": "هنرمندان",
                "description": "نام، عکس و نقش هر کس. نقش‌ها از داده می‌آیند و فقط به بازیگر محدود نیستند.",
                "action": "/artists/",
                "search_label": "جستجو در هنرمندان",
                "placeholder": "نام یا نقش",
                "intro_stats": stats["artists"],
                "art_quick": with_href("/artists/"),
            },
            "opportunities": {
                "kind": "opportunities",
                "title": "فراخوان‌ها",
                "description": "نقش، شهر و پروژه را یک‌جا ببینید.",
                "action": "/opportunities/",
                "search_label": "جستجو در فرصت‌ها",
                "placeholder": "نقش، شهر یا پروژه",
                "intro_stats": stats["opportunities"],
                "art_quick": with_href("/opportunities/"),
            },
        }
    }
