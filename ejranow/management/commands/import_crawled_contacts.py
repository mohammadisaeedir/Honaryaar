"""Import crawled contact sidecars onto indexed profiles.

Dry-run unless --apply. Existing ProfileContact rows are never updated.
Rollback deletes only ids from a contacts manifest that still exist and
still have source tiwall or gishe10.
"""

import json
import os
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.utils import timezone

from ejranow.models import Profile, ProfileContact, ProfileStatus

_SOURCES = {"tiwall", "gishe10"}
_STRING_FIELDS = ("email", "telegram", "whatsapp", "website")
_FIELD_ORDER = ("phones", "instagram", "email", "telegram", "whatsapp", "website", "other")
_LABEL_KINDS = {
    "youtube": "youtube",
    "aparat": "aparat",
    "آپارات": "aparat",
    "twitch": "twitch",
    "imdb": "imdb",
    "linkedin": "linkedin",
    "pinterest": "pinterest",
    "spotify": "spotify",
    "soundcloud": "soundcloud",
}


class Command(BaseCommand):
    help = "Import crawled contacts for manifest slugs. Writes nothing unless --apply."

    def add_arguments(self, parser):
        parser.add_argument("--data-dir", required=True, help="Absolute path to data/import-ready/.")
        parser.add_argument("--manifest", default="", help="Import run manifest. Only its slugs are considered.")
        parser.add_argument("--only-slug", action="append", dest="only_slug", help="Limit to this slug. Repeatable.")
        parser.add_argument("--public", action="store_true", help="Set is_public=True. Default is False.")
        parser.add_argument("--apply", action="store_true", help="Write rows. Without this, the run only prints a plan.")
        parser.add_argument("--rollback", default="", help="Contacts manifest from a previous run. Dry unless --apply.")

    def handle(self, *args, **options):
        _refuse_remote()
        data_dir = Path(options["data_dir"]).expanduser()
        if not data_dir.is_dir():
            raise CommandError(f"data dir not found: {data_dir}")
        only = options["only_slug"] or []
        if options["rollback"]:
            self._rollback(data_dir, Path(options["rollback"]).expanduser(), options["apply"], only)
            return
        if not options["manifest"]:
            raise CommandError("--manifest is required")
        self._import(
            data_dir,
            Path(options["manifest"]).expanduser(),
            only,
            options["public"],
            options["apply"],
        )

    def _import(self, data_dir, manifest_path, only, public, apply):
        sidecar_path = data_dir / "contacts-sidecar.json"
        profiles_path = data_dir / "profiles.json"
        for path in (sidecar_path, profiles_path):
            if not path.is_file():
                raise CommandError(f"missing {path.name}")
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
        if not isinstance(sidecar, dict):
            raise CommandError("contacts-sidecar.json must be an object keyed by slug")
        if not isinstance(profiles, list):
            raise CommandError("profiles.json must be a list")
        self.stdout.write(_describe_inputs(sidecar, profiles))
        slugs = _manifest_slugs(manifest_path)
        if only:
            wanted = set(only)
            slugs = [slug for slug in slugs if slug in wanted]
        sources = {}
        for item in profiles:
            if isinstance(item, dict) and item.get("slug"):
                sources[item["slug"]] = item.get("source") or ""
        verb = "added" if apply else "would add"
        created = []
        unmapped = []
        seen = set()
        for slug in slugs:
            if slug in seen:
                continue
            seen.add(slug)
            row = sidecar.get(slug)
            if not isinstance(row, dict):
                self.stdout.write(f"{slug}\tskip (no sidecar row)")
                continue
            source = sources.get(slug, "")
            if source not in _SOURCES:
                self.stdout.write(f"{slug}\tskip (source: {source or 'missing'})")
                continue
            profile = Profile.objects.filter(slug=slug).first()
            if profile is None:
                self.stdout.write(f"{slug}\tskip (no profile)")
                continue
            if profile.status != ProfileStatus.INDEXED:
                self.stdout.write(f"{slug}\tskip (not indexed)")
                continue
            adds, notes, rows, extra = _plan_profile(profile, row, source, public)
            unmapped.extend((slug, label, value) for label, value in extra)
            counts = "\t".join(f"{kind}={adds[kind]}" for kind in adds) or "none"
            self.stdout.write(f"{slug}\t{verb}\t{counts}")
            for note in notes:
                self.stdout.write(f"{slug}\t{note}")
            if not apply:
                continue
            with transaction.atomic():
                for contact in rows:
                    try:
                        with transaction.atomic():
                            contact.save()
                    except IntegrityError:
                        self.stdout.write(f"{slug}\tskip (exists: {contact.kind})")
                        continue
                    created.append(
                        {
                            "id": contact.pk,
                            "slug": slug,
                            "profile_id": profile.pk,
                            "kind": contact.kind,
                        }
                    )
        if unmapped:
            for slug, label, value in unmapped:
                self.stdout.write(f"unmapped\t{slug}\t{label}\t{value}")
        else:
            self.stdout.write("unmapped\tnone")
        if apply:
            path = _write_manifest(data_dir, created)
            self.stdout.write(f"manifest\t{path}\tids={len(created)}")

    def _rollback(self, data_dir, manifest_path, apply, only):
        path = manifest_path
        if not path.is_file():
            path = data_dir / manifest_path
        if not path.is_file():
            raise CommandError(f"manifest not found: {manifest_path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload.get("records") if isinstance(payload, dict) else None
        if not isinstance(records, list):
            raise CommandError("contacts manifest has no records list")
        wanted = set(only)
        verb = "deleted" if apply else "would delete"
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get("id"), int):
                self.stdout.write("skip (manifest row has no id)")
                continue
            if wanted and record.get("slug") not in wanted:
                continue
            contact = ProfileContact.objects.filter(pk=record["id"]).first()
            if contact is None:
                self.stdout.write(f"skip (missing id {record['id']})")
                continue
            if contact.source not in _SOURCES:
                self.stdout.write(f"skip (source {contact.source or 'blank'} id {contact.pk})")
                continue
            if not apply:
                self.stdout.write(f"{verb}\t{contact.pk}\t{contact.profile.slug}\t{contact.kind}")
                continue
            with transaction.atomic():
                contact.delete()
            self.stdout.write(f"{verb}\t{record['id']}\t{record.get('slug', '')}\t{record.get('kind', '')}")


def _refuse_remote():
    if os.environ.get("VERCEL") == "1":
        raise CommandError("refusing to run when VERCEL=1")
    host = (settings.DATABASES["default"].get("HOST") or "").strip()
    if host not in {"localhost", "127.0.0.1"}:
        raise CommandError(f"refusing database host {host or '(empty)'}")


def _manifest_slugs(path):
    if not path.is_file():
        raise CommandError(f"manifest not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        raise CommandError("import manifest has no records list")
    slugs = []
    for record in records:
        slug = record.get("slug") if isinstance(record, dict) else ""
        if isinstance(slug, str) and slug.strip():
            slugs.append(slug.strip())
    return slugs


def _describe_inputs(sidecar, profiles):
    field_types = Counter()
    phone_keys = Counter()
    instagram_keys = Counter()
    other_keys = Counter()
    string_fields = Counter()
    sources = Counter()
    phone_example = None
    instagram_example = None
    other_example = None
    for row in sidecar.values():
        if not isinstance(row, dict):
            field_types["row:" + type(row).__name__] += 1
            continue
        for field in _FIELD_ORDER:
            value = row.get(field)
            field_types[f"{field}:{type(value).__name__}"] += 1
        for item in row.get("phones") or []:
            if isinstance(item, dict):
                phone_keys[tuple(sorted(item))] += 1
                if phone_example is None:
                    phone_example = item
            else:
                phone_keys[type(item).__name__] += 1
        for item in row.get("instagram") or []:
            if isinstance(item, dict):
                instagram_keys[tuple(sorted(item))] += 1
                if instagram_example is None:
                    instagram_example = item
            else:
                instagram_keys[type(item).__name__] += 1
        for field in _STRING_FIELDS:
            for item in row.get(field) or []:
                string_fields[f"{field}:{type(item).__name__}"] += 1
        for item in row.get("other") or []:
            if isinstance(item, dict):
                other_keys[tuple(sorted(item))] += 1
                if other_example is None:
                    other_example = item
            else:
                other_keys[type(item).__name__] += 1
    for item in profiles:
        if isinstance(item, dict):
            sources[str(item.get("source") or "")] += 1
    lines = [
        f"structure\tcontacts-sidecar.json\tobject\tslugs={len(sidecar)}",
        f"structure\tfields\t{', '.join(f'{name}={count}' for name, count in sorted(field_types.items()))}",
        f"structure\tphones\t{_shape(phone_keys)}",
        "structure\tphones example\t" + json.dumps(phone_example, ensure_ascii=False),
        f"structure\tinstagram\t{_shape(instagram_keys)}",
        "structure\tinstagram example\t" + json.dumps(instagram_example, ensure_ascii=False),
        f"structure\tother\t{_shape(other_keys)}",
        "structure\tother example\t" + json.dumps(other_example, ensure_ascii=False),
        f"structure\tstring fields\t{', '.join(f'{name}={count}' for name, count in sorted(string_fields.items()))}",
        f"structure\tprofiles.json\tlist\t{len(profiles)}\tsource={', '.join(f'{name}:{count}' for name, count in sorted(sources.items()))}",
    ]
    return "\n".join(lines)


def _shape(counter):
    if not counter:
        return "none"
    parts = []
    for keys, count in counter.most_common():
        if isinstance(keys, tuple):
            parts.append("{" + ", ".join(keys) + "}" + f"={count}")
        else:
            parts.append(f"{keys}={count}")
    return ", ".join(parts)


def _plan_profile(profile, row, source, public):
    adds = Counter()
    notes = []
    rows = []
    unmapped = []
    position = 0
    for kind, raw in _candidates(row, unmapped):
        if not raw:
            notes.append(f"skip (invalid: {kind}: empty)")
            continue
        contact = ProfileContact(
            profile=profile,
            kind=kind,
            value=raw,
            is_public=public,
            position=position,
            source=source,
        )
        try:
            contact.full_clean()
        except ValidationError as exc:
            if _only_unique(exc):
                notes.append(f"skip (exists: {kind})")
            else:
                notes.append(f"skip (invalid: {kind}: {_validation_reason(exc)})")
            continue
        if ProfileContact.objects.filter(profile=profile, kind=contact.kind, value=contact.value).exists():
            notes.append(f"skip (exists: {kind})")
            continue
        contact.position = position
        position += 1
        adds[contact.kind] += 1
        rows.append(contact)
    return adds, notes, rows, unmapped


def _candidates(row, unmapped):
    for item in row.get("phones") or []:
        yield "phone", _phone_value(item)
    for item in row.get("instagram") or []:
        yield "instagram", _instagram_value(item)
    for field in _STRING_FIELDS:
        for item in row.get(field) or []:
            if not isinstance(item, str):
                yield field, ""
                continue
            value = item.strip()
            if field == "email":
                value = _email_value(value)
            yield field, value
    for item in row.get("other") or []:
        if not isinstance(item, dict):
            unmapped.append(("", json.dumps(item, ensure_ascii=False)))
            continue
        label = item.get("label") if isinstance(item.get("label"), str) else ""
        value = item.get("value") if isinstance(item.get("value"), str) else ""
        kind = _kind_for_label(label)
        if kind is None:
            unmapped.append((label, value))
            continue
        yield kind, value.strip()


def _phone_value(item):
    if isinstance(item, str):
        return item.strip()
    if not isinstance(item, dict):
        return ""
    normalized = item.get("normalized")
    if isinstance(normalized, str) and normalized.strip():
        return normalized.strip()
    raw = item.get("raw")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return ""


def _email_value(value):
    text = value.strip()
    if text.lower().startswith("mailto:"):
        text = text[7:]
    return text.split("?", 1)[0].strip()


def _instagram_value(item):
    if isinstance(item, str):
        return item.strip()
    if not isinstance(item, dict):
        return ""
    handle = item.get("handle")
    if isinstance(handle, str) and handle.strip():
        return handle.strip()
    return ""


def _kind_for_label(label):
    text = (label or "").strip()
    if text in _LABEL_KINDS:
        return _LABEL_KINDS[text]
    return _LABEL_KINDS.get(text.casefold())


def _only_unique(exc):
    codes = _error_codes(exc)
    return bool(codes) and codes <= {"unique", "unique_together"}


def _error_codes(exc):
    codes = set()
    if getattr(exc, "error_dict", None):
        for errors in exc.error_dict.values():
            for error in errors:
                if error.code:
                    codes.add(error.code)
    return codes


def _validation_reason(exc):
    if getattr(exc, "error_dict", None):
        parts = []
        for field, errors in exc.error_dict.items():
            texts = []
            for error in errors:
                texts.extend(error.messages)
            message = "; ".join(texts)
            if field in {"value", "__all__"}:
                parts.append(message)
            else:
                parts.append(f"{field}: {message}")
        return "; ".join(parts)
    return "; ".join(exc.messages)


def _write_manifest(data_dir, created):
    runs = data_dir / "runs"
    runs.mkdir(exist_ok=True)
    stamp = timezone.now().strftime("%Y%m%dT%H%M%S")
    path = runs / f"contacts-{stamp}.json"
    payload = {
        "created_at": timezone.now().isoformat(),
        "records": created,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
