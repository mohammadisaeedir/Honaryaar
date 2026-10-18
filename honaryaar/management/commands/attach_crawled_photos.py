"""Attach crawled profile photos to list_image and list_thumb.

--probe downloads and validates only. A run with neither --probe nor --apply
prints the plan. --apply uploads to ParsPack under the dev prefix.
"""

import gzip
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from honaryaar.media_files import EXT, MediaError, detect, max_bytes, process_image
from honaryaar.media_service import assign_file, url_for_key
from honaryaar.models import Profile, ProfileStatus
from honaryaar.storage import (
    ParsPackBackend,
    get_backend,
    parspack_configured,
    reset_backend,
    storage_prefix,
)

_ALLOWED_HOSTS = {"zbcdn.cloud", "gishe10.ir"}
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
_DEV_PROFILE_PREFIX = "dev/profiles/"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class _PhotoFailure(Exception):
    pass


def _decode_body(data, encoding):
    encoding = (encoding or "").strip().lower()
    if encoding in {"", "identity"}:
        return data
    if encoding == "gzip":
        try:
            return gzip.decompress(data)
        except OSError as exc:
            raise _PhotoFailure("gzip") from exc
    if encoding == "br":
        return _brotli_decompress(data)
    raise _PhotoFailure(f"content encoding {encoding}")


def _brotli_decompress(data):
    try:
        import brotli
    except ImportError:
        brotli = None
    if brotli is not None:
        try:
            return brotli.decompress(data)
        except Exception as exc:
            raise _PhotoFailure("brotli") from exc
    binary = shutil.which("brotli")
    if not binary:
        raise _PhotoFailure("brotli")
    result = subprocess.run([binary, "-d", "-c"], input=data, capture_output=True, check=False)
    if result.returncode != 0 or not result.stdout:
        raise _PhotoFailure("brotli")
    return result.stdout


class Command(BaseCommand):
    help = "Attach crawled photos to indexed profiles. Writes nothing unless --apply."

    def add_arguments(self, parser):
        parser.add_argument("--manifest", default="", help="Import run manifest. Required unless --rollback.")
        parser.add_argument("--data-dir", required=True, help="Absolute path to data/import-ready/.")
        parser.add_argument("--only-slug", action="append", dest="only_slug", help="Limit to this slug. Repeatable.")
        parser.add_argument("--probe", action="store_true", help="Download and validate only. No bucket or database writes.")
        parser.add_argument("--apply", action="store_true", help="Upload and save. Without --apply or --probe, print the plan.")
        parser.add_argument("--rollback", default="", help="Photo manifest from a previous run. Dry unless --apply.")

    def handle(self, *args, **options):
        _refuse_remote()
        if options["probe"] and options["apply"]:
            raise CommandError("use only one of --probe or --apply")
        if options["rollback"] and options["probe"]:
            raise CommandError("do not combine --rollback with --probe")
        data_dir = Path(options["data_dir"]).expanduser()
        if not data_dir.is_dir():
            raise CommandError(f"data dir not found: {data_dir}")
        if options["rollback"]:
            if options["apply"]:
                _require_parspack_dev()
            self._rollback(Path(options["rollback"]).expanduser(), options["apply"], options["only_slug"] or [])
            return
        if not options["manifest"]:
            raise CommandError("--manifest is required")
        if options["apply"]:
            _require_parspack_dev()
        mode = "probe" if options["probe"] else "apply" if options["apply"] else "plan"
        self._attach(data_dir, Path(options["manifest"]).expanduser(), options["only_slug"] or [], mode)

    def _attach(self, data_dir, manifest_path, only_slug, mode):
        records, description = _load_records(manifest_path)
        self.stdout.write(description)
        selected, missing = _select(records, only_slug)
        if only_slug:
            self.stdout.write(f"only-slug kept {len(selected)} of {len(records)}")
        urls = _photo_urls(data_dir)
        counts = {"would_upload": 0, "uploaded": 0, "probe_ok": 0, "skip": 0, "failed": 0}
        written = []
        self._did_fetch = False
        for slug in missing:
            self._result("skip", slug, "not in manifest")
            counts["skip"] += 1
        for record in selected:
            slug = str(record.get("slug") or "")
            status, row, detail = self._one(record, urls.get(slug), mode)
            counts[status] += 1
            if status == "uploaded" and row is not None:
                written.append(row)
            self._result(_LABELS[status], slug, detail)
        if mode == "apply":
            path = self._write_manifest(data_dir, written)
            if path is not None:
                self.stdout.write(f"manifest {path}")
        self.stdout.write(
            "totals "
            f"would_upload={counts['would_upload']} uploaded={counts['uploaded']} "
            f"probe_ok={counts['probe_ok']} skip={counts['skip']} failed={counts['failed']}"
        )
        if mode == "plan":
            self.stdout.write("plan only, nothing written")
        elif mode == "probe":
            self.stdout.write("probe only, nothing written")

    def _one(self, record, source_url, mode):
        slug = str(record.get("slug") or "")
        if mode == "probe":
            return self._probe(source_url)
        profile, reason = _eligible_profile(record)
        if reason:
            return "skip", None, reason
        if not source_url:
            return "skip", None, "null photo_source_url"
        if mode == "plan":
            return "would_upload", None, "url=-"
        try:
            data = self._fetch(source_url)
            _kind, content_type = detect(data, "photo")
            body, out_type, thumb = process_image(data, content_type)
        except (_PhotoFailure, MediaError) as exc:
            return "failed", None, _failure_text(exc)
        if not body or not thumb:
            return "failed", None, "empty image"
        ext = EXT.get(out_type)
        if not ext:
            return "failed", None, "unsupported type"
        prefix = storage_prefix()
        token = uuid.uuid4()
        key = f"{prefix}/profiles/{profile.id}/{token}{ext}"
        thumb_key = f"{prefix}/profiles/{profile.id}/{token}-thumb.jpg"
        backend = get_backend()
        stored = []
        try:
            backend.put_bytes(key, body, out_type)
            stored.append(key)
            backend.put_bytes(thumb_key, thumb, "image/jpeg")
            stored.append(thumb_key)
            public_acl = bool(backend.set_public(key) and backend.set_public(thumb_key))
            with transaction.atomic():
                assign_file(profile, "list_image", key)
                assign_file(profile, "list_thumb", thumb_key)
                profile.list_public_acl = public_acl
                profile.save(update_fields=["list_image", "list_thumb", "list_public_acl"])
        except Exception as exc:
            for item in stored:
                try:
                    backend.delete(item)
                except Exception:
                    pass
            return "failed", None, _failure_text(exc)
        public_url = url_for_key(key, public=True, public_acl=public_acl) or "-"
        row = {
            "profile_id": profile.id,
            "slug": slug,
            "source_url": source_url,
            "list_image": key,
            "list_thumb": thumb_key,
            "list_public_acl": public_acl,
            "bytes": len(body),
        }
        return "uploaded", row, f"bytes={len(body)} url={public_url}"

    def _probe(self, source_url):
        if not source_url:
            return "skip", None, "null photo_source_url"
        try:
            data = self._fetch(source_url)
            _kind, content_type = detect(data, "photo")
            body, out_type, _thumb = process_image(data, content_type)
        except (_PhotoFailure, MediaError) as exc:
            return "failed", None, _failure_text(exc)
        return "probe_ok", None, f"bytes={len(data)} type={out_type} stored_bytes={len(body)} from={content_type} url=-"

    def _fetch(self, url):
        if not isinstance(url, str):
            raise _PhotoFailure("not https")
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme.lower() != "https":
            raise _PhotoFailure("not https")
        if host not in _ALLOWED_HOSTS:
            raise _PhotoFailure("host not allowed")
        if self._did_fetch:
            time.sleep(1)
        self._did_fetch = True
        limit = max_bytes("photo")
        opener = urllib.request.build_opener(_NoRedirect)
        request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT}, method="GET")
        try:
            with opener.open(request, timeout=20) as response:
                status = getattr(response, "status", None) or response.getcode()
                if status is not None and 300 <= int(status) < 400:
                    raise _PhotoFailure("redirect")
                encoding = response.headers.get("Content-Encoding", "")
                chunks = []
                size = 0
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > limit:
                        raise _PhotoFailure("too large")
                    chunks.append(chunk)
        except _PhotoFailure:
            raise
        except urllib.error.HTTPError as exc:
            if 300 <= exc.code < 400:
                raise _PhotoFailure("redirect") from exc
            raise _PhotoFailure(f"HTTP {exc.code}") from exc
        except TimeoutError as exc:
            raise _PhotoFailure("timeout") from exc
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, TimeoutError) or "timed out" in str(reason).lower():
                raise _PhotoFailure("timeout") from exc
            raise _PhotoFailure("fetch failed") from exc
        return _decode_body(b"".join(chunks), encoding)

    def _result(self, label, slug, detail):
        if detail:
            self.stdout.write(f"{label}\t{slug}\t{detail}")
        else:
            self.stdout.write(f"{label}\t{slug}")

    def _write_manifest(self, data_dir, rows):
        if not rows:
            self.stdout.write("no photo manifest written")
            return None
        folder = data_dir / "runs"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = timezone.now().strftime("%Y%m%dT%H%M%S")
        path = folder / f"photos-{stamp}.json"
        payload = {"created_at": timezone.now().isoformat(), "records": rows}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def _rollback(self, path, apply, only_slug):
        records, description = _load_records(path)
        self.stdout.write(description)
        selected, missing = _select(records, only_slug)
        counts = {"would_rollback": 0, "rolled_back": 0, "skip": 0, "failed": 0}
        for slug in missing:
            self._result("skip", slug, "not in manifest")
            counts["skip"] += 1
        backend = get_backend() if apply else None
        for record in selected:
            slug = str(record.get("slug") or "")
            status, detail = self._rollback_one(record, apply, backend)
            counts[status] += 1
            self._result(_LABELS[status], slug, detail)
        self.stdout.write(
            "totals "
            f"would_rollback={counts['would_rollback']} rolled_back={counts['rolled_back']} "
            f"skip={counts['skip']} failed={counts['failed']}"
        )
        if not apply:
            self.stdout.write("rollback plan only, nothing written")

    def _rollback_one(self, record, apply, backend):
        slug = str(record.get("slug") or "")
        image_key = record.get("list_image") or ""
        thumb_key = record.get("list_thumb") or ""
        profile_id = record.get("profile_id")
        if not isinstance(image_key, str) or not isinstance(thumb_key, str) or not image_key or not thumb_key:
            return "skip", "incomplete row"
        if not image_key.startswith(_DEV_PROFILE_PREFIX) or not thumb_key.startswith(_DEV_PROFILE_PREFIX):
            return "skip", "key is outside dev/profiles/"
        profile = Profile.objects.filter(pk=profile_id).first() if profile_id else None
        if profile is None:
            return "skip", "profile missing"
        if profile.slug != slug:
            return "skip", "slug does not match profile"
        if profile.list_image.name != image_key or profile.list_thumb.name != thumb_key:
            return "skip", "profile keys differ"
        if not apply:
            return "would_rollback", "url=-"
        try:
            with transaction.atomic():
                assign_file(profile, "list_image", "")
                assign_file(profile, "list_thumb", "")
                profile.list_public_acl = False
                profile.save(update_fields=["list_image", "list_thumb", "list_public_acl"])
        except Exception as exc:
            return "failed", _failure_text(exc)
        for key in (image_key, thumb_key):
            try:
                if not backend.delete(key):
                    return "failed", "delete refused"
            except Exception as exc:
                return "failed", _failure_text(exc)
        return "rolled_back", "url=-"


_LABELS = {
    "would_upload": "would upload",
    "uploaded": "uploaded",
    "probe_ok": "probe ok",
    "would_rollback": "would rollback",
    "rolled_back": "rolled back",
    "skip": "skip",
    "failed": "failed",
}


def _refuse_remote():
    if os.environ.get("VERCEL") == "1":
        raise CommandError("refusing to run when VERCEL=1")
    host = (settings.DATABASES["default"].get("HOST") or "").strip()
    if host not in {"localhost", "127.0.0.1"}:
        raise CommandError(f"refusing database host {host or '(empty)'}")


def _require_parspack_dev():
    if not parspack_configured():
        raise CommandError("ParsPack is not configured. Refusing to fall back to local disk.")
    reset_backend()
    backend = get_backend()
    if not isinstance(backend, ParsPackBackend):
        raise CommandError("storage backend is not ParsPack. Refusing to fall back to local disk.")
    if storage_prefix() != "dev":
        raise CommandError("storage prefix must be exactly dev")
    return backend


def _load_records(path):
    if not path.is_file():
        raise CommandError(f"manifest not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        records = [item for item in payload["records"] if isinstance(item, dict)]
        sample = list(records[0]) if records else []
        slugs = [item.get("slug") for item in records]
        text = (
            f"detected manifest object=True keys={list(payload)} "
            f"records={len(payload['records'])} usable={len(records)} "
            f"record_keys={sample} slugs={slugs}"
        )
        return records, text
    if isinstance(payload, list):
        records = [item for item in payload if isinstance(item, dict) and item.get("slug")]
        sample = list(records[0]) if records else []
        slugs = [item.get("slug") for item in records]
        text = (
            f"detected manifest list=True n={len(payload)} usable={len(records)} "
            f"record_keys={sample} slugs={slugs}"
        )
        return records, text
    kind = type(payload).__name__
    keys = list(payload) if isinstance(payload, dict) else []
    raise CommandError(f"unrecognized manifest type={kind} keys={keys}")


def _photo_urls(data_dir):
    path = data_dir / "profiles.json"
    if not path.is_file():
        raise CommandError("missing profiles.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise CommandError("profiles.json is not a list")
    urls = {}
    for item in payload:
        if isinstance(item, dict) and item.get("slug"):
            urls[item["slug"]] = item.get("photo_source_url")
    return urls


def _select(records, only_slug):
    if not only_slug:
        return records, []
    wanted = []
    seen = set()
    for slug in only_slug:
        if slug not in seen:
            wanted.append(slug)
            seen.add(slug)
    by_slug = {}
    for record in records:
        slug = record.get("slug")
        if slug in seen and slug not in by_slug:
            by_slug[slug] = record
    selected = [by_slug[slug] for slug in wanted if slug in by_slug]
    missing = [slug for slug in wanted if slug not in by_slug]
    return selected, missing


def _eligible_profile(record):
    slug = str(record.get("slug") or "")
    profile_id = record.get("profile_id")
    profile = Profile.objects.filter(pk=profile_id).first() if profile_id else None
    if profile is None:
        return None, "profile missing"
    if profile.slug != slug:
        return None, "slug does not match profile"
    if profile.status != ProfileStatus.INDEXED:
        return None, "not indexed"
    if profile.list_image.name:
        return None, "list_image already set"
    return profile, ""


def _failure_text(exc):
    if isinstance(exc, MediaError):
        return exc.message
    if isinstance(exc, _PhotoFailure):
        return str(exc)
    return exc.__class__.__name__
