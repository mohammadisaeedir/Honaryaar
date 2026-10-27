from django.conf import settings
from django.core.management.base import BaseCommand

from honaryaar.notifications import purge_old_logs


class Command(BaseCommand):
    help = "Delete notification log rows older than NOTIFICATION_LOG_RETENTION_DAYS."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Override retention window in days (default: settings.NOTIFICATION_LOG_RETENTION_DAYS).",
        )

    def handle(self, *args, **options):
        days = options["days"]
        if days is None:
            days = int(getattr(settings, "NOTIFICATION_LOG_RETENTION_DAYS", 90))
        deleted = purge_old_logs(days=days)
        self.stdout.write(f"deleted={deleted} retention_days={days}")
