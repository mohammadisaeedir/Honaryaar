"""Fill empty gender on indexed profiles from a slug map.

Dry run unless --apply. Never overwrites a gender, never creates a profile,
and never writes any other field. --rollback clears gender only when it is
still exactly the value this command wrote.
"""

import json
import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone

from honaryaar.models import Profile, ProfileStatus

_GENDERS = {"male", "female"}


class Command(BaseCommand):
    help = "Fill empty gender on indexed crawled profiles. Writes nothing unless --apply."

    def add_arguments(self, parser):
        parser.add_argument("--genders-file", default="")
        parser.add_argument("--bundle-dir", default="")
        parser.add_argument("--only-slug", action="append", dest="only_slug")
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--rollback", default="")
        parser.add_argument("--production", action="store_true")
        parser.add_argument("--expect-host", default="")

    def handle(self, *args, **options):
        _prepare_database(options)
        host, name = _announce(self.stdout)
        if options["rollback"]:
            _rollback(
                self.stdout,
                Path(options["rollback"]).expanduser().resolve(),
                host,
                name,
                options["apply"],
            )
            return
        genders_path = Path(options["genders_file"]).expanduser()
        if not options["genders_file"] or not genders_path.is_file():
            raise CommandError("--genders-file is required")
        genders = _load_genders(genders_path)
        bundle_dir = Path(options["bundle_dir"]).expanduser().resolve() if options["bundle_dir"] else None
        if bundle_dir is not None:
            _require_bundle_slugs(self.stdout, bundle_dir, genders)
        slugs = list(genders)
        chosen = set(options["only_slug"] or [])
        if chosen:
            slugs = [slug for slug in slugs if slug in chosen]
            for slug in sorted(chosen - set(genders)):
                self.stdout.write(f"{slug}\tskip (not in genders file)")
        root = bundle_dir or genders_path.resolve().parent
        _fill(self.stdout, genders, slugs, root, host, name, options["apply"], extra_skips=len(chosen - set(genders)) if chosen else 0)


def _prepare_database(options):
    if options["production"]:
        _repoint(_production_params(options["expect_host"]))
        return
    if os.environ.get("VERCEL") == "1":
        raise CommandError("refusing to run when VERCEL=1")
    host = (connections["default"].settings_dict.get("HOST") or "").strip()
    if host not in {"localhost", "127.0.0.1"}:
        raise CommandError("database host must be localhost or 127.0.0.1")


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
    return host, name


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


def _load_genders(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CommandError("genders file must be an object keyed by slug")
    genders = {}
    for slug, value in payload.items():
        if not isinstance(slug, str) or not slug.strip():
            raise CommandError("genders file keys must be slugs")
        genders[slug.strip()] = value
    return genders


def _require_bundle_slugs(stdout, bundle_dir, genders):
    path = bundle_dir / "bundle.json"
    if not path.is_file():
        raise CommandError("bundle.json is missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise CommandError("bundle.json must be a list")
    missing = []
    for row in payload:
        slug = (row.get("slug") or "").strip() if isinstance(row, dict) else ""
        if slug and slug not in genders:
            missing.append(slug)
    for slug in missing:
        stdout.write(f"missing slug\t{slug}")
    if missing:
        raise CommandError("genders file is missing bundle slugs")


def _fill(stdout, genders, slugs, root, host, name, apply, extra_skips):
    would = set_count = 0
    skipped = extra_skips
    written = []
    for slug in slugs:
        value = genders.get(slug)
        action, profile = _plan(slug, value)
        if action != "set":
            skipped += 1
            stdout.write(f"{slug}\tskip ({action})")
            continue
        if not apply:
            would += 1
            stdout.write(f"{slug}\twould set\t{value}")
            continue
        saved = _apply_one(profile.pk, value)
        if saved is None:
            skipped += 1
            stdout.write(f"{slug}\tskip (already set)")
            continue
        set_count += 1
        written.append({"id": saved, "slug": slug, "gender": value})
        stdout.write(f"{slug}\tset\t{value}")
    if apply:
        manifest = _write_manifest(root, host, name, written)
        stdout.write(f"manifest\t{manifest}")
    stdout.write(f"totals\twould_set={would}\tset={set_count}\tskip={skipped}\tapply={int(bool(apply))}")


def _plan(slug, value):
    if value not in _GENDERS:
        return "not male or female", None
    profile = Profile.objects.filter(slug=slug).only("id", "status", "gender").first()
    if profile is None:
        return "no profile", None
    if profile.status != ProfileStatus.INDEXED:
        return "not indexed", None
    if profile.gender:
        return "already set", None
    return "set", profile


def _apply_one(profile_id, value):
    with transaction.atomic():
        profile = Profile.objects.select_for_update(of=("self",)).select_related("user").get(pk=profile_id)
        if profile.status != ProfileStatus.INDEXED or profile.gender:
            return None
        _save_gender(profile, value)
    return profile_id


def _save_gender(profile, value):
    """Save gender only. Profile.save copies the username onto the slug, so the
    in-memory username is pinned to the public slug for this call and restored
    before the row is checked."""
    user = profile.user
    username = user.username
    user.username = profile.slug
    before = _snapshot(profile.pk)
    try:
        profile.gender = value
        profile.save(update_fields=["gender"])
    finally:
        user.username = username
    after = _snapshot(profile.pk)
    changed = {key for key in before if before[key] != after[key]}
    if changed != {"gender"} or after["gender"] != value:
        raise CommandError("refusing to change fields other than gender")


def _snapshot(profile_id):
    return Profile.objects.filter(pk=profile_id).values().get()


def _write_manifest(root, host, name, records):
    folder = root / "runs"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = timezone.now().strftime("%Y%m%dT%H%M%S")
    path = folder / f"gender-{stamp}.json"
    counter = 0
    while path.exists():
        counter += 1
        path = folder / f"gender-{stamp}-{counter}.json"
    payload = {
        "created_at": timezone.now().isoformat(),
        "target_host": host,
        "target_name": name,
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
    records = payload.get("records")
    if not isinstance(records, list):
        raise CommandError("gender manifest has no records list")
    cleared = skipped = 0
    for record in records:
        if not isinstance(record, dict):
            skipped += 1
            stdout.write("skip (bad record)")
            continue
        slug = record.get("slug") or ""
        action, ok = _rollback_one(record, apply)
        if ok:
            cleared += 1
        else:
            skipped += 1
        stdout.write(f"{action}\t{slug}")
    label = "cleared" if apply else "would_clear"
    stdout.write(f"totals\t{label}={cleared}\tskip={skipped}\tapply={int(bool(apply))}")


def _rollback_one(record, apply):
    profile = Profile.objects.filter(pk=record.get("id")).select_related("user").first()
    if profile is None:
        return "skip (missing)", False
    expected = record.get("gender")
    if profile.gender != expected:
        return "skip (value changed)", False
    label = "cleared" if apply else "would clear"
    if not apply:
        return label, True
    with transaction.atomic():
        locked = Profile.objects.select_for_update(of=("self",)).select_related("user").get(pk=profile.pk)
        if locked.gender != expected:
            return "skip (value changed)", False
        _save_gender(locked, "")
    return label, True
