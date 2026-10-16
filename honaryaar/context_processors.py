from pathlib import Path

from django.conf import settings

from honaryaar.catalog import footer_shortcuts, search_shortcuts


def footer(_request):
    data = footer_shortcuts()
    data.update(search_shortcuts())
    return data


def assets(request):
    from honaryaar.data_source import preview_active, switch_visible

    css_dir = Path(settings.BASE_DIR) / "honaryaar" / "static" / "css"
    try:
        version = max(int(path.stat().st_mtime) for path in css_dir.glob("*.css"))
    except (OSError, ValueError):
        version = 1
    return {
        "asset_v": version,
        "production_preview": preview_active(),
        "data_source_switch": switch_visible(request),
    }
