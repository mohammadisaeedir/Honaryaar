"""Fill empty birth dates on indexed profiles from birthdates.json.

Dry-run unless --apply. Never overwrites a birth date, never creates a profile,
and never writes any other field. --rollback clears a date only when it is
still exactly the value that command wrote.
"""

import json
import os
from datetime import date, datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from honaryaar.models import Profile, ProfileStatus

_EARLIEST = date(1900, 1, 1)


class Command(BaseCommand):
    help = "Fill empty birth dates on indexed crawled profiles."

    def add_arguments(self, parser):
        parser.add_argument("--data-dir", required=True)
        parser.add_argument("--only-file", default="")
        parser.add_argument("--only-slug", action="append", default=[])
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--rollback", default="")

    def handle(self, *args, **options):
        _refuse_remote()
        data_dir = Path(options["data_dir"])
        if options["rollback"]:
            self._rollback(data_dir, options["rollback"], options["apply"], options["only_slug"])
            return
        path = data_dir / "birthdates.json"
        if not path.is_file():
            raise CommandError(f"missing {path.name}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.stdout.write(_describe(payload))
        if not isinstance(payload, dict):
            raise CommandError("birthdates.json must be an object keyed by slug")
        wanted = _wanted_slugs(data_dir, options["only_file"], options["only_slug"], payload)
        verb = "set" if options["apply"] else "would set"
        totals = {"set": 0, "would_set": 0, "skip": 0}
        written = []
        seen = set()
        for slug in wanted:
            if slug in seen:
                continue
            seen.add(slug)
            outcome, reason, value = _plan(slug, payload.get(slug))
            if outcome != "set":
                totals["skip"] += 1
                self.stdout.write(f"{slug}\tskip ({reason})")
                continue
            profile = reason
            if not options["apply"]:
                totals["would_set"] += 1
                self.stdout.write(f"{slug}\twould set\t{value}")
                continue
            with transaction.atomic():
                profile.birth_date = value
                profile.save(update_fields=["birth_date"])
            totals["set"] += 1
            written.append({"id": profile.pk, "slug": slug, "birth_date": value.isoformat()})
            self.stdout.write(f"{slug}\tset\t{value.isoformat()}")
        self.stdout.write(
            f"totals\tset={totals['set']}\twould_set={totals['would_set']}\tskip={totals['skip']}"
        )
        if options["apply"]:
            destination = _write_manifest(data_dir, written)
            self.stdout.write(f"manifest\t{destination}\tids={len(written)}")
        else:
            self.stdout.write("dry run, nothing written")

    def _rollback(self, data_dir, manifest_arg, apply, only):
        path = Path(manifest_arg)
        if not path.is_file():
            path = data_dir / manifest_arg
        if not path.is_file():
            raise CommandError(f"manifest not found: {manifest_arg}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload.get("records") if isinstance(payload, dict) else None
        if not isinstance(records, list):
            raise CommandError("birth manifest has no records list")
        wanted = set(only)
        verb = "cleared" if apply else "would clear"
        cleared = 0
        skipped = 0
        for record in records:
            if not isinstance(record, dict):
                skipped += 1
                self.stdout.write("skip (bad record)")
                continue
            slug = record.get("slug") or ""
            if wanted and slug not in wanted:
                continue
            profile_id = record.get("id")
            raw = record.get("birth_date") or ""
            profile = Profile.objects.filter(pk=profile_id).first()
            if profile is None:
                skipped += 1
                self.stdout.write(f"{slug}\tskip (no profile)")
                continue
            current = profile.birth_date.isoformat() if profile.birth_date else ""
            if current != raw:
                skipped += 1
                self.stdout.write(f"{slug}\tskip (value changed)")
                continue
            if not apply:
                cleared += 1
                self.stdout.write(f"{slug}\t{verb}\t{raw}")
                continue
            with transaction.atomic():
                profile.birth_date = None
                profile.save(update_fields=["birth_date"])
            cleared += 1
            self.stdout.write(f"{slug}\t{verb}\t{raw}")
        self.stdout.write(f"totals\t{verb}={cleared}\tskip={skipped}")
        if not apply:
            self.stdout.write("dry run, nothing written")


def _refuse_remote():
    if os.environ.get("VERCEL") == "1":
        raise CommandError("refusing to run when VERCEL=1")
    host = (settings.DATABASES["default"].get("HOST") or "").strip()
    if host not in {"localhost", "127.0.0.1"}:
        raise CommandError(f"refusing database host {host or '(empty)'}")


def _describe(payload):
    if isinstance(payload, dict):
        sample = next(iter(payload.values()), None)
        kind = type(sample).__name__
        keys = sorted(sample) if isinstance(sample, dict) else []
        extra = f" value_keys={','.join(keys)}" if keys else ""
        return f"detected birthdates.json object keyed by slug n={len(payload)} value={kind}{extra}"
    if isinstance(payload, list):
        return f"detected birthdates.json list n={len(payload)}"
    return f"detected birthdates.json {type(payload).__name__}"


def _wanted_slugs(data_dir, only_file, only_slug, payload):
    slugs = list(payload)
    if only_file:
        path = data_dir / only_file
        if not path.is_file():
            raise CommandError(f"only-file not found: {path}")
        selected = _slug_list(json.loads(path.read_text(encoding="utf-8")))
        slugs = selected
    if only_slug:
        chosen = set(only_slug)
        slugs = [slug for slug in slugs if slug in chosen]
    return slugs


def _slug_list(payload):
    rows = payload
    if isinstance(payload, dict):
        for key in ("selected", "slugs", "profiles", "records"):
            if isinstance(payload.get(key), list):
                rows = payload[key]
                break
        else:
            raise CommandError("only-file object has no slug list")
    if not isinstance(rows, list):
        raise CommandError("only-file must be a list of slugs or objects with slug")
    slugs = []
    for item in rows:
        if isinstance(item, str) and item.strip():
            slugs.append(item.strip())
        elif isinstance(item, dict) and isinstance(item.get("slug"), str) and item["slug"].strip():
            slugs.append(item["slug"].strip())
        else:
            raise CommandError("only-file rows must be slugs or objects with slug")
    return slugs


def _plan(slug, row):
    parsed, reason = _parse_date(row)
    if parsed is None:
        return "skip", reason, None
    profile = Profile.objects.filter(slug=slug).first()
    if profile is None:
        return "skip", "no profile", None
    if profile.status != ProfileStatus.INDEXED:
        return "skip", "not indexed", None
    if profile.birth_date is not None:
        return "skip", "already set", None
    return "set", profile, parsed


def _parse_date(row):
    if not isinstance(row, dict):
        return None, "no birth date"
    raw = row.get("birth_date")
    if not isinstance(raw, str) or not raw.strip():
        return None, "no birth date"
    try:
        parsed = datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None, "not a date"
    if parsed < _EARLIEST:
        return None, "before 1900"
    if parsed > timezone.localdate():
        return None, "in the future"
    return parsed, ""


def _write_manifest(data_dir, records):
    stamp = timezone.now().strftime("%Y%m%dT%H%M%S")
    destination = data_dir / "runs" / f"birthdates-{stamp}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {"created_at": timezone.now().isoformat(), "records": records}
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination
