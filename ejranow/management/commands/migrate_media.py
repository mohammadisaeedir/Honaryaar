import hashlib
import tempfile
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from ejranow.media_files import EXT, HEADER_BYTES, detect, process_image
from ejranow.media_service import hash_path
from ejranow.models import MediaMigrationRecord, ProfileMedia, Project, Testimonial
from ejranow.storage import get_backend, key_in_scope, reset_backend, storage_prefix

TARGETS = (
    ("ejranow.profilemedia", ProfileMedia, "file", "thumbnail"),
    ("ejranow.project", Project, "image", "image_thumb"),
    ("ejranow.testimonial", Testimonial, "image", "image_thumb"),
)


def remote_allowed(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if host in {"169.254.169.254", "metadata.google.internal"}:
        return False
    allowed = {item.strip().lower() for item in settings.MEDIA_MIGRATION_HOSTS.split(",") if item.strip()}
    if host not in allowed:
        return False
    if parsed.scheme == "https":
        return True
    return parsed.scheme == "http" and host in {"localhost", "127.0.0.1"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _fetch(url, limit):
    if not remote_allowed(url):
        raise CommandError(f"refusing untrusted source host for {url}")
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(url, method="GET")
    try:
        with opener.open(request, timeout=20) as response:
            chunks = []
            size = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > limit:
                    raise CommandError("source is larger than the media limit")
                chunks.append(chunk)
    except CommandError:
        raise
    except Exception as exc:
        raise CommandError(f"source fetch failed: {exc.__class__.__name__}") from exc
    payload = b"".join(chunks)
    handle = tempfile.NamedTemporaryFile(delete=False)
    handle.write(payload)
    handle.close()
    return Path(handle.name)


class Command(BaseCommand):
    help = "Copy existing media into the current ParsPack prefix. Does not delete originals."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--verify", action="store_true")
        parser.add_argument("--rollback", action="store_true")
        parser.add_argument("--manifest", default="")

    def handle(self, *args, **options):
        reset_backend()
        if options["rollback"]:
            self._rollback(options["limit"])
            return
        if options["verify"]:
            self._verify(options["limit"])
            return
        manifest = self._manifest(options["manifest"])
        planned = self._plan(manifest)
        self.stdout.write(
            f"prefix={storage_prefix()} caption_only={planned['empty']} stored={planned['stored']} pending={len(planned['work'])}"
        )
        done = 0
        for item in planned["work"]:
            if done >= options["limit"]:
                break
            if options["dry_run"]:
                self.stdout.write(f"dry-run {item['label']} {item['pk']} {item['source']}")
                done += 1
                continue
            self._apply(item)
            done += 1
        self.stdout.write(f"processed={done}")

    def _manifest(self, path):
        if not path:
            return {}
        import json

        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        found = {}
        for row in payload:
            found[(row["model"], str(row["id"]), row["field"])] = row["source"]
        return found

    def _plan(self, manifest):
        empty = 0
        stored = 0
        work = []
        root = Path(settings.MEDIA_ROOT)
        for label, model, field, thumb in TARGETS:
            for obj in model.objects.order_by("pk"):
                current = getattr(obj, field).name
                source = manifest.get((label, str(obj.pk), field), current)
                if not source:
                    empty += 1
                    continue
                if key_in_scope(source):
                    stored += 1
                    continue
                work.append(
                    {
                        "label": label,
                        "model": model,
                        "pk": obj.pk,
                        "field": field,
                        "thumb": thumb,
                        "source": source,
                        "root": root,
                        "previous": current,
                    }
                )
        return {"empty": empty, "stored": stored, "work": work}

    def _source_file(self, item, limit):
        source = item["source"]
        if source.startswith(("https://", "http://")):
            return _fetch(source, limit), True
        path = (item["root"] / source).resolve()
        root = item["root"].resolve()
        if not str(path).startswith(str(root)) or not path.is_file():
            raise CommandError("local source is missing or outside MEDIA_ROOT")
        return path, False

    def _apply(self, item):
        from django.conf import settings as django_settings

        limit = max(
            django_settings.MEDIA_MAX_IMAGE_BYTES,
            django_settings.MEDIA_MAX_VIDEO_BYTES,
            django_settings.MEDIA_MAX_AUDIO_BYTES,
        )
        source_hash = hashlib.sha256(item["source"].encode("utf-8")).hexdigest()
        record, _created = MediaMigrationRecord.objects.get_or_create(
            model_label=item["label"],
            object_id=str(item["pk"]),
            field_name=item["field"],
            source_hash=source_hash,
            defaults={"source": item["source"], "previous_value": item["previous"], "status": "planned"},
        )
        if record.status == "applied":
            self.stdout.write(f"skip {item['label']} {item['pk']}")
            return
        temporary = False
        path = None
        try:
            path, temporary = self._source_file(item, limit)
            checksum, size = hash_path(path)
            if size < 1 or size > limit:
                raise CommandError("source size is not allowed")
            header = path.read_bytes()[:HEADER_BYTES]
            kind = ""
            content_type = ""
            for candidate in ("photo", "video", "audio"):
                try:
                    kind, content_type = detect(header, candidate)
                    break
                except Exception:
                    continue
            if not kind:
                raise CommandError("source content is not a supported media file")
            ext = EXT[content_type]
            if "profilemedia" in item["label"]:
                group = "profiles"
                owner_id = item["model"].objects.values_list("profile_id", flat=True).get(pk=item["pk"])
            elif item["label"].endswith("project"):
                group = "projects"
                owner_id = item["pk"]
            else:
                group = "testimonials"
                owner_id = item["pk"]
            destination = record.destination_key or f"{storage_prefix()}/{group}/{owner_id}/{uuid.uuid4()}{ext}"
            backend = get_backend()
            backend.put_file(destination, path, content_type)
            copied, copied_size = backend.hash_key(destination)
            if copied != checksum or copied_size != size:
                backend.delete(destination)
                raise CommandError("copied object did not match the source")
            thumb_key = ""
            if kind == "photo":
                try:
                    _body, thumb_type, thumb = process_image(path.read_bytes(), content_type)
                    thumb_key = f"{storage_prefix()}/{group}/{owner_id}/{uuid.uuid4()}-thumb.jpg"
                    backend.put_bytes(thumb_key, thumb, "image/jpeg")
                except Exception:
                    thumb_key = ""
            with transaction.atomic():
                obj = item["model"].objects.select_for_update().get(pk=item["pk"])
                getattr(obj, item["field"]).name = destination
                if thumb_key and hasattr(obj, item["thumb"]):
                    getattr(obj, item["thumb"]).name = thumb_key
                if hasattr(obj, "public_acl"):
                    obj.public_acl = False
                if hasattr(obj, "image_public_acl"):
                    obj.image_public_acl = False
                obj.save()
                record.destination_key = destination
                record.thumb_key = thumb_key
                record.checksum = checksum
                record.byte_size = size
                record.status = "applied"
                record.error = ""
                record.updated_at = timezone.now()
                record.save()
            self.stdout.write(f"applied {item['label']} {item['pk']}")
        except Exception as exc:
            record.status = "failed"
            record.error = str(exc)[:500]
            record.save(update_fields=["status", "error", "updated_at"])
            self.stdout.write(f"failed {item['label']} {item['pk']}: {record.error}")
        finally:
            if temporary and path is not None:
                path.unlink(missing_ok=True)

    def _verify(self, limit):
        checked = 0
        for record in MediaMigrationRecord.objects.filter(status="applied").order_by("pk")[:limit]:
            checked += 1
            try:
                checksum, size = get_backend().hash_key(record.destination_key)
            except Exception as exc:
                self.stdout.write(f"mismatch {record.object_id}: {exc.__class__.__name__}")
                continue
            if checksum != record.checksum or size != record.byte_size:
                self.stdout.write(f"mismatch {record.model_label} {record.object_id}")
            else:
                self.stdout.write(f"ok {record.model_label} {record.object_id}")
        self.stdout.write(f"verified={checked}")

    def _rollback(self, limit):
        changed = 0
        rows = MediaMigrationRecord.objects.filter(status="applied").order_by("pk")[:limit]
        models = {label: (model, thumb) for label, model, _field, thumb in TARGETS}
        for record in rows:
            found = models.get(record.model_label)
            if found is None:
                continue
            model, thumb = found
            with transaction.atomic():
                obj = model.objects.select_for_update().get(pk=record.object_id)
                getattr(obj, record.field_name).name = record.previous_value
                if record.thumb_key:
                    getattr(obj, thumb).name = ""
                obj.save()
                record.status = "rolled_back"
                record.save(update_fields=["status", "updated_at"])
            changed += 1
            self.stdout.write(f"rolled_back {record.model_label} {record.object_id}")
        self.stdout.write(f"rolled_back={changed}")
