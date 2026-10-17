"""Upsert the role catalog on the local database.

Creates missing roles and refreshes title, group, and art category for roles
that are already in the catalog. Roles that are not in the catalog are left
as they are. Nothing is deleted. Dry run unless --apply.
"""

import os

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, connections, transaction

from honaryaar.catalog import role_catalog
from honaryaar.models import ArtCategory, Role


class Command(BaseCommand):
    help = "Upsert role_catalog() into the local database. Never deletes roles."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        host, name = _refuse_remote()
        self.stdout.write(f"target\t{host}\t{name}")
        catalog = role_catalog()
        fallback = (
            ArtCategory.objects.filter(slug="stage-play").first()
            or ArtCategory.objects.order_by("priority", "id").first()
        )
        if fallback is None:
            raise CommandError("no art category to attach roles to")
        existing = {role.slug: role for role in Role.objects.select_related("art_category")}
        plan, leftovers, conflicts = _plan(catalog, existing, fallback)
        for slug in leftovers:
            role = existing[slug]
            self.stdout.write(f"untouched\t{slug}\t{role.group or '-'}\t{role.title}")
        for row in conflicts:
            self.stdout.write(
                f"conflict\t{row['slug']}\t{row['group']}\t{row['title']}\tblocked by {row['blocked_by']}"
            )
        created = updated = unchanged = 0
        for row in plan:
            if row["action"] == "unchanged":
                unchanged += 1
                continue
            if not options["apply"]:
                if row["action"] == "create":
                    created += 1
                else:
                    updated += 1
                continue
            try:
                with transaction.atomic():
                    _write(row, existing, fallback)
            except IntegrityError:
                conflicts.append(row)
                self.stdout.write(
                    f"conflict\t{row['slug']}\t{row['group']}\t{row['title']}\tunique_role_group_title"
                )
                continue
            if row["action"] == "create":
                created += 1
            else:
                updated += 1
        self.stdout.write(f"catalog\t{len(catalog)}")
        self.stdout.write(f"created\t{created}")
        self.stdout.write(f"updated\t{updated}")
        self.stdout.write(f"unchanged\t{unchanged}")
        self.stdout.write(f"conflicts\t{len(conflicts)}")
        self.stdout.write(f"untouched\t{len(leftovers)}")
        self.stdout.write(f"totals\tapply={int(bool(options['apply']))}")


def _refuse_remote():
    if os.environ.get("VERCEL") == "1":
        raise CommandError("refusing to run when VERCEL=1")
    db = connections["default"].settings_dict
    host = (db.get("HOST") or "").strip()
    if host not in {"localhost", "127.0.0.1"}:
        raise CommandError("database host must be localhost or 127.0.0.1")
    return host, db.get("NAME") or ""


def _plan(catalog, existing, fallback):
    catalog_slugs = {item["slug"] for item in catalog}
    leftovers = sorted(slug for slug in existing if slug not in catalog_slugs)
    owners = {}
    for slug in leftovers:
        role = existing[slug]
        owners.setdefault((role.group, role.title), slug)
    conflicts = []
    plan = []
    for item in catalog:
        key = (item["group"], item["title"])
        owner = owners.get(key)
        if owner is not None and owner != item["slug"]:
            conflicts.append(
                {
                    "slug": item["slug"],
                    "group": item["group"],
                    "title": item["title"],
                    "blocked_by": owner,
                }
            )
            continue
        if len(item["title"]) > 80 or len(item["group"]) > 80:
            conflicts.append(
                {
                    "slug": item["slug"],
                    "group": item["group"],
                    "title": item["title"],
                    "blocked_by": "field length",
                }
            )
            continue
        owners[key] = item["slug"]
        role = existing.get(item["slug"])
        if role is None:
            plan.append({**item, "action": "create"})
            continue
        same = (
            role.title == item["title"]
            and role.group == item["group"]
            and role.art_category_id == fallback.id
        )
        plan.append({**item, "action": "unchanged" if same else "update"})
    return plan, leftovers, conflicts


def _write(row, existing, fallback):
    role = existing.get(row["slug"])
    if role is None:
        role = Role(
            slug=row["slug"],
            title=row["title"],
            group=row["group"],
            art_category=fallback,
        )
        role.full_clean()
        role.save()
        existing[role.slug] = role
        return
    role.title = row["title"]
    role.group = row["group"]
    role.art_category = fallback
    role.full_clean()
    role.save()
