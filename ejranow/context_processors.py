from pathlib import Path

from django.conf import settings

from ejranow.catalog import footer_shortcuts, search_shortcuts


def footer(_request):
    data = footer_shortcuts()
    data.update(search_shortcuts())
    return data


def assets(_request):
    css_dir = Path(settings.BASE_DIR) / "ejranow" / "static" / "css"
    try:
        version = max(int(path.stat().st_mtime) for path in css_dir.glob("*.css"))
    except (OSError, ValueError):
        version = 1
    return {"asset_v": version}
