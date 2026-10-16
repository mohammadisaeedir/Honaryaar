from datetime import date, datetime
from pathlib import Path

from django.utils import timezone

DOCUMENTS_DIR = Path(__file__).resolve().parent / "documents"

DOCUMENTS = [
    {
        "slug": "erd",
        "title": "Entity relationship",
        "live": True,
    },
    {
        "slug": "artist-network-discovery",
        "title": "Artist network discovery",
        "filename": "artist-network-discovery.html",
        "added": date(2026, 10, 3),
    },
    {
        "slug": "on-site-discovery-v1",
        "title": "On-site discovery V1",
        "filename": "on-site-discovery-v1.html",
        "added": date(2026, 10, 3),
    },
]


def document_added(item):
    if item.get("live"):
        import honaryaar.models as model_module

        stamp = Path(model_module.__file__).stat().st_mtime
        return datetime.fromtimestamp(stamp, tz=timezone.get_current_timezone()).date()
    return item["added"]


def document_path(slug):
    match = next((item for item in DOCUMENTS if item["slug"] == slug), None)
    if match is None or match.get("live"):
        return None
    path = (DOCUMENTS_DIR / match["filename"]).resolve()
    if DOCUMENTS_DIR.resolve() not in path.parents or not path.is_file():
        return None
    return path
