from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from ejranow.media_service import enqueue_delete, sync_stored_visibility
from ejranow.models import PUBLIC_PROJECT_STATUSES, Profile, ProfileMedia, Project, Testimonial


def _file_name(instance, field):
    value = getattr(instance, field, None)
    return getattr(value, "name", "") or ""


@receiver(post_delete, sender=ProfileMedia)
def delete_profile_media_files(sender, instance, **kwargs):
    enqueue_delete(_file_name(instance, "file"), _file_name(instance, "thumbnail"))


@receiver(post_delete, sender=Profile)
def delete_profile_pictures(sender, instance, **kwargs):
    enqueue_delete(
        _file_name(instance, "list_image"),
        _file_name(instance, "list_thumb"),
        _file_name(instance, "banner"),
        _file_name(instance, "banner_thumb"),
    )


@receiver(post_delete, sender=Project)
def delete_project_files(sender, instance, **kwargs):
    enqueue_delete(_file_name(instance, "image"), _file_name(instance, "image_thumb"))


@receiver(post_delete, sender=Testimonial)
def delete_testimonial_files(sender, instance, **kwargs):
    enqueue_delete(_file_name(instance, "image"), _file_name(instance, "image_thumb"))


@receiver(pre_save, sender=Project)
def remember_project_media(sender, instance, **kwargs):
    if not instance.pk:
        instance._media_before = None
        return
    instance._media_before = (
        Project.objects.filter(pk=instance.pk).values_list("status", "image", "image_public_acl").first()
    )


def _apply_project_visibility(project_id):
    project = Project.objects.filter(pk=project_id).first()
    if project is None or not project.image:
        return
    public = project.status in PUBLIC_PROJECT_STATUSES
    ok = sync_stored_visibility(project.image.name, project.image_thumb.name, public)
    if project.image_public_acl != ok:
        Project.objects.filter(pk=project.pk).update(image_public_acl=ok)


@receiver(post_save, sender=Project)
def sync_project_media(sender, instance, **kwargs):
    if not instance.image:
        return
    current = (instance.status, instance.image.name, instance.image_public_acl)
    if getattr(instance, "_media_before", None) == current:
        return
    project_id = instance.pk
    transaction.on_commit(lambda: _apply_project_visibility(project_id))


@receiver(pre_save, sender=ProfileMedia)
def remember_profile_media(sender, instance, **kwargs):
    if not instance.pk:
        instance._media_before = None
        return
    instance._media_before = (
        ProfileMedia.objects.filter(pk=instance.pk).values_list("is_public", "file", "public_acl").first()
    )


def _apply_profile_visibility(media_id):
    item = ProfileMedia.objects.filter(pk=media_id).first()
    if item is None or not item.file:
        return
    ok = sync_stored_visibility(item.file.name, item.thumbnail.name, item.is_public)
    if item.public_acl != ok:
        ProfileMedia.objects.filter(pk=item.pk).update(public_acl=ok)


@receiver(post_save, sender=ProfileMedia)
def sync_profile_media(sender, instance, **kwargs):
    if not instance.file:
        return
    current = (instance.is_public, instance.file.name, instance.public_acl)
    if getattr(instance, "_media_before", None) == current:
        return
    media_id = instance.pk
    transaction.on_commit(lambda: _apply_profile_visibility(media_id))
