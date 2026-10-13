from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Rename stored ejranow tables and migration rows to honaryaar. Safe to run more than once."

    def handle(self, *args, **options):
        quote = connection.ops.quote_name
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.django_migrations')")
            if cursor.fetchone()[0] is None:
                self.stdout.write("no migrations table yet")
                return
            cursor.execute(
                """
                SELECT 1 FROM django_migrations WHERE app = %s
                UNION ALL
                SELECT 1 FROM pg_tables
                WHERE schemaname = 'public' AND tablename LIKE %s
                LIMIT 1
                """,
                ["ejranow", r"ejranow\_%"],
            )
            if cursor.fetchone() is None:
                self.stdout.write("already honaryaar")
                return

        with transaction.atomic():
            with connection.cursor() as cursor:
                renamed = self._rename_relations(cursor, quote, "r", "TABLE")
                renamed += self._rename_relations(cursor, quote, "i", "INDEX")
                renamed += self._rename_relations(cursor, quote, "S", "SEQUENCE")
                renamed += self._rename_constraints(cursor, quote)
                cursor.execute(
                    "UPDATE django_migrations SET app = %s WHERE app = %s",
                    ["honaryaar", "ejranow"],
                )
                migrations = cursor.rowcount
                cursor.execute(
                    "UPDATE django_content_type SET app_label = %s WHERE app_label = %s",
                    ["honaryaar", "ejranow"],
                )
                types = cursor.rowcount
        self.stdout.write(
            f"renamed {renamed} database objects, {migrations} migration rows, {types} content types"
        )

    def _rename_relations(self, cursor, quote, kind, keyword):
        cursor.execute(
            """
            SELECT c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = %s AND c.relname LIKE %s
            ORDER BY c.relname
            """,
            [kind, r"ejranow\_%"],
        )
        names = [row[0] for row in cursor.fetchall()]
        for name in names:
            new = "honaryaar_" + name[len("ejranow_") :]
            cursor.execute(f"ALTER {keyword} {quote(name)} RENAME TO {quote(new)}")
        return len(names)

    def _rename_constraints(self, cursor, quote):
        cursor.execute(
            """
            SELECT c.relname, con.conname
            FROM pg_constraint con
            JOIN pg_class c ON c.oid = con.conrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND con.conname LIKE %s
            ORDER BY con.conname
            """,
            [r"ejranow\_%"],
        )
        rows = cursor.fetchall()
        for table, name in rows:
            new = "honaryaar_" + name[len("ejranow_") :]
            cursor.execute(
                f"ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(name)} TO {quote(new)}"
            )
        return len(rows)
