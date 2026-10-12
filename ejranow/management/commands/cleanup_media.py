from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from ejranow.media_service import delete_key
from ejranow.models import PendingUpload, StorageCleanup, UploadStatus
from ejranow.storage import reset_backend


class Command(BaseCommand):
    help = "Delete abandoned uploads and retry object cleanup for this environment prefix only."

    def handle(self, *args, **options):
        reset_backend()
        now = timezone.now()
        cutoff = now - timedelta(hours=settings.MEDIA_ABANDON_HOURS)
        stale = PendingUpload.objects.filter(
            Q(status=UploadStatus.PENDING, expires_at__lt=now)
            | Q(
                status__in=[
                    UploadStatus.PENDING,
                    UploadStatus.VALIDATED,
                    UploadStatus.FAILED,
                    UploadStatus.EXPIRED,
                ],
                created_at__lt=cutoff,
            )
        )
        abandoned = 0
        for upload in stale.iterator():
            delete_key(upload.key)
            delete_key(upload.thumb_key)
            upload.status = UploadStatus.ABANDONED
            upload.save(update_fields=["status"])
            abandoned += 1
        retried = 0
        for row in StorageCleanup.objects.order_by("pk"):
            row.attempts += 1
            row.save(update_fields=["attempts"])
            delete_key(row.key)
            retried += 1
        self.stdout.write(f"abandoned={abandoned} retried={retried} remaining={StorageCleanup.objects.count()}")
