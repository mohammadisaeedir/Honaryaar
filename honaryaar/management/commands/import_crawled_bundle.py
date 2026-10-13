"""Import a crawled-profile bundle into the target database.

Dry run unless --apply. Without --production the database host must be local.
With --production the command repoints the default connection at PROD_DATABASE_URL
and never opens a second database alias.
"""

import hashlib
import json
import os
import uuid
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone

from honaryaar.media_files import EXT, detect
from honaryaar.media_service import assign_file
from honaryaar.models import (
    City,
    ContactKind,
    Credit,
    Profile,
    ProfileContact,
    ProfileRole,
    ProfileStatus,
    Role,
)
from honaryaar.storage import ParsPackBackend, get_backend, reset_backend, storage_prefix


class Command(BaseCommand):
    help = "Import a crawled profile bundle. Writes nothing unless --apply."

    def add_arguments(self, parser):
        parser.add_argument("--bundle-dir", required=True)
        parser.add_argument("--only-slug", action="append", dest="only_slug")
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--rollback", default="")
        parser.add_argument("--skip-photos", action="store_true")
        parser.add_argument("--production", action="store_true")
        parser.add_argument("--expect-host", default="")

    def handle(self, *args, **options):
        bundle_dir = Path(options["bundle_dir"]).expanduser().resolve()
        if not bundle_dir.is_dir():
            raise CommandError("bundle dir is not a directory")
        _prepare_database(options)
        host, name, leaf = _announce(self.stdout)
        if options["rollback"]:
            _rollback(
                self.stdout,
                Path(options["rollback"]).expanduser().resolve(),
                host,
                name,
                options["apply"],
            )
            return
        rows = _load_bundle(bundle_dir, options["only_slug"] or [])
        roles, cities = _preconditions(self.stdout, rows)
        _import_rows(
            self.stdout,
            bundle_dir,
            rows,
            roles,
            cities,
            host,
            name,
            options["apply"],
            options["skip_photos"],
        )


def _prepare_database(options):
    if options["production"]:
        params = _production_params(options["expect_host"])
        if not options["skip_photos"]:
            _require_photo_storage("production", require_parspack=True)
        _repoint(params)
        return
    host = (connections["default"].settings_dict.get("HOST") or "").strip()
    if host not in {"localhost", "127.0.0.1"}:
        raise CommandError("database host must be localhost or 127.0.0.1")
    if not options["skip_photos"]:
        _require_photo_storage("dev", require_parspack=False)


def _production_params(expect_host):
    raw = os.environ.get("PROD_DATABASE_URL", "").strip()
    if not raw:
        raise CommandError("PROD_DATABASE_URL is not set")
    parsed = urlparse(raw)
    database = unquote((parsed.path or "").lstrip("/"))
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname or not database:
        raise CommandError("PROD_DATABASE_URL could not be parsed")
    expect = (expect_host or "").strip()
    if not expect:
        raise CommandError("--expect-host is required with --production")
    if expect != parsed.hostname:
        raise CommandError("--expect-host does not match the database host")
    if os.environ.get("ALLOW_PROD_IMPORT") != "yes":
        raise CommandError("ALLOW_PROD_IMPORT must be yes")
    sslmode = (parse_qs(parsed.query).get("sslmode") or ["require"])[0]
    return {
        "NAME": database,
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname,
        "PORT": str(parsed.port or 5432),
        "OPTIONS": {"sslmode": sslmode},
    }


def _repoint(params):
    wrapper = connections["default"]
    wrapper.close()
    wrapper.settings_dict["ENGINE"] = "django.db.backends.postgresql"
    wrapper.settings_dict["NAME"] = params["NAME"]
    wrapper.settings_dict["USER"] = params["USER"]
    wrapper.settings_dict["PASSWORD"] = params["PASSWORD"]
    wrapper.settings_dict["HOST"] = params["HOST"]
    wrapper.settings_dict["PORT"] = params["PORT"]
    wrapper.settings_dict["OPTIONS"] = params["OPTIONS"]
    wrapper.close()


def _require_photo_storage(expected, require_parspack):
    prefix = (settings.MEDIA_STORAGE_PREFIX or "").strip().strip("/")
    if prefix != expected:
        raise CommandError(f"MEDIA_STORAGE_PREFIX must be {expected}")
    if not require_parspack:
        return
    reset_backend()
    if not isinstance(get_backend(), ParsPackBackend):
        raise CommandError("ParsPack storage is required")


def _announce(stdout):
    db = connections["default"].settings_dict
    host = (db.get("HOST") or "").strip()
    name = db.get("NAME") or ""
    stdout.write(f"target\t{host}\t{name}")
    leaf, missing = _migration_leaf()
    stdout.write(f"leaf\t{leaf}")
    if missing:
        raise CommandError("honaryaar migrations are not fully applied")
    stdout.write(f"profiles\t{Profile.objects.count()}")
    return host, name, leaf


def _migration_leaf():
    connection = connections["default"]
    loader = MigrationLoader(connection, ignore_no_migrations=False)
    leaves = [node for node in loader.graph.leaf_nodes() if node[0] == "honaryaar"]
    if len(leaves) != 1:
        raise CommandError("honaryaar migrations do not have one leaf")
    leaf = leaves[0]
    applied = MigrationRecorder(connection).applied_migrations()
    missing = [node for node in loader.graph.forwards_plan(leaf) if node[0] == "honaryaar" and node not in applied]
    return leaf[1], missing


def _load_bundle(bundle_dir, only):
    path = bundle_dir / "bundle.json"
    if not path.is_file():
        raise CommandError("bundle.json is missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise CommandError("bundle.json must be a list")
    wanted = set(only)
    rows = []
    seen = set()
    for item in payload:
        if not isinstance(item, dict) or not isinstance(item.get("slug"), str) or not item["slug"].strip():
            raise CommandError("bundle rows must be objects with a slug")
        slug = item["slug"].strip()
        if slug in seen:
            raise CommandError(f"duplicate slug in bundle: {slug}")
        seen.add(slug)
        if wanted and slug not in wanted:
            continue
        rows.append(item)
    unknown = sorted(wanted - seen)
    if unknown:
        raise CommandError(f"slug is not in the bundle: {unknown[0]}")
    return rows


def _preconditions(stdout, rows):
    role_slugs = set()
    city_slugs = set()
    kinds = set()
    for row in rows:
        for link in row.get("roles") or []:
            slug = (link or {}).get("role_slug") or ""
            if slug:
                role_slugs.add(slug)
        for credit in row.get("credits") or []:
            slug = (credit or {}).get("role_slug") or ""
            if slug:
                role_slugs.add(slug)
        city = row.get("city_slug") or ""
        if city:
            city_slugs.add(city)
        for contact in row.get("contacts") or []:
            kind = (contact or {}).get("kind") or ""
            if kind:
                kinds.add(kind)
    known_roles = {role.slug: role for role in Role.objects.filter(slug__in=role_slugs)}
    known_cities = {city.slug: city for city in City.objects.filter(slug__in=city_slugs)}
    known_kinds = set(ContactKind.values)
    missing_roles = sorted(role_slugs - set(known_roles))
    missing_cities = sorted(city_slugs - set(known_cities))
    missing_kinds = sorted(kinds - known_kinds)
    for slug in missing_roles:
        stdout.write(f"missing role\t{slug}")
    for slug in missing_cities:
        stdout.write(f"missing city\t{slug}")
    for kind in missing_kinds:
        stdout.write(f"missing contact kind\t{kind}")
    if missing_roles or missing_cities or missing_kinds:
        raise CommandError("catalog is missing rows the bundle needs")
    return known_roles, known_cities


def _import_rows(stdout, bundle_dir, rows, roles, cities, host, name, apply, skip_photos):
    records = []
    created = would = skipped = conflicts = failed = 0
    for row in rows:
        slug = row["slug"].strip()
        counts = _row_counts(row, skip_photos)
        existing = Profile.objects.filter(slug=slug).only("id").first()
        if existing is not None:
            skipped += 1
            stdout.write(_status_line("skip (exists)", slug, counts))
            continue
        username = f"idx-{slug}"
        if len(username) > 150:
            failed += 1
            stdout.write(_status_line("failed", slug, counts) + "\tusername too long")
            continue
        taken = get_user_model().objects.filter(username=username).first()
        if taken is not None and not Profile.objects.filter(user=taken).exists():
            conflicts += 1
            stdout.write(_status_line("skip (conflict)", slug, counts))
            continue
        if taken is not None:
            skipped += 1
            stdout.write(_status_line("skip (exists)", slug, counts))
            continue
        if not apply:
            would += 1
            stdout.write(_status_line("would create", slug, counts))
            continue
        try:
            record, line = _create_one(bundle_dir, row, roles, cities, skip_photos)
        except Exception as exc:
            failed += 1
            detail = str(exc) if isinstance(exc, CommandError) else exc.__class__.__name__
            stdout.write(_status_line("failed", slug, counts) + f"\t{detail}")
            continue
        records.append(record)
        created += 1
        stdout.write(line)
    if apply:
        prefix = "" if skip_photos else storage_prefix()
        manifest = _write_manifest(bundle_dir, host, name, prefix, records)
        stdout.write(f"manifest\t{manifest}")
    stdout.write(
        "totals\t"
        f"would_create={would}\tcreated={created}\tskip={skipped}\t"
        f"conflict={conflicts}\tfailed={failed}\tapply={int(bool(apply))}"
    )


def _create_one(bundle_dir, row, roles, cities, skip_photos):
    slug = row["slug"].strip()
    username = f"idx-{slug}"
    counts = _row_counts(row, skip_photos)
    city_slug = row.get("city_slug") or ""
    born = _birth(row.get("birth_date"))
    User = get_user_model()
    with transaction.atomic():
        user = User(username=username, email="", is_staff=False, is_superuser=False)
        user.set_unusable_password()
        user.save()
        profile = Profile(
            user=user,
            slug=slug,
            name=row.get("name") or "",
            about=row.get("about") or "",
            arts=list(row.get("arts") or []),
            status=ProfileStatus.INDEXED,
            birth_date=born,
            gender=row.get("gender") or "",
            city=cities.get(city_slug) if city_slug else None,
        )
        profile.save()
        role_rows = [
            ProfileRole(
                profile=profile,
                role=roles[item["role_slug"]],
                is_primary=bool(item.get("is_primary")),
            )
            for item in row.get("roles") or []
        ]
        if role_rows:
            role_rows = ProfileRole.objects.bulk_create(role_rows)
        credit_rows = [
            Credit(
                profile=profile,
                title=item.get("title") or "",
                role=roles.get(item.get("role_slug") or ""),
                role_name=item.get("role_name") or "",
                year="" if item.get("year") in (None, "") else str(item.get("year")),
            )
            for item in row.get("credits") or []
        ]
        if credit_rows:
            credit_rows = Credit.objects.bulk_create(credit_rows)
        contact_rows = []
        for item in row.get("contacts") or []:
            contact = ProfileContact(
                profile=profile,
                kind=item["kind"],
                value=item.get("value") or "",
                is_public=bool(item.get("is_public")),
                source=item.get("source") or "",
                position=item.get("position") or 0,
            )
            contact.full_clean()
            contact.save()
            contact_rows.append(contact)
        keys = []
        try:
            if row.get("photo") and not skip_photos:
                keys = _store_photo(bundle_dir, profile, row["photo"])
            _pin_slug(profile, slug)
        except Exception:
            if keys:
                reset_backend()
                _delete_keys(get_backend(), keys, storage_prefix())
            raise
    return (
        {
            "slug": slug,
            "username": username,
            "user_id": user.id,
            "profile_id": profile.id,
            "credit_ids": [item.id for item in credit_rows],
            "contact_ids": [item.id for item in contact_rows],
            "role_ids": [item.id for item in role_rows],
            "keys": keys,
        },
        _status_line("created", slug, counts),
    )


def _pin_slug(profile, slug):
    """Profile.save copies the username onto the slug. Put the public address back."""
    if profile.slug == slug:
        return
    Profile.objects.filter(pk=profile.pk).update(slug=slug)
    profile.slug = slug


def _birth(value):
    if not value:
        return None
    return date.fromisoformat(str(value)[:10])


def _store_photo(bundle_dir, profile, photo):
    original = _read_part(bundle_dir, photo.get("original") or {})
    thumb = _read_part(bundle_dir, photo.get("thumb") or {})
    _kind, content_type = detect(original, "photo")
    detect(thumb, "photo")
    ext = EXT.get(content_type)
    if ext not in {".jpg", ".png", ".webp", ".gif"}:
        raise CommandError("unsupported image type")
    prefix = storage_prefix()
    token = uuid.uuid4()
    key = f"{prefix}/profiles/{profile.id}/{token}{ext}"
    thumb_key = f"{prefix}/profiles/{profile.id}/{token}-thumb.jpg"
    reset_backend()
    backend = get_backend()
    stored = []
    try:
        backend.put_bytes(key, original, content_type)
        stored.append(key)
        backend.put_bytes(thumb_key, thumb, "image/jpeg")
        stored.append(thumb_key)
        original_public = backend.set_public(key)
        thumb_public = backend.set_public(thumb_key)
        want_public = bool(photo.get("list_public_acl"))
        if want_public and not (original_public and thumb_public):
            raise CommandError("set_public failed")
        assign_file(profile, "list_image", key)
        assign_file(profile, "list_thumb", thumb_key)
        profile.list_public_acl = want_public and original_public and thumb_public
        profile.save(update_fields=["list_image", "list_thumb", "list_public_acl"])
    except Exception:
        _delete_keys(backend, stored, prefix)
        raise
    return stored


def _read_part(bundle_dir, part):
    rel = part.get("file") or ""
    path = (bundle_dir / rel).resolve()
    root = bundle_dir.resolve()
    if path != root and root not in path.parents:
        raise CommandError("photo path escapes the bundle")
    if not path.is_file():
        raise CommandError("photo file is missing")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != (part.get("sha256") or ""):
        raise CommandError("sha256 mismatch")
    if part.get("bytes") is not None and len(data) != part["bytes"]:
        raise CommandError("size mismatch")
    return data


def _delete_keys(backend, keys, prefix):
    for key in keys:
        if not key.startswith(prefix + "/"):
            continue
        try:
            backend.delete(key)
        except Exception:
            continue


def _write_manifest(bundle_dir, host, name, prefix, records):
    folder = bundle_dir / "runs"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = timezone.now().strftime("%Y%m%dT%H%M%S")
    path = folder / f"import-{stamp}.json"
    counter = 0
    while path.exists():
        counter += 1
        path = folder / f"import-{stamp}-{counter}.json"
    payload = {
        "created_at": timezone.now().isoformat(),
        "target_host": host,
        "target_name": name,
        "prefix": prefix,
        "records": records,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _rollback(stdout, manifest_path, host, name, apply):
    if not manifest_path.is_file():
        raise CommandError("rollback manifest is missing")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("target_host") != host or payload.get("target_name") != name:
        raise CommandError("rollback manifest is for a different database")
    prefix = payload.get("prefix") or ""
    records = payload.get("records") or []
    keys_present = any(record.get("keys") for record in records)
    if keys_present:
        if storage_prefix() != prefix or not prefix:
            raise CommandError("storage prefix does not match the manifest")
        reset_backend()
    backend = get_backend() if keys_present else None
    deleted = skipped = 0
    User = get_user_model()
    for record in records:
        slug = record.get("slug") or ""
        action, ok = _rollback_one(record, prefix, backend, apply, User)
        if ok:
            deleted += 1
        else:
            skipped += 1
        stdout.write(f"{action}\t{slug}")
    stdout.write(f"totals\tdeleted={deleted}\tskip={skipped}\tapply={int(bool(apply))}")


def _rollback_one(record, prefix, backend, apply, User):
    profile = Profile.objects.filter(pk=record.get("profile_id")).select_related("user").first()
    if profile is None:
        return "skip (missing)", False
    if profile.status != ProfileStatus.INDEXED:
        return "skip (not indexed)", False
    if profile.slug != record.get("slug") or profile.user_id != record.get("user_id"):
        return "skip (mismatch)", False
    user = profile.user
    if user.username != record.get("username") or user.is_staff or user.is_superuser:
        return "skip (mismatch)", False
    keys = [key for key in (record.get("keys") or []) if isinstance(key, str)]
    for key in keys:
        if not prefix or not key.startswith(prefix + "/") or key.split("/", 1)[0] != prefix:
            return "skip (key outside prefix)", False
    label = "deleted" if apply else "would delete"
    if not apply:
        return label, True
    with transaction.atomic():
        credit_ids = set(record.get("credit_ids") or [])
        contact_ids = set(record.get("contact_ids") or [])
        role_ids = set(record.get("role_ids") or [])
        Credit.objects.filter(pk__in=credit_ids, profile_id=profile.pk).delete()
        ProfileContact.objects.filter(pk__in=contact_ids, profile_id=profile.pk).delete()
        ProfileRole.objects.filter(pk__in=role_ids, profile_id=profile.pk).delete()
        profile_id = profile.pk
        user_id = user.pk
        profile.delete()
        User.objects.filter(pk=user_id, is_staff=False, is_superuser=False).delete()
        if keys:
            for key in keys:
                if not backend.delete(key):
                    raise CommandError("could not delete an uploaded key")
        if Profile.objects.filter(pk=profile_id).exists():
            raise CommandError("profile was not deleted")
    return label, True


def _row_counts(row, skip_photos):
    return {
        "credits": len(row.get("credits") or []),
        "roles": len(row.get("roles") or []),
        "contacts": len(row.get("contacts") or []),
        "birth": bool(row.get("birth_date")),
        "photo": bool(row.get("photo")) and not skip_photos,
    }


def _status_line(action, slug, counts):
    return (
        f"{action}\t{slug}\tcredits={counts['credits']}\troles={counts['roles']}\t"
        f"contacts={counts['contacts']}\tbirth={'yes' if counts['birth'] else 'no'}\t"
        f"photo={'yes' if counts['photo'] else 'no'}"
    )
