"""Import crawled profiles onto the local database.

Dry-run unless --apply. Photos are ignored. Contact strings are never stored.
"""

import json
import os
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_slug
from django.db import transaction
from django.utils import timezone

from ejranow.accounts import normalize_phone
from ejranow.models import Art, City, Credit, Profile, ProfileRole, ProfileStatus, Role

_ARABIC_LETTERS = str.maketrans({"ي": "ی", "ك": "ک"})
_ARTS = {value for value, _label in Art.choices}


class Command(BaseCommand):
    help = "Import crawled profiles, credits, and mapped roles. Writes nothing unless --apply."

    def add_arguments(self, parser):
        parser.add_argument("--data-dir", required=True, help="Absolute path to data/import-ready/")
        parser.add_argument(
            "--only-file",
            default="",
            help="JSON file in the data dir: a list of slugs, a list of objects with slug, or an object whose selected list is one of those.",
        )
        parser.add_argument("--apply", action="store_true", help="Write rows. Without this, the run only prints a plan.")
        parser.add_argument("--rollback", default="", help="Manifest from a previous run. Deletes only those ids.")
        parser.add_argument("--verify", default="", help="Manifest from a previous run. Read-only page and login checks.")

    def handle(self, *args, **options):
        _refuse_remote_database()
        data_dir = Path(options["data_dir"]).expanduser()
        if not data_dir.is_dir():
            raise CommandError(f"data dir not found: {data_dir}")
        modes = [name for name in ("rollback", "verify") if options[name]]
        if len(modes) > 1 or (modes and options["only_file"]):
            raise CommandError("use only one of import, --rollback, or --verify")
        if options["rollback"]:
            self._rollback(data_dir, options["rollback"], options["apply"])
            return
        if options["verify"]:
            self._verify(data_dir, options["verify"])
            return
        self._import(data_dir, options["only_file"], options["apply"])

    def _import(self, data_dir, only_file, apply):
        profiles_path = data_dir / "profiles.json"
        credits_path = data_dir / "credits.json"
        contacts_path = data_dir / "contacts-sidecar.json"
        role_map_path = data_dir / "role-map-candidates.json"
        for path in (profiles_path, credits_path, contacts_path, role_map_path):
            if not path.is_file():
                raise CommandError(f"missing {path.name}")
        profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
        credits = json.loads(credits_path.read_text(encoding="utf-8"))
        contacts = json.loads(contacts_path.read_text(encoding="utf-8"))
        role_rows = json.loads(role_map_path.read_text(encoding="utf-8"))
        self.stdout.write(_describe_inputs(profiles, credits, contacts, role_rows))
        by_slug = {}
        for item in profiles:
            if isinstance(item, dict) and item.get("slug"):
                by_slug[item["slug"]] = item
        credits_by_slug = {}
        for item in credits:
            if isinstance(item, dict) and item.get("profile_slug"):
                credits_by_slug.setdefault(item["profile_slug"], []).append(item)
        role_map = {}
        for item in role_rows:
            if not isinstance(item, dict):
                continue
            proposed = item.get("catalog_slug")
            if isinstance(proposed, str) and proposed.strip():
                role_map[item.get("role") or ""] = proposed.strip()
        if only_file:
            only_path = _resolve_in_dir(data_dir, only_file)
            payload = json.loads(only_path.read_text(encoding="utf-8"))
            wanted, detected = _slugs_from_only(payload)
            self.stdout.write(detected)
        else:
            wanted = list(by_slug)
            self.stdout.write(f"only-file: not set, using all {len(wanted)} profile slugs")
        known_roles = {row.slug: row for row in Role.objects.all()}
        cities = {}
        for city in City.objects.all():
            cities.setdefault(_norm_text(city.title), city)
        totals = Counter()
        unmatched_titles = Counter()
        invalid_arts = Counter()
        missing_roles = Counter()
        manifest_records = []
        seen = set()
        for slug in wanted:
            if slug in seen:
                continue
            seen.add(slug)
            record = by_slug.get(slug)
            if record is None:
                totals["missing"] += 1
                self.stdout.write(f"missing\t{slug}\tno row in profiles.json")
                continue
            credit_rows = credits_by_slug.get(slug, [])
            plan = _plan_profile(record, credit_rows, role_map, known_roles, cities, _ARTS)
            unmatched_titles.update(plan["unmatched_cities"])
            invalid_arts.update(plan["invalid_arts"])
            missing_roles.update(plan["missing_roles"])
            existing = Profile.objects.filter(slug=slug).only("id").first()
            username = f"idx-{slug}"
            if existing is not None:
                totals["skip"] += 1
                totals["skip_credits"] += len(plan["credits"])
                totals["skip_roles"] += len(plan["roles"])
                self.stdout.write(f"skip (exists)\t{slug}\t{_profile_bits(slug, plan)}")
                continue
            taken = User.objects.filter(username=username).first()
            if taken is not None and not Profile.objects.filter(user=taken).exists():
                totals["conflict"] += 1
                self.stdout.write(
                    f"conflict\t{username}\tuser exists without a profile\t{_profile_bits(slug, plan)}"
                )
                continue
            if taken is not None:
                totals["conflict"] += 1
                linked = Profile.objects.filter(user=taken).values_list("slug", flat=True).first()
                self.stdout.write(
                    f"conflict\t{username}\talready linked to {linked}\t{_profile_bits(slug, plan)}"
                )
                continue
            if plan["error"]:
                totals["rejected"] += 1
                self.stdout.write(f"rejected\t{slug}\t{plan['error']}")
                continue
            totals["create"] += 1
            totals["credits"] += len(plan["credits"])
            totals["roles"] += len(plan["roles"])
            totals["credits_skipped"] += plan["credits_skipped"]
            line = (
                f"would create\t{slug}\t{_profile_bits(slug, plan)}\t"
                f"city={plan['city_title'] or '-'}\tskipped_credits={plan['credits_skipped']}"
            )
            if not apply:
                self.stdout.write(line)
                continue
            with transaction.atomic():
                user = User(username=username, is_staff=False, is_superuser=False)
                user.set_unusable_password()
                user.save()
                profile = Profile.objects.create(
                    user=user,
                    slug=slug,
                    name=plan["name"],
                    about=plan["about"],
                    status=ProfileStatus.INDEXED,
                    arts=plan["arts"],
                    city=plan["city"],
                )
                role_rows_created = []
                for catalog_slug in plan["roles"]:
                    role_rows_created.append(
                        ProfileRole(
                            profile=profile,
                            role=known_roles[catalog_slug],
                            is_primary=catalog_slug == plan["primary"],
                        )
                    )
                if role_rows_created:
                    role_rows_created = ProfileRole.objects.bulk_create(role_rows_created)
                credit_objects = [
                    Credit(
                        profile=profile,
                        title=item["title"],
                        role=known_roles.get(item["role_slug"]) if item["role_slug"] else None,
                        role_name=item["role_name"],
                        year=item["year"],
                    )
                    for item in plan["credits"]
                ]
                if credit_objects:
                    credit_objects = Credit.objects.bulk_create(credit_objects)
            manifest_records.append(
                {
                    "slug": slug,
                    "username": username,
                    "user_id": user.id,
                    "profile_id": profile.id,
                    "credit_ids": [item.id for item in credit_objects],
                    "profile_role_ids": [item.id for item in role_rows_created],
                }
            )
            self.stdout.write(line.replace("would create", "created", 1))
        self.stdout.write(
            "totals\t"
            f"would_create={totals['create']}\t"
            f"skip={totals['skip']}\t"
            f"conflict={totals['conflict']}\t"
            f"missing={totals['missing']}\t"
            f"rejected={totals['rejected']}\t"
            f"credits={totals['credits']}\t"
            f"roles={totals['roles']}\t"
            f"skipped_credits={totals['credits_skipped']}\t"
            f"unmatched_cities={sum(unmatched_titles.values())}"
        )
        if unmatched_titles:
            shown = ", ".join(f"{title}={count}" for title, count in unmatched_titles.most_common())
            self.stdout.write(f"unmatched city titles\t{shown}")
        if invalid_arts:
            shown = ", ".join(f"{title}={count}" for title, count in invalid_arts.most_common())
            self.stdout.write(f"ignored arts\t{shown}")
        if missing_roles:
            shown = ", ".join(f"{title}={count}" for title, count in missing_roles.most_common())
            self.stdout.write(f"role slugs missing in database\t{shown}")
        if plan_contacts_ignored(contacts):
            self.stdout.write("contacts-sidecar.json was read and not written")
        if not apply:
            self.stdout.write("dry run, nothing written")
            return
        stamp = timezone.now().strftime("%Y%m%dT%H%M%S")
        destination = data_dir / "runs" / f"import-{stamp}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "created_at": timezone.now().isoformat(),
            "records": manifest_records,
        }
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.stdout.write(f"manifest\t{destination}")

    def _rollback(self, data_dir, manifest_arg, apply):
        manifest = _load_manifest(data_dir, manifest_arg)
        records = manifest.get("records") or []
        self.stdout.write(f"rollback manifest\t{len(records)} records")
        for item in records:
            slug = item.get("slug") or ""
            profile = Profile.objects.filter(pk=item.get("profile_id")).first()
            user = User.objects.filter(pk=item.get("user_id")).first()
            delete_profile = profile is not None and profile.status == ProfileStatus.INDEXED
            if profile is not None and not delete_profile:
                self.stdout.write(f"skip profile\t{slug}\tstatus is {profile.status}")
            if delete_profile:
                if apply:
                    with transaction.atomic():
                        profile.delete()
                    self.stdout.write(f"deleted profile\t{slug}\tstatus={ProfileStatus.INDEXED}")
                else:
                    self.stdout.write(f"would delete profile\t{slug}\tstatus={profile.status}")
            if user is None:
                self.stdout.write(f"skip user\t{slug}\tabsent")
                continue
            if not user.username.startswith("idx-"):
                self.stdout.write(f"skip user\t{slug}\tusername {user.username}")
                continue
            still_linked = Profile.objects.filter(user=user).exists()
            if still_linked and not (delete_profile and not apply):
                self.stdout.write(f"skip user\t{slug}\tprofile still linked")
                continue
            if apply:
                with transaction.atomic():
                    user.delete()
                self.stdout.write(f"deleted user\t{slug}\t{user.username}")
            else:
                self.stdout.write(f"would delete user\t{slug}\t{user.username}")
        if not apply:
            self.stdout.write("dry run, nothing written")

    def _verify(self, data_dir, manifest_arg):
        from django.test import Client

        manifest = _load_manifest(data_dir, manifest_arg)
        contacts = json.loads((data_dir / "contacts-sidecar.json").read_text(encoding="utf-8"))
        client = Client(SERVER_NAME="localhost")
        list_response = client.get("/artists/")
        list_ok = list_response.status_code == 200
        self.stdout.write(f"{'pass' if list_ok else 'fail'}\t/artists/\t{list_response.status_code}")
        passed = 1 if list_ok else 0
        failed = 0 if list_ok else 1
        for item in manifest.get("records") or []:
            slug = item.get("slug") or ""
            detail = client.get(f"/artists/{slug}/")
            detail_ok = detail.status_code == 200
            self.stdout.write(f"{'pass' if detail_ok else 'fail'}\t/artists/{slug}/\t{detail.status_code}")
            if detail_ok:
                passed += 1
            else:
                failed += 1
            html = detail.content.decode("utf-8", errors="replace")
            secret_hit = _contact_hit(html, contacts.get(slug))
            secret_ok = secret_hit == ""
            self.stdout.write(f"{'pass' if secret_ok else 'fail'}\t{slug} contacts hidden\t{secret_hit or 'none'}")
            if secret_ok:
                passed += 1
            else:
                failed += 1
            phone_ok = normalize_phone(f"idx-{slug}") == ""
            self.stdout.write(f"{'pass' if phone_ok else 'fail'}\tnormalize_phone(idx-{slug})")
            if phone_ok:
                passed += 1
            else:
                failed += 1
        self.stdout.write(f"verify\tpass={passed}\tfail={failed}")


def _refuse_remote_database():
    if os.environ.get("VERCEL") == "1":
        raise CommandError("refusing to run when VERCEL=1")
    host = (settings.DATABASES["default"].get("HOST") or "").strip()
    if host not in {"localhost", "127.0.0.1"}:
        raise CommandError(f"refusing database host {host or '(empty)'}")


def _describe_inputs(profiles, credits, contacts, role_rows):
    profile_keys = list(profiles[0]) if isinstance(profiles, list) and profiles and isinstance(profiles[0], dict) else []
    credit_keys = list(credits[0]) if isinstance(credits, list) and credits and isinstance(credits[0], dict) else []
    contact_keys = []
    if isinstance(contacts, dict) and contacts:
        sample = next(iter(contacts.values()))
        if isinstance(sample, dict):
            contact_keys = list(sample)
    mapped = 0
    if isinstance(role_rows, list):
        mapped = sum(1 for item in role_rows if isinstance(item, dict) and item.get("catalog_slug"))
    return (
        f"detected profiles.json list={isinstance(profiles, list)} n={len(profiles) if isinstance(profiles, list) else 0} keys={profile_keys}\n"
        f"detected credits.json list={isinstance(credits, list)} n={len(credits) if isinstance(credits, list) else 0} keys={credit_keys}\n"
        f"detected contacts-sidecar.json object={isinstance(contacts, dict)} n={len(contacts) if isinstance(contacts, dict) else 0} value_keys={contact_keys}\n"
        f"detected role-map-candidates.json list={isinstance(role_rows, list)} n={len(role_rows) if isinstance(role_rows, list) else 0} with_catalog_slug={mapped}"
    )


def _slugs_from_only(payload):
    if isinstance(payload, list):
        slugs = _slug_list(payload)
        kind = "strings" if payload and all(isinstance(item, str) for item in payload) else "objects with slug"
        return slugs, f"detected only-file list of {len(slugs)} {kind}"
    if isinstance(payload, dict):
        for key in ("selected", "slugs", "profiles"):
            rows = payload.get(key)
            if isinstance(rows, list):
                slugs = _slug_list(rows)
                kind = "strings" if rows and all(isinstance(item, str) for item in rows) else "objects with slug"
                ignored = [name for name, value in payload.items() if name != key and isinstance(value, list)]
                extra = f"; ignored lists {ignored}" if ignored else ""
                return slugs, f"detected only-file object key {key}: {len(slugs)} {kind}{extra}"
    raise CommandError("only-file must be a list of slugs, a list of objects with slug, or an object containing one of those lists")


def _slug_list(rows):
    slugs = []
    for item in rows:
        if isinstance(item, str) and item.strip():
            slugs.append(item.strip())
        elif isinstance(item, dict) and isinstance(item.get("slug"), str) and item["slug"].strip():
            slugs.append(item["slug"].strip())
        else:
            raise CommandError("only-file rows must be slugs or objects with slug")
    return slugs


def _resolve_in_dir(data_dir, raw):
    path = Path(raw).expanduser()
    if path.is_file():
        return path
    nested = data_dir / raw
    if nested.is_file():
        return nested
    raise CommandError(f"only-file not found: {raw}")


def _load_manifest(data_dir, raw):
    path = _resolve_in_dir(data_dir, raw)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        raise CommandError("manifest must be an object with a records list")
    return payload


def _norm_text(value):
    return " ".join((value or "").translate(_ARABIC_LETTERS).split())


def _plan_profile(record, credit_rows, role_map, known_roles, cities, valid_arts):
    slug = record.get("slug") or ""
    error = ""
    try:
        validate_slug(slug)
    except ValidationError:
        error = "slug is not a Django slug"
    if len(slug) > 50:
        error = "slug longer than 50"
    name = (record.get("name") or "").strip()
    if len(name) > 120:
        error = "name longer than 120"
    about = record.get("about") or ""
    if not isinstance(about, str):
        about = ""
    arts = []
    invalid = []
    raw_arts = record.get("arts") or []
    if isinstance(raw_arts, list):
        for value in raw_arts:
            if value in valid_arts and value not in arts:
                arts.append(value)
            elif value not in valid_arts:
                invalid.append(str(value))
    city = None
    unmatched = []
    raw_city = record.get("city_title")
    city_title = _norm_text(raw_city) if isinstance(raw_city, str) else ""
    if city_title:
        city = cities.get(city_title)
        if city is None:
            unmatched.append(city_title)
    counts = Counter()
    first_seen = {}
    missing = []
    cursor = 0

    def consider(text):
        nonlocal cursor
        cursor += 1
        proposed = role_map.get(text or "")
        if not proposed:
            return
        if proposed not in known_roles:
            missing.append(proposed)
            return
        first_seen.setdefault(proposed, cursor)
        counts[proposed] += 1

    for title in record.get("role_titles") or []:
        if isinstance(title, str):
            consider(title)
    prepared = []
    skipped = 0
    for row in credit_rows:
        title = row.get("title") if isinstance(row.get("title"), str) else ""
        role_name = row.get("role_name") if isinstance(row.get("role_name"), str) else ""
        role_raw = row.get("role_raw") if isinstance(row.get("role_raw"), str) else ""
        year = row.get("year") if isinstance(row.get("year"), str) else ""
        title = title.strip()
        role_name = role_name.strip()
        year = year.strip()
        if not title or len(title) > 160 or len(role_name) > 120 or len(year) > 20:
            skipped += 1
            continue
        proposed = role_map.get(role_name) or role_map.get(role_raw)
        if proposed and proposed not in known_roles:
            missing.append(proposed)
            proposed = ""
        elif proposed not in known_roles:
            proposed = ""
        consider_text = role_name if role_map.get(role_name) else role_raw
        if role_map.get(consider_text) in known_roles:
            consider(consider_text)
        prepared.append(
            {
                "title": title,
                "role_name": role_name,
                "year": year,
                "role_slug": proposed if proposed in known_roles else "",
            }
        )
    frequent = ""
    if counts:
        frequent = min(counts, key=lambda item: (-counts[item], first_seen[item]))
    ordered = sorted(counts, key=lambda item: first_seen[item])
    raw_primary = record.get("primary_role_slug")
    stated = raw_primary.strip() if isinstance(raw_primary, str) else ""
    if stated and stated in known_roles:
        primary = stated
        primary_rule = "primary_role_slug"
        if stated not in ordered:
            ordered.append(stated)
    else:
        if stated:
            missing.append(stated)
        primary = frequent
        primary_rule = "most_frequent"
    return {
        "error": error,
        "name": name,
        "about": about,
        "arts": arts,
        "city": city,
        "city_title": city.title if city is not None else "",
        "unmatched_cities": unmatched,
        "invalid_arts": invalid,
        "missing_roles": missing,
        "credits": prepared,
        "credits_skipped": skipped,
        "roles": ordered,
        "primary": primary,
        "primary_rule": primary_rule,
    }


def _profile_bits(slug, plan):
    return (
        f"credits={len(plan['credits'])}\t"
        f"roles={len(plan['roles'])}\t"
        f"primary={plan['primary'] or '-'}\t"
        f"rule={plan['primary_rule']}\t"
        f"path=/artists/{slug}/"
    )


def plan_contacts_ignored(contacts):
    return isinstance(contacts, dict)


def _contact_hit(html, sidecar):
    if not isinstance(sidecar, dict):
        return ""
    strings = []
    for item in sidecar.get("phones") or []:
        if isinstance(item, dict):
            strings.extend([item.get("raw") or "", item.get("normalized") or ""])
        elif isinstance(item, str):
            strings.append(item)
    for item in sidecar.get("email") or []:
        if isinstance(item, str):
            strings.append(item)
    for item in sidecar.get("instagram") or []:
        if isinstance(item, dict):
            strings.extend([item.get("handle") or "", item.get("url") or "", item.get("raw") or ""])
        elif isinstance(item, str):
            strings.append(item)
    for value in strings:
        text = value.strip()
        if len(text) >= 3 and text in html:
            if "@" in text:
                return "email"
            if "instagram" in text.lower() or text.startswith("@"):
                return "instagram"
            return "phone"
    return ""
