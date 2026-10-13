"""Authorize, publish, and clean uploaded media.

Browsers send file bytes to ParsPack. This module only handles keys,
permissions, and a bounded check of what landed in the bucket.
"""

import hashlib
import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from honaryaar.accounts import ensure_profile
from honaryaar.media_files import (
    BAD_REQUEST,
    EMPTY_FILE,
    EXPIRED,
    EXT,
    HEADER_BYTES,
    IMAGE_ONLY,
    INCOMPLETE,
    KIND_MISMATCH,
    MISSING,
    NEED_FILE,
    NEED_IMAGE,
    NEED_LABEL,
    NOT_READY,
    PERMISSION,
    SIZE_MISMATCH,
    TOO_LARGE,
    UPLOAD_USED,
    UPLOAD_WRONG,
    MediaError,
    detect,
    max_bytes,
    process_image,
)
from honaryaar.models import (
    PUBLIC_PROJECT_STATUSES,
    PendingUpload,
    Profile,
    ProfileMedia,
    Project,
    StorageCleanup,
    Testimonial,
    UploadStatus,
)
from honaryaar.storage import (
    UPLOAD_CONTENT_TYPE,
    choose_media_url,
    get_backend,
    key_in_scope,
    parspack_configured,
    storage_prefix,
)

logger = logging.getLogger("honaryaar.media")
GROUPS = {
    "profile": "profiles",
    "profile_list": "profiles",
    "profile_banner": "profiles",
    "project": "projects",
    "testimonial": "testimonials",
}
PICTURES = {"profile_list", "profile_banner", "project", "testimonial"}


def presign_seconds():
    return max(60, min(int(settings.MEDIA_PRESIGN_SECONDS), 3600))


def url_for_key(key, *, public=False, public_acl=False, kind="photo"):
    if not key or not key_in_scope(key):
        return ""
    backend = get_backend()
    if not backend.remote:
        return backend.url(key)
    signed = ""
    try:
        if not (public and (public_acl or settings.PARSPACK_PUBLIC_MEDIA_BASE_URL)):
            signed = backend.signed_url(key, kind=kind)
        return choose_media_url(
            key=key,
            public=public,
            public_acl=public_acl,
            base=settings.PARSPACK_PUBLIC_MEDIA_BASE_URL,
            endpoint=settings.PARSPACK_ENDPOINT_URL,
            bucket=settings.PARSPACK_BUCKET_NAME,
            signed=signed,
        )
    except Exception:
        logger.exception("media url failed")
        return ""


def _require_storage():
    if getattr(settings, "MEDIA_STORAGE_TESTING", False):
        return
    if not parspack_configured():
        raise MediaError(NOT_READY, 503)


def authorize(user, purpose, target_id):
    if purpose not in GROUPS:
        raise MediaError(BAD_REQUEST)
    if purpose == "testimonial":
        if not getattr(user, "is_staff", False):
            raise MediaError(PERMISSION, 403)
        if target_id and not Testimonial.objects.filter(pk=target_id).exists():
            raise MediaError(PERMISSION, 403)
        return target_id
    if purpose in {"profile", "profile_list", "profile_banner"}:
        if getattr(user, "is_staff", False) and target_id:
            if not Profile.objects.filter(pk=target_id).exists():
                raise MediaError(PERMISSION, 403)
            return target_id
        profile = ensure_profile(user)
        if profile is None or (target_id and target_id != profile.id):
            raise MediaError(PERMISSION, 403)
        return profile.id
    project = None
    if target_id:
        project = Project.objects.filter(pk=target_id).first()
        if project is None:
            raise MediaError(PERMISSION, 403)
    if getattr(user, "is_staff", False):
        return project.id if project else None
    profile = ensure_profile(user)
    if profile is None:
        raise MediaError(PERMISSION, 403)
    if project and project.owner_id != profile.id:
        raise MediaError(PERMISSION, 403)
    return project.id if project else None


def _within_limit(profile, replacing):
    if replacing:
        return
    limit = settings.MEDIA_PROFILE_MAX_ITEMS
    existing = profile.media_items.count()
    inflight = PendingUpload.objects.filter(
        purpose="profile",
        target_id=profile.id,
        status__in=[UploadStatus.PENDING, UploadStatus.VALIDATED],
    ).count()
    if existing + inflight >= limit:
        raise MediaError(f"حداکثر {limit} فایل برای پروفایل مجاز است.")


def start_upload(user, payload):
    _require_storage()
    if not isinstance(payload, dict):
        raise MediaError(BAD_REQUEST)
    purpose = payload.get("purpose")
    kind = payload.get("kind") or "photo"
    if kind not in {"photo", "video", "audio"}:
        raise MediaError(BAD_REQUEST)
    if purpose in PICTURES and kind != "photo":
        raise MediaError(IMAGE_ONLY)
    size = payload.get("size")
    if isinstance(size, bool) or not isinstance(size, int) or size < 1:
        raise MediaError(BAD_REQUEST)
    if size > max_bytes(kind):
        raise MediaError(TOO_LARGE)
    raw_target = payload.get("target_id")
    if raw_target in (None, ""):
        target_id = None
    elif isinstance(raw_target, int) and not isinstance(raw_target, bool):
        target_id = raw_target
    else:
        raise MediaError(BAD_REQUEST)
    target_id = authorize(user, purpose, target_id)
    if purpose == "profile":
        _within_limit(Profile.objects.get(pk=target_id), payload.get("replacing") is True)
    token = uuid.uuid4()
    key = f"{storage_prefix()}/{GROUPS[purpose]}/pending/{user.id}/{token}"
    expires = presign_seconds()
    upload = PendingUpload.objects.create(
        id=token,
        owner=user,
        purpose=purpose,
        target_id=target_id,
        key=key,
        declared_size=size,
        requested_kind=kind,
        status=UploadStatus.PENDING,
        expires_at=timezone.now() + timedelta(seconds=expires),
    )
    url = get_backend().presign_put(key, expires)
    return {
        "id": str(upload.id),
        "url": url,
        "method": "PUT",
        "headers": {"Content-Type": UPLOAD_CONTENT_TYPE},
        "expires_in": expires,
    }


def complete_upload(user, upload_id):
    _require_storage()
    failure = None
    try:
        with transaction.atomic():
            try:
                upload = PendingUpload.objects.select_for_update().get(pk=upload_id)
            except PendingUpload.DoesNotExist:
                raise MediaError(PERMISSION, 403) from None
            if upload.owner_id != user.id:
                raise MediaError(PERMISSION, 403)
            if upload.status == UploadStatus.VALIDATED:
                return _preview(upload)
            if upload.status != UploadStatus.PENDING:
                raise MediaError(UPLOAD_USED)
            if upload.expires_at <= timezone.now():
                failure = (upload.pk, EXPIRED, UploadStatus.EXPIRED, "", "")
                raise MediaError(EXPIRED)
            try:
                _verify(upload)
            except MediaError as exc:
                failure = (upload.pk, exc.message, UploadStatus.FAILED, upload.key, upload.thumb_key)
                raise
            upload.status = UploadStatus.VALIDATED
            upload.validated_at = timezone.now()
            upload.save()
            return _preview(upload)
    except MediaError:
        if failure:
            pk, message, status, key, thumb = failure
            PendingUpload.objects.filter(pk=pk).update(status=status, error=message[:200])
            if status == UploadStatus.FAILED:
                transaction.on_commit(lambda key=key: delete_key(key))
                if thumb:
                    transaction.on_commit(lambda key=thumb: delete_key(key))
        raise


def _verify(upload):
    backend = get_backend()
    found = backend.head(upload.key)
    if not found:
        raise MediaError(MISSING)
    size = int(found["size"])
    if size < 1:
        raise MediaError(EMPTY_FILE)
    if size > max_bytes(upload.requested_kind):
        raise MediaError(TOO_LARGE)
    if size != upload.declared_size:
        raise MediaError(SIZE_MISMATCH)
    if upload.requested_kind == "photo":
        payload = backend.read(upload.key)
        if len(payload) != size:
            raise MediaError(INCOMPLETE)
        kind, content_type = detect(payload[:HEADER_BYTES], upload.requested_kind)
        body, content_type, thumb = process_image(payload, content_type)
        ext = EXT[content_type]
        final_pending = f"{upload.key}{ext}"
        thumb_key = f"{upload.key}-thumb.jpg"
        backend.put_bytes(final_pending, body, content_type)
        backend.put_bytes(thumb_key, thumb, "image/jpeg")
        if final_pending != upload.key:
            backend.delete(upload.key)
        upload.key = final_pending
        upload.thumb_key = thumb_key
        upload.kind = kind
        upload.content_type = content_type
        upload.actual_size = len(body)
        upload.checksum = hashlib.sha256(body).hexdigest()
        return
    header = backend.read(upload.key, 0, HEADER_BYTES - 1)
    if len(header) < 12:
        raise MediaError(BAD_FILE)
    kind, content_type = detect(header, upload.requested_kind)
    ext = EXT[content_type]
    final_pending = f"{upload.key}{ext}"
    if final_pending != upload.key:
        backend.copy(upload.key, final_pending, content_type)
        backend.delete(upload.key)
    else:
        try:
            backend.copy(upload.key, upload.key, content_type)
        except Exception:
            logger.info("content type update skipped")
    upload.key = final_pending
    upload.kind = kind
    upload.content_type = content_type
    upload.actual_size = size
    upload.checksum = hashlib.sha256(header).hexdigest()


def _preview(upload):
    return {
        "id": str(upload.id),
        "kind": upload.kind,
        "preview_url": url_for_key(upload.key, public=False, kind=upload.kind),
        "thumb_url": url_for_key(upload.thumb_key, public=False, kind="photo") if upload.thumb_key else "",
    }


def _assert_publish_target(user, purpose, target_id):
    authorize(user, purpose, target_id)
    if purpose == "project":
        project = Project.objects.filter(pk=target_id).only("status").first()
        if project is None:
            raise MediaError(PERMISSION, 403)
        return project.status in PUBLIC_PROJECT_STATUSES
    if purpose in {"profile", "profile_list", "profile_banner"}:
        if not Profile.objects.filter(pk=target_id).exists():
            raise MediaError(PERMISSION, 403)
        return True
    if not Testimonial.objects.filter(pk=target_id).exists():
        raise MediaError(PERMISSION, 403)
    return True


def publish_upload(user, upload_id, *, purpose, target_id, public):
    _require_storage()
    with transaction.atomic():
        try:
            upload = PendingUpload.objects.select_for_update().get(pk=upload_id)
        except PendingUpload.DoesNotExist:
            raise MediaError(PERMISSION, 403) from None
        if upload.owner_id != user.id:
            raise MediaError(PERMISSION, 403)
        if upload.purpose != purpose:
            raise MediaError(UPLOAD_WRONG)
        if upload.status != UploadStatus.VALIDATED:
            raise MediaError(UPLOAD_USED)
        if upload.target_id and upload.target_id != target_id:
            raise MediaError(PERMISSION, 403)
        horizon = timezone.now() - timedelta(hours=settings.MEDIA_ABANDON_HOURS)
        if upload.validated_at and upload.validated_at < horizon:
            raise MediaError(EXPIRED)
        intended_public = _assert_publish_target(user, purpose, target_id)
        public = bool(public and intended_public)
        if purpose in PICTURES and upload.kind != "photo":
            raise MediaError(IMAGE_ONLY)
        ext = EXT[upload.content_type]
        final = f"{storage_prefix()}/{GROUPS[purpose]}/{target_id}/{upload.id}{ext}"
        thumb_final = ""
        if upload.thumb_key:
            thumb_final = f"{storage_prefix()}/{GROUPS[purpose]}/{target_id}/{upload.id}-thumb.jpg"
        pending_key = upload.key
        pending_thumb = upload.thumb_key
        backend = get_backend()
        backend.copy(pending_key, final, upload.content_type)
        if pending_thumb and thumb_final:
            backend.copy(pending_thumb, thumb_final, "image/jpeg")
        public_acl = False
        if public:
            public_acl = backend.set_public(final)
            if thumb_final:
                backend.set_public(thumb_final)
        else:
            backend.set_private(final)
            if thumb_final:
                backend.set_private(thumb_final)
        upload.key = final
        upload.thumb_key = thumb_final
        upload.target_id = target_id
        upload.status = UploadStatus.PUBLISHED
        upload.public_acl = public_acl
        upload.save()

        def _drop_pending():
            if pending_key != final:
                delete_key(pending_key)
            if pending_thumb and pending_thumb != thumb_final:
                delete_key(pending_thumb)

        transaction.on_commit(_drop_pending)
        return upload


def enqueue_delete(*keys):
    pending = [key for key in keys if key]

    def _run():
        for key in pending:
            delete_key(key)

    transaction.on_commit(_run)


def delete_key(key, attempts=3):
    if not key or not key_in_scope(key):
        return False
    if _referenced(key):
        return False
    backend = get_backend()
    error = ""
    for _ in range(attempts):
        try:
            backend.delete(key)
            StorageCleanup.objects.filter(key=key).delete()
            return True
        except Exception as exc:
            error = str(exc)[:200]
            logger.exception("media delete failed")
    StorageCleanup.objects.update_or_create(key=key, defaults={"last_error": error})
    return False


def _referenced(key):
    if not key:
        return False
    return (
        ProfileMedia.objects.filter(models.Q(file=key) | models.Q(thumbnail=key)).exists()
        or Profile.objects.filter(
            models.Q(list_image=key)
            | models.Q(list_thumb=key)
            | models.Q(banner=key)
            | models.Q(banner_thumb=key)
        ).exists()
        or Project.objects.filter(models.Q(image=key) | models.Q(image_thumb=key)).exists()
        or Testimonial.objects.filter(models.Q(image=key) | models.Q(image_thumb=key)).exists()
    )


def assign_file(instance, field, key):
    getattr(instance, field).name = key or ""


def profile_limit_error(profile, rows):
    final = 0
    for row in rows:
        if not row or row.get("delete"):
            continue
        if row.get("media_id") or (row.get("label") or "").strip() or row.get("upload_id"):
            final += 1
    limit = settings.MEDIA_PROFILE_MAX_ITEMS
    if final > limit and final > profile.media_items.count():
        raise MediaError(f"حداکثر {limit} فایل برای پروفایل مجاز است.")


def save_profile_media(profile, rows, user):
    profile_limit_error(profile, rows)
    owned = {item.id: item for item in profile.media_items.all()}
    position = 0
    for row in rows:
        if not row:
            continue
        media_id = row.get("media_id")
        current = owned.get(media_id)
        if media_id and current is None:
            continue
        if row.get("delete"):
            if current:
                current.delete()
            continue
        label = (row.get("label") or "").strip()
        upload_id = row.get("upload_id")
        if current is None and not upload_id:
            if label:
                raise MediaError(NEED_FILE)
            continue
        if upload_id and not label:
            raise MediaError(NEED_LABEL)
        if not label and current is None:
            continue
        if not label:
            continue
        if upload_id:
            published = publish_upload(
                user,
                upload_id,
                purpose="profile",
                target_id=profile.id,
                public=True,
            )
            if current is None:
                current = ProfileMedia(profile=profile, is_public=True)
            else:
                enqueue_delete(current.file.name, current.thumbnail.name)
            current.kind = published.kind
            current.label = label
            current.position = position
            current.is_public = True
            current.public_acl = published.public_acl
            assign_file(current, "file", published.key)
            assign_file(current, "thumbnail", published.thumb_key)
            current.save()
        else:
            current.label = label
            if not current.file:
                current.kind = row.get("kind") or current.kind
            current.position = position
            current.save()
        position += 1


def attach_profile_picture(user, profile, upload_id, *, field, remove=False):
    thumb = "list_thumb" if field == "list_image" else "banner_thumb"
    acl_field = "list_public_acl" if field == "list_image" else "banner_public_acl"
    purpose = "profile_list" if field == "list_image" else "profile_banner"
    current = getattr(profile, field).name
    current_thumb = getattr(profile, thumb).name
    if upload_id:
        published = publish_upload(
            user,
            upload_id,
            purpose=purpose,
            target_id=profile.id,
            public=True,
        )
        assign_file(profile, field, published.key)
        assign_file(profile, thumb, published.thumb_key)
        setattr(profile, acl_field, published.public_acl)
        profile.save(update_fields=[field, thumb, acl_field])
        enqueue_delete(current, current_thumb)
        return
    if remove and current:
        assign_file(profile, field, "")
        assign_file(profile, thumb, "")
        setattr(profile, acl_field, False)
        profile.save(update_fields=[field, thumb, acl_field])
        enqueue_delete(current, current_thumb)


def attach_project_image(user, project, upload_id, *, required=False, remove=False):
    if upload_id:
        old = project.image.name
        old_thumb = project.image_thumb.name
        published = publish_upload(
            user,
            upload_id,
            purpose="project",
            target_id=project.id,
            public=project.status in PUBLIC_PROJECT_STATUSES,
        )
        assign_file(project, "image", published.key)
        assign_file(project, "image_thumb", published.thumb_key)
        project.image_public_acl = published.public_acl
        project.save(update_fields=["image", "image_thumb", "image_public_acl"])
        enqueue_delete(old, old_thumb)
        return
    if remove and project.image:
        old = project.image.name
        old_thumb = project.image_thumb.name
        assign_file(project, "image", "")
        assign_file(project, "image_thumb", "")
        project.image_public_acl = False
        project.save(update_fields=["image", "image_thumb", "image_public_acl"])
        enqueue_delete(old, old_thumb)
        return
    if required and not project.image:
        raise MediaError(NEED_IMAGE)


def attach_testimonial_image(user, item, upload_id, *, remove=False):
    if not upload_id and not remove:
        return
    if upload_id:
        old = item.image.name
        old_thumb = item.image_thumb.name
        published = publish_upload(
            user,
            upload_id,
            purpose="testimonial",
            target_id=item.id,
            public=True,
        )
        assign_file(item, "image", published.key)
        assign_file(item, "image_thumb", published.thumb_key)
        item.image_public_acl = published.public_acl
        item.save(update_fields=["image", "image_thumb", "image_public_acl"])
        enqueue_delete(old, old_thumb)
        return
    if item.image:
        old = item.image.name
        old_thumb = item.image_thumb.name
        assign_file(item, "image", "")
        assign_file(item, "image_thumb", "")
        item.image_public_acl = False
        item.save(update_fields=["image", "image_thumb", "image_public_acl"])
        enqueue_delete(old, old_thumb)


def sync_stored_visibility(key, thumb, public):
    if not key or not key_in_scope(key):
        return False
    backend = get_backend()
    if public:
        ok = backend.set_public(key)
        if thumb:
            backend.set_public(thumb)
        return ok
    backend.set_private(key)
    if thumb:
        backend.set_private(thumb)
    return False


def parse_upload_id(raw):
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw))
    except (TypeError, ValueError):
        raise MediaError(BAD_REQUEST) from None


def hash_path(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size
