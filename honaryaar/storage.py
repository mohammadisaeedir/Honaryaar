"""ParsPack object storage for uploaded media.

Endpoint, region, bucket, and keys come from the environment. Signature V4 and
path-style addressing follow ParsPack's AWS S3 protocol and its connection
guide: entering the host by hand causes DNS errors, and ParsPack's client
profile corrects that addressing. `parspack_check` confirms the pair.
"""

import os
import re
from urllib.parse import quote

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible

_PREFIX = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
UPLOAD_CONTENT_TYPE = "application/octet-stream"
_backend = None


def parspack_configured():
    endpoint = settings.PARSPACK_ENDPOINT_URL
    return bool(
        settings.PARSPACK_ACCESS_KEY_ID
        and settings.PARSPACK_SECRET_ACCESS_KEY
        and endpoint.startswith("https://")
        and settings.PARSPACK_BUCKET_NAME
        and settings.PARSPACK_REGION_NAME
    )


def storage_prefix():
    from honaryaar.data_source import preview_active

    if preview_active():
        return "production"
    raw = (settings.MEDIA_STORAGE_PREFIX or "").strip().strip("/")
    if not raw:
        vercel = os.environ.get("VERCEL_ENV", "")
        if vercel == "production":
            raw = "production"
        elif vercel == "preview":
            raw = "preview"
        else:
            raw = "dev"
    if not _PREFIX.match(raw):
        raise ImproperlyConfigured(
            "MEDIA_STORAGE_PREFIX must be a short token such as dev, preview, or production."
        )
    return raw


def key_in_scope(key):
    if not isinstance(key, str) or not key or key.startswith(("/", "\\")) or "\\" in key:
        return False
    parts = key.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return False
    return parts[0] == storage_prefix()


def upload_origins():
    configured = [item.strip() for item in settings.MEDIA_UPLOAD_ORIGINS.split(",") if item.strip()]
    if configured:
        return configured
    prefix = storage_prefix()
    if prefix == "production":
        return [
            "https://honaryaar.ir",
            "https://www.honaryaar.ir",
            "https://honaryaar.vercel.app",
        ]
    if prefix == "preview":
        return []
    return ["http://127.0.0.1:8000", "http://localhost:8000"]


def cors_configuration():
    return {
        "CORSRules": [
            {
                "AllowedOrigins": upload_origins(),
                "AllowedMethods": ["GET", "HEAD", "PUT"],
                "AllowedHeaders": ["content-type"],
                "ExposeHeaders": ["ETag", "Accept-Ranges", "Content-Range", "Content-Length"],
                "MaxAgeSeconds": 600,
            }
        ]
    }


def merge_cors(existing, desired):
    """Add this app's upload rule and keep every unrelated rule."""
    rules = [dict(rule) for rule in (existing or {}).get("CORSRules") or []]
    addition = dict(desired["CORSRules"][0])
    wanted = set(addition["AllowedMethods"])
    merged = []
    consumed = False
    for rule in rules:
        methods = set(rule.get("AllowedMethods") or [])
        if methods == wanted and not consumed:
            rule["AllowedOrigins"] = list(
                dict.fromkeys(list(rule.get("AllowedOrigins") or []) + list(addition["AllowedOrigins"]))
            )
            rule["AllowedHeaders"] = list(
                dict.fromkeys(list(rule.get("AllowedHeaders") or []) + list(addition["AllowedHeaders"]))
            )
            rule["ExposeHeaders"] = list(
                dict.fromkeys(list(rule.get("ExposeHeaders") or []) + list(addition["ExposeHeaders"]))
            )
            rule["MaxAgeSeconds"] = addition["MaxAgeSeconds"]
            merged.append(rule)
            consumed = True
        else:
            merged.append(rule)
    if not consumed:
        merged.append(addition)
    return {"CORSRules": merged}


def choose_media_url(*, key, public, public_acl, base, endpoint, bucket, signed):
    if public and base:
        return f"{base.rstrip('/')}/{quote(key, safe='/')}"
    if public and public_acl and endpoint and bucket:
        return f"{endpoint.rstrip('/')}/{bucket}/{quote(key, safe='/')}"
    return signed


def reset_backend():
    global _backend
    _backend = None


def get_backend():
    global _backend
    if _backend is None:
        _backend = ParsPackBackend() if parspack_configured() else LocalBackend()
    return _backend


def _local_storage():
    return FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)


class LocalBackend:
    remote = False

    def path(self, key):
        if not key_in_scope(key):
            raise PermissionError(key)
        root = settings.MEDIA_ROOT
        path = (root / key).resolve()
        if not str(path).startswith(str(root.resolve())):
            raise PermissionError(key)
        return path

    def url(self, key):
        if not key_in_scope(key):
            return ""
        return _local_storage().url(key)

    def signed_url(self, key, expires=600, kind="photo"):
        return self.url(key)

    def public_url(self, key):
        return self.url(key)

    def presign_put(self, key, expires):
        return self.url(key)

    def head(self, key):
        path = self.path(key)
        if not path.is_file():
            return None
        return {"size": path.stat().st_size}

    def read(self, key, start=0, end=None):
        path = self.path(key)
        with path.open("rb") as handle:
            handle.seek(max(0, start))
            if end is None:
                return handle.read()
            return handle.read(max(0, end - start + 1))

    def put_bytes(self, key, body, content_type):
        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)

    def put_file(self, key, source, content_type):
        self.put_bytes(key, source.read_bytes(), content_type)

    def copy(self, source, dest, content_type):
        self.put_bytes(dest, self.read(source), content_type)

    def delete(self, key):
        if not key_in_scope(key):
            return False
        path = self.path(key)
        if path.is_file():
            path.unlink()
        return True

    def hash_key(self, key):
        import hashlib

        digest = hashlib.sha256()
        payload = self.read(key)
        digest.update(payload)
        return digest.hexdigest(), len(payload)

    def set_public(self, key):
        return key_in_scope(key) and self.head(key) is not None

    def set_private(self, key):
        return key_in_scope(key)


class ParsPackBackend:
    remote = True

    def __init__(self):
        self.storage = ParsPackStorage()

    def client(self):
        return self.storage.connection.meta.client

    def bucket(self):
        return settings.PARSPACK_BUCKET_NAME

    def signed_url(self, key, expires=600, kind="photo"):
        if not key_in_scope(key):
            return ""
        if kind in {"video", "audio"}:
            expires = max(expires, 6 * 3600)
        return self.client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket(), "Key": key},
            ExpiresIn=expires,
            HttpMethod="GET",
        )

    def public_url(self, key):
        if not key_in_scope(key):
            return ""
        return choose_media_url(
            key=key,
            public=True,
            public_acl=True,
            base=settings.PARSPACK_PUBLIC_MEDIA_BASE_URL,
            endpoint=settings.PARSPACK_ENDPOINT_URL,
            bucket=self.bucket(),
            signed="",
        )

    def presign_put(self, key, expires):
        if not key_in_scope(key):
            raise PermissionError(key)
        return self.client().generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket(),
                "Key": key,
                "ContentType": UPLOAD_CONTENT_TYPE,
            },
            ExpiresIn=expires,
            HttpMethod="PUT",
        )

    def head(self, key):
        from botocore.exceptions import ClientError

        if not key_in_scope(key):
            return None
        try:
            found = self.client().head_object(Bucket=self.bucket(), Key=key)
        except ClientError:
            return None
        return {"size": int(found.get("ContentLength") or 0)}

    def read(self, key, start=0, end=None):
        if not key_in_scope(key):
            raise PermissionError(key)
        kwargs = {"Bucket": self.bucket(), "Key": key}
        if end is not None:
            kwargs["Range"] = f"bytes={start}-{end}"
        found = self.client().get_object(**kwargs)
        return found["Body"].read()

    def put_bytes(self, key, body, content_type):
        if not key_in_scope(key):
            raise PermissionError(key)
        self.client().put_object(
            Bucket=self.bucket(),
            Key=key,
            Body=body,
            ContentType=content_type,
        )

    def put_file(self, key, source, content_type):
        if not key_in_scope(key):
            raise PermissionError(key)
        self.client().upload_fileobj(
            source.open("rb"),
            self.bucket(),
            key,
            ExtraArgs={"ContentType": content_type},
        )

    def copy(self, source, dest, content_type):
        if not key_in_scope(source) or not key_in_scope(dest):
            raise PermissionError(dest)
        self.client().copy_object(
            Bucket=self.bucket(),
            Key=dest,
            CopySource={"Bucket": self.bucket(), "Key": source},
            ContentType=content_type,
            MetadataDirective="REPLACE",
        )

    def delete(self, key):
        if not key_in_scope(key):
            return False
        self.client().delete_object(Bucket=self.bucket(), Key=key)
        return True

    def hash_key(self, key):
        import hashlib

        digest = hashlib.sha256()
        size = 0
        found = self.client().get_object(Bucket=self.bucket(), Key=key)
        body = found["Body"]
        while True:
            chunk = body.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
        return digest.hexdigest(), size

    def set_public(self, key):
        from botocore.exceptions import ClientError

        if not key_in_scope(key):
            return False
        try:
            self.client().put_object_acl(Bucket=self.bucket(), Key=key, ACL="public-read")
        except ClientError:
            return False
        return True

    def set_private(self, key):
        from botocore.exceptions import ClientError

        if not key_in_scope(key):
            return False
        try:
            self.client().put_object_acl(Bucket=self.bucket(), Key=key, ACL="private")
        except ClientError:
            return False
        return True


@deconstructible
class ParsPackStorage(Storage):
    def __init__(self, **kwargs):
        from storages.backends.s3 import S3Storage

        self._delegate = S3Storage(
            access_key=settings.PARSPACK_ACCESS_KEY_ID or None,
            secret_key=settings.PARSPACK_SECRET_ACCESS_KEY or None,
            bucket_name=settings.PARSPACK_BUCKET_NAME or None,
            endpoint_url=settings.PARSPACK_ENDPOINT_URL or None,
            region_name=settings.PARSPACK_REGION_NAME or None,
            signature_version="s3v4",
            addressing_style="path",
            default_acl=None,
            querystring_auth=True,
            querystring_expire=max(60, min(int(settings.MEDIA_PRESIGN_SECONDS or 600), 3600)),
            file_overwrite=True,
            location="",
        )

    @property
    def connection(self):
        return self._delegate.connection

    def _open(self, name, mode="rb"):
        return self._delegate._open(name, mode)

    def _save(self, name, content):
        return self._delegate._save(name, content)

    def delete(self, name):
        if key_in_scope(name):
            self._delegate.delete(name)

    def exists(self, name):
        return self._delegate.exists(name)

    def size(self, name):
        return self._delegate.size(name)

    def url(self, name):
        return get_backend().signed_url(name)


@deconstructible
class MediaStorage(Storage):
    """File-field storage. Static assets never come through here."""

    def _delegate(self):
        if parspack_configured():
            return ParsPackStorage()
        return _local_storage()

    def _open(self, name, mode="rb"):
        return self._delegate()._open(name, mode)

    def _save(self, name, content):
        return self._delegate()._save(name, content)

    def delete(self, name):
        if name and key_in_scope(name):
            self._delegate().delete(name)

    def exists(self, name):
        if not name:
            return False
        return self._delegate().exists(name)

    def size(self, name):
        return self._delegate().size(name)

    def url(self, name):
        return get_backend().signed_url(name)

    def get_available_name(self, name, max_length=None):
        return name
