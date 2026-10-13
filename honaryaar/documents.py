from datetime import date
from pathlib import Path

DOCUMENTS_DIR = Path(__file__).resolve().parent / "documents"

DOCUMENTS = [
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


def document_path(slug):
    match = next((item for item in DOCUMENTS if item["slug"] == slug), None)
    if match is None:
        return None
    path = (DOCUMENTS_DIR / match["filename"]).resolve()
    if DOCUMENTS_DIR.resolve() not in path.parents or not path.is_file():
        return None
    return path
