import os

from django.core.management.base import BaseCommand, CommandError
from django.db import connection


KEEP = (
    "auth_group",
    "auth_group_permissions",
    "auth_permission",
    "auth_user",
    "auth_user_groups",
    "auth_user_user_permissions",
    "django_content_type",
    "django_migrations",
    "honaryaar_artcategory",
    "honaryaar_city",
    "honaryaar_role",
    "honaryaar_skill",
)

CLEAR = (
    "honaryaar_application",
    "honaryaar_bookmark",
    "honaryaar_credit",
    "honaryaar_invite",
    "honaryaar_match",
    "honaryaar_mediamigrationrecord",
    "honaryaar_opportunity",
    "honaryaar_pendingupload",
    "honaryaar_profile",
    "honaryaar_profilemedia",
    "honaryaar_profilerole",
    "honaryaar_profileskill",
    "honaryaar_project",
    "honaryaar_storagecleanup",
    "honaryaar_supportticket",
    "honaryaar_testimonial",
    "honaryaar_ticketmessage",
    "django_admin_log",
    "django_session",
)


class Command(BaseCommand):
    help = "Remove imported content. Users, groups, and catalogue tables stay."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        if os.environ.get("CLEAR_CONTENT") != "1" and not options["dry_run"]:
            self.stdout.write("skipped; CLEAR_CONTENT is not 1")
            return
        quote = connection.ops.quote_name
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
            present = {row[0] for row in cursor.fetchall()}
            targets = [name for name in CLEAR if name in present]
            missing = [name for name in CLEAR if name not in present]
            if missing:
                self.stdout.write("missing " + ", ".join(missing))
            if not targets:
                self.stdout.write("nothing to clear")
                return
            affected = self._cascade_targets(cursor, targets)
            protected = sorted(set(affected) & set(KEEP))
            if protected:
                raise CommandError(
                    "refusing to clear catalogue or accounts: " + ", ".join(protected)
                )
            self._write_counts(cursor, targets, "before")
            self._write_counts(cursor, [name for name in KEEP if name in present], "kept")
            if options["dry_run"]:
                self.stdout.write("dry-run " + ", ".join(targets))
                return
            listed = ", ".join(quote(name) for name in targets)
            cursor.execute(f"TRUNCATE {listed} RESTART IDENTITY CASCADE")
            self._write_counts(cursor, targets, "after")

    def _cascade_targets(self, cursor, targets):
        cursor.execute(
            """
            WITH RECURSIVE refs AS (
                SELECT c.oid, c.relname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relname = ANY(%s)
                UNION
                SELECT child.oid, child.relname
                FROM pg_constraint con
                JOIN refs ON con.confrelid = refs.oid
                JOIN pg_class child ON child.oid = con.conrelid
                JOIN pg_namespace n ON n.oid = child.relnamespace
                WHERE n.nspname = 'public' AND con.contype = 'f'
            )
            SELECT relname FROM refs
            """,
            [list(targets)],
        )
        return [row[0] for row in cursor.fetchall()]

    def _write_counts(self, cursor, names, label):
        for name in names:
            cursor.execute(f'SELECT count(*) FROM "{name}"')
            self.stdout.write(f"{label} {name} {cursor.fetchone()[0]}")
