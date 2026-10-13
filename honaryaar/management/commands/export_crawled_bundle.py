"""Export indexed crawled profiles to a folder outside the repo.

Reads the database and storage objects only. Writes bundle.json, bundle-meta.json,
and photo files. Never prints storage keys, ids, or secrets.
"""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import Prefetch
from django.utils import timezone
from PIL import Image

from honaryaar.media_files import EXT, detect
from honaryaar.models import Credit, Profile, ProfileContact, ProfileRole, ProfileStatus
from honaryaar.storage import ParsPackBackend, get_backend, reset_backend

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_PILOTS = {
    "khabgardesahne",
    "hesunhooshdar",
    "alifaridani",
    "abbasimani",
    "farshidjafari",
    "rezaghasemi",
    "faezehfardi",
    "ahsan-rzvanian",
    "mohammad-lalh-zari",
    "abolfazl-jvkar",
}


class Command(BaseCommand):
    help = "Export indexed crawled profiles and their photos to a local bundle."

    def add_arguments(self, parser):
        parser.add_argument("--slugs-file", required=True)
        parser.add_argument("--out-dir", required=True)

    def handle(self, *args, **options):
        _refuse_remote()
        _read_only_session()
        out_dir = _prepare_out_dir(options["out_dir"])
        slugs = _load_slugs(options["slugs_file"])
        profiles = _load_profiles(slugs)
        backend = _backend()
        remote_name = type(backend).__name__
        self.stdout.write(f"storage\t{remote_name}")
        rows = []
        notes = []
        for slug in slugs:
            profile = profiles.get(slug)
            if profile is None:
                notes.append(f"{slug}\tmissing from database")
                self.stdout.write(notes[-1])
                continue
            if profile.status != ProfileStatus.INDEXED:
                notes.append(f"{slug}\tstatus is {profile.status}")
                self.stdout.write(notes[-1])
                continue
            photo, photo_note = _photo(profile, backend, slug, out_dir)
            if photo_note:
                notes.append(f"{slug}\t{photo_note}")
                self.stdout.write(notes[-1])
            rows.append(_row(profile, photo))
        bundle_path = out_dir / "bundle.json"
        _write_json(bundle_path, rows)
        bundle_sha = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
        meta = _meta(rows, bundle_sha)
        _write_json(out_dir / "bundle-meta.json", meta)
        self.stdout.write(f"bundle\t{bundle_path}")
        self.stdout.write(f"meta\t{out_dir / 'bundle-meta.json'}")
        _verify(self.stdout, slugs, rows, out_dir, bundle_sha)
        size = sum(path.stat().st_size for path in out_dir.rglob("*") if path.is_file())
        self.stdout.write(f"folder_bytes\t{size}")


def _refuse_remote():
    if os.environ.get("VERCEL") == "1":
        raise CommandError("refusing to run when VERCEL=1")
    host = (settings.DATABASES["default"].get("HOST") or "").strip()
    if host not in {"localhost", "127.0.0.1"}:
        raise CommandError(f"refusing database host {host or '(empty)'}")


def _read_only_session():
    connection.ensure_connection()
    raw = connection.connection
    if hasattr(raw, "set_session"):
        raw.set_session(readonly=True, autocommit=True)


def _prepare_out_dir(raw):
    out_dir = Path(raw).expanduser().resolve()
    repo = Path(settings.BASE_DIR).resolve()
    if out_dir == repo or repo in out_dir.parents:
        raise CommandError("out dir must be outside the repo")
    if out_dir.exists():
        if any(out_dir.iterdir()):
            raise CommandError("out dir exists and is not empty")
    else:
        out_dir.mkdir(parents=True)
    return out_dir


def _load_slugs(raw):
    path = Path(raw).expanduser()
    if not path.is_file():
        raise CommandError(f"slugs file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise CommandError("slugs file must be a list of slugs or objects with slug")
    slugs = []
    for item in payload:
        if isinstance(item, str) and item.strip():
            slug = item.strip()
        elif isinstance(item, dict) and isinstance(item.get("slug"), str) and item["slug"].strip():
            slug = item["slug"].strip()
        else:
            raise CommandError("slugs file rows must be slugs or objects with slug")
        if not _SLUG.match(slug):
            raise CommandError(f"slug is not clean ASCII: {slug}")
        slugs.append(slug)
    return slugs


def _load_profiles(slugs):
    role_query = ProfileRole.objects.select_related("role").order_by("id")
    credit_query = Credit.objects.select_related("role").order_by("id")
    contact_query = ProfileContact.objects.order_by("position", "id")
    found = Profile.objects.select_related("user", "city").prefetch_related(
        Prefetch("profile_roles", queryset=role_query),
        Prefetch("credits", queryset=credit_query),
        Prefetch("contacts", queryset=contact_query),
    ).filter(slug__in=slugs)
    return {profile.slug: profile for profile in found}


def _backend():
    reset_backend()
    return get_backend()


def _row(profile, photo):
    return {
        "slug": profile.slug,
        "username": profile.user.username,
        "name": profile.name,
        "about": profile.about,
        "arts": list(profile.arts or []),
        "status": profile.status,
        "birth_date": profile.birth_date.isoformat() if profile.birth_date else None,
        "gender": profile.gender,
        "city_slug": profile.city.slug if profile.city_id else None,
        "roles": [
            {"role_slug": link.role.slug, "is_primary": link.is_primary}
            for link in profile.profile_roles.all()
        ],
        "credits": [
            {
                "title": credit.title,
                "role_name": credit.role_name,
                "role_slug": credit.role.slug if credit.role_id else None,
                "year": credit.year,
            }
            for credit in profile.credits.all()
        ],
        "contacts": [
            {
                "kind": contact.kind,
                "value": contact.value,
                "is_public": contact.is_public,
                "source": contact.source,
                "position": contact.position,
            }
            for contact in profile.contacts.all()
        ],
        "photo": photo,
    }


def _photo(profile, backend, slug, out_dir):
    image_key = profile.list_image.name or ""
    thumb_key = profile.list_thumb.name or ""
    if not image_key and not thumb_key:
        return None, ""
    if not isinstance(backend, ParsPackBackend):
        missing = [key for key in (image_key, thumb_key) if key and backend.head(key) is None]
        if missing or not image_key or not thumb_key:
            return None, "backend is not ParsPack and the photo is not on local disk"
    if not image_key or not thumb_key:
        return None, "photo is missing an original or a thumb"
    try:
        original = backend.read(image_key)
        thumb = backend.read(thumb_key)
    except Exception as exc:
        return None, f"photo read failed ({type(exc).__name__})"
    try:
        _kind, content_type = detect(original, "photo")
    except Exception as exc:
        return None, f"original is not a supported image ({type(exc).__name__})"
    ext = EXT.get(content_type, "")
    if ext not in {".jpg", ".png", ".webp", ".gif"}:
        return None, "original type has no image extension"
    folder = out_dir / "files" / slug
    folder.mkdir(parents=True, exist_ok=True)
    original_name = f"files/{slug}/original{ext}"
    thumb_name = f"files/{slug}/thumb.jpg"
    (out_dir / original_name).write_bytes(original)
    (out_dir / thumb_name).write_bytes(thumb)
    return {
        "list_public_acl": profile.list_public_acl,
        "original": {
            "file": original_name,
            "bytes": len(original),
            "sha256": hashlib.sha256(original).hexdigest(),
            "content_type": content_type,
        },
        "thumb": {
            "file": thumb_name,
            "bytes": len(thumb),
            "sha256": hashlib.sha256(thumb).hexdigest(),
        },
    }, ""


def _meta(rows, bundle_sha):
    return {
        "exported_at": timezone.now().isoformat(),
        "git_commit": _git_commit(),
        "migrations_last_10": _recent_migrations(),
        "counts": _counts(rows),
        "bundle_sha256": bundle_sha,
    }


def _counts(rows):
    return {
        "profiles": len(rows),
        "credits": sum(len(row["credits"]) for row in rows),
        "roles": sum(len(row["roles"]) for row in rows),
        "contacts": sum(len(row["contacts"]) for row in rows),
        "photos": sum(1 for row in rows if row["photo"]),
    }


def _git_commit():
    result = subprocess.run(
        ["git", "-C", str(settings.BASE_DIR), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _recent_migrations():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT name FROM django_migrations WHERE app = %s ORDER BY id DESC LIMIT 10",
            ["honaryaar"],
        )
        names = [row[0] for row in cursor.fetchall()]
    names.reverse()
    return names


def _write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _verify(stdout, slugs, rows, out_dir, bundle_sha):
    by_slug = {row["slug"]: row for row in rows}
    db_rows = []
    mismatches = []
    file_problems = []
    duplicate_contacts = []
    for slug in slugs:
        profile = Profile.objects.filter(slug=slug, status=ProfileStatus.INDEXED).first()
        row = by_slug.get(slug)
        if profile is None or row is None:
            mismatches.append(slug)
            continue
        db_counts = {
            "credits": profile.credits.count(),
            "roles": profile.profile_roles.count(),
            "contacts": profile.contacts.count(),
            "birth": 1 if profile.birth_date else 0,
            "photo": 1 if profile.list_image.name else 0,
        }
        bundle_counts = {
            "credits": len(row["credits"]),
            "roles": len(row["roles"]),
            "contacts": len(row["contacts"]),
            "birth": 1 if row["birth_date"] else 0,
            "photo": 1 if row["photo"] else 0,
        }
        db_rows.append(db_counts)
        if db_counts != bundle_counts:
            mismatches.append(slug)
        seen = set()
        for contact in row["contacts"]:
            key = (contact["kind"], contact["value"])
            if key in seen:
                duplicate_contacts.append(slug)
            seen.add(key)
        photo = row["photo"]
        if not photo:
            continue
        for part in (photo["original"], photo["thumb"]):
            path = out_dir / part["file"]
            if not path.is_file():
                file_problems.append(f"{slug} missing file")
                continue
            payload = path.read_bytes()
            if hashlib.sha256(payload).hexdigest() != part["sha256"] or len(payload) != part["bytes"]:
                file_problems.append(f"{slug} sha256")
                continue
            try:
                with Image.open(path) as image:
                    image.load()
            except Exception:
                file_problems.append(f"{slug} pillow")
    db_totals = _sum_counts(db_rows)
    bundle_totals = _counts(rows)
    on_disk = hashlib.sha256((out_dir / "bundle.json").read_bytes()).hexdigest()
    pilots = [slug for slug in slugs if slug in _PILOTS]
    newcomers = [slug for slug in slugs if slug not in _PILOTS]
    stdout.write("metric\tdb\tbundle")
    stdout.write(f"profiles\t{len(db_rows)}\t{bundle_totals['profiles']}")
    for key in ("credits", "roles", "contacts"):
        stdout.write(f"{key}\t{db_totals[key]}\t{bundle_totals[key]}")
    stdout.write(f"photos\t{db_totals['photo']}\t{bundle_totals['photos']}")
    stdout.write(f"birth_dates\t{db_totals['birth']}\t{sum(1 for row in rows if row['birth_date'])}")
    stdout.write(f"pilots\t{len(pilots)}\t{sum(1 for slug in pilots if slug in by_slug)}")
    stdout.write(f"new\t{len(newcomers)}\t{sum(1 for slug in newcomers if slug in by_slug)}")
    stdout.write(f"sha256_match\t{on_disk == bundle_sha}")
    stdout.write(f"per_slug_mismatches\t{mismatches or 'none'}")
    stdout.write(f"file_problems\t{file_problems or 'none'}")
    stdout.write(f"duplicate_contacts\t{duplicate_contacts or 'none'}")
    roles = sorted({item["role_slug"] for row in rows for item in row["roles"]})
    credit_roles = sorted({item["role_slug"] for row in rows for item in row["credits"] if item["role_slug"]})
    cities = sorted({row["city_slug"] for row in rows if row["city_slug"]})
    stdout.write(f"profile_role_slugs\t{', '.join(roles) or '-'}")
    stdout.write(f"credit_role_slugs\t{', '.join(credit_roles) or '-'}")
    stdout.write(f"city_slugs\t{', '.join(cities) or '-'}")
    stdout.write(f"profiles_without_city\t{sum(1 for row in rows if not row['city_slug'])}")


def _sum_counts(rows):
    totals = {"credits": 0, "roles": 0, "contacts": 0, "birth": 0, "photo": 0}
    for row in rows:
        for key in totals:
            totals[key] += row[key]
    return totals
