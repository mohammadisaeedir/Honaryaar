"""Import crawled casting calls into the local database.

Dry run unless --apply. Refuses every host except localhost. Never updates
an existing project.
"""

import json
import os
import re
from collections import Counter
from datetime import date, datetime, time
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import URLValidator
from django.db import connections, transaction
from django.utils import timezone

from honaryaar.contacts import normalize_contact
from honaryaar.models import (
    City,
    Opportunity,
    OpportunityStatus,
    Project,
    ProjectContact,
    ProjectStatus,
    Role,
)

_SOURCE = re.compile(r"^([a-z]+):([^/]+)/(\d+)$")
_PRODUCTION = {
    "نمایش": "stage-play",
    "تئاتر": "stage-play",
    "فیلم کوتاه": "short-film",
    "فیلم سینمایی": "feature-film",
    "سریال": "series",
    "تبلیغات": "commercial",
    "تولید محتوا": "content",
}
_GENDERS = {"male", "female", "any"}
_CONTACT_KINDS = ("phone", "whatsapp", "telegram", "instagram", "email", "website")


class Command(BaseCommand):
    help = "Import crawled casting calls. Writes nothing unless --apply."

    def add_arguments(self, parser):
        parser.add_argument("--file", default="")
        parser.add_argument("--only-slug", action="append", dest="only_slug")
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--select-pilot", type=int, default=0)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--rollback", default="")

    def handle(self, *args, **options):
        host, name = _refuse_remote()
        self.stdout.write(f"target\t{host}\t{name}")
        if options["rollback"]:
            _rollback(self.stdout, Path(options["rollback"]).expanduser().resolve(), host, name, options["apply"])
            return
        path = Path(options["file"]).expanduser()
        if not options["file"] or not path.is_file():
            raise CommandError("--file is required")
        payload = json.loads(path.read_text(encoding="utf-8"))
        _print_structure(self.stdout, payload)
        if not isinstance(payload, list):
            raise CommandError("casting file must be a list")
        calls, blocked = _prepare(payload)
        _print_file_stats(self.stdout, calls, blocked)
        chosen = _select(calls, options["only_slug"] or [], options["limit"], options["select_pilot"])
        if options["select_pilot"]:
            _print_pilot(self.stdout, chosen)
        _import(self.stdout, path, chosen, options["apply"], host, name)


def _refuse_remote():
    if os.environ.get("VERCEL") == "1":
        raise CommandError("refusing to run when VERCEL=1")
    db = connections["default"].settings_dict
    host = (db.get("HOST") or "").strip()
    if host not in {"localhost", "127.0.0.1"}:
        raise CommandError("database host must be localhost or 127.0.0.1")
    return host, db.get("NAME") or ""


def _print_structure(stdout, payload):
    kind = type(payload).__name__
    size = len(payload) if isinstance(payload, (list, dict)) else 0
    stdout.write(f"detected\t{kind}\tn={size}")
    sample = payload[0] if isinstance(payload, list) and payload else None
    if not isinstance(sample, dict):
        return
    stdout.write("record_keys\t" + ",".join(sample))
    project = sample.get("project")
    if isinstance(project, dict):
        stdout.write("project_keys\t" + ",".join(project))
        contact = project.get("contact")
        if isinstance(contact, dict):
            stdout.write("contact_keys\t" + ",".join(contact))
    opportunities = sample.get("opportunities")
    if isinstance(opportunities, list) and opportunities and isinstance(opportunities[0], dict):
        stdout.write("opportunity_keys\t" + ",".join(opportunities[0]))
    source = sample.get("source") or ""
    stdout.write("source_pattern\t" + ("channel/id" if _SOURCE.match(str(source).strip()) else "other"))


def _prepare(payload):
    cities = {_city_key(city.title): city for city in City.objects.all()}
    roles = {role.slug: role for role in Role.objects.all()}
    calls = []
    blocked = []
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            blocked.append(("not an object", str(index)))
            continue
        parsed, reason, detail = _parse_call(row, cities, roles)
        if parsed is None:
            blocked.append((reason, detail))
            continue
        calls.append(parsed)
    return calls, blocked


def _parse_call(row, cities, roles):
    source = str(row.get("source") or "").strip()
    match = _SOURCE.match(source)
    if match is None:
        return None, "source not channel/id", ""
    channel = f"{match.group(1)}:{match.group(2)}"
    if len(channel) > 60:
        return None, "source channel too long", ""
    project = row.get("project") if isinstance(row.get("project"), dict) else {}
    slug = str(project.get("slug") or "").strip()
    if not slug:
        return None, "missing project slug", ""
    if len(slug) > 50:
        raise CommandError(f"slug longer than 50: {slug}")
    title = str(project.get("title") or "").strip()
    if not title or len(title) > 160:
        return None, "bad project title", slug
    lead_name = str(project.get("lead_name") or "").strip()
    if len(lead_name) > 120:
        return None, "lead_name too long", slug
    opportunities = row.get("opportunities")
    if not isinstance(opportunities, list) or not opportunities:
        return None, "no opportunities", slug
    parsed_opps = []
    categories = []
    for item in opportunities:
        if not isinstance(item, dict):
            return None, "bad opportunity", slug
        opp, reason, detail = _parse_opportunity(item, cities, roles)
        if opp is None:
            return None, reason, detail or slug
        parsed_opps.append(opp)
        categories.append(opp["art_category"])
    category = Counter(categories).most_common(1)[0][0]
    city, city_note = _match_city(project.get("city"), cities)
    contacts, contact_notes = _contacts(project.get("contact"))
    lead_role = str(project.get("lead_role") or "").strip()
    role = None
    if lead_role:
        role = roles.get(lead_role)
        if role is None:
            return None, "missing role", lead_role
    return {
        "slug": slug,
        "title": title,
        "summary": str(project.get("summary") or ""),
        "lead_name": lead_name,
        "lead_role": role,
        "city": city,
        "city_title": city.title if city is not None else "",
        "city_note": city_note,
        "art_category": category,
        "source_channel": channel,
        "source_post_id": int(match.group(3)),
        "source_url": _url(row.get("sourceUrl")),
        "source_url_dropped": bool(str(row.get("sourceUrl") or "").strip()) and not _url(row.get("sourceUrl")),
        "source_posted_at": _posted_at(row.get("postDate")),
        "opportunities": parsed_opps,
        "contacts": contacts,
        "contact_notes": contact_notes,
        "multi": len(parsed_opps) >= 2,
        "social": any(item["kind"] in {"instagram", "whatsapp"} for item in contacts),
        "other_city": city is not None and _city_key(city.title) != "تهران",
        "deadline": _soonest(parsed_opps),
    }, "", ""


def _parse_opportunity(item, cities, roles):
    slug = str(item.get("slug") or "").strip()
    if not slug:
        return None, "missing opportunity slug", ""
    if len(slug) > 50:
        raise CommandError(f"slug longer than 50: {slug}")
    title = str(item.get("title") or "").strip()
    if not title or len(title) > 160:
        return None, "bad opportunity title", slug
    production = str(item.get("production") or "").strip()
    category = _PRODUCTION.get(production)
    if category is None:
        return None, "unmapped category", production or "(empty)"
    role_slug = str(item.get("role") or "").strip()
    role = roles.get(role_slug)
    if role is None:
        return None, "missing role", role_slug or "(empty)"
    gender = str(item.get("gender") or "").strip() or "any"
    if gender not in _GENDERS:
        return None, "bad gender", gender
    deadline, deadline_error = _deadline(item.get("deadline"))
    if deadline_error:
        return None, deadline_error, slug
    if deadline is not None and deadline < timezone.localdate():
        return None, "deadline passed", slug
    city, _note = _match_city(item.get("city"), cities)
    pay_note = str(item.get("pay_note") or "")
    return {
        "slug": slug,
        "title": title,
        "role": role,
        "art_category": category,
        "city": city,
        "age_min": _small(item.get("age_min")),
        "age_max": _small(item.get("age_max")),
        "gender": gender,
        "count": _small(item.get("count")) or 1,
        "paid": bool(item.get("paid")),
        "pay_note": pay_note[:240],
        "pay_note_trimmed": len(pay_note) > 240,
        "deadline": deadline,
        "description": str(item.get("description") or ""),
    }, "", ""


def _deadline(value):
    if value in (None, ""):
        return None, ""
    if not isinstance(value, str):
        return None, "bad deadline"
    try:
        return date.fromisoformat(value.strip()[:10]), ""
    except ValueError:
        return None, "bad deadline"


def _posted_at(value):
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        if len(text) <= 10:
            parsed = datetime.combine(date.fromisoformat(text[:10]), time.min)
        else:
            parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _url(value):
    text = str(value or "").strip()
    if not text or len(text) > 300:
        return ""
    try:
        URLValidator()(text)
    except ValidationError:
        return ""
    return text


def _small(value):
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number < 0 or number > 32767:
        return None
    return number


def _city_key(value):
    return str(value or "").strip().replace("ي", "ی").replace("ك", "ک")


def _match_city(value, cities):
    key = _city_key(value)
    if not key:
        return None, "empty"
    city = cities.get(key)
    if city is None:
        return None, key
    return city, key


def _contacts(raw):
    if not isinstance(raw, dict):
        return [], []
    rows = []
    notes = []
    seen = set()
    position = 0
    for kind in _CONTACT_KINDS:
        value = raw.get(kind)
        if value in (None, ""):
            continue
        try:
            normalized = normalize_contact(kind, str(value))
        except ValidationError as exc:
            notes.append(f"{kind}\t{exc.messages[0]}")
            continue
        if (kind, normalized) in seen:
            continue
        seen.add((kind, normalized))
        rows.append({"kind": kind, "value": normalized, "position": position})
        position += 1
    return rows, notes


def _soonest(opportunities):
    dates = [item["deadline"] for item in opportunities if item["deadline"] is not None]
    if not dates:
        return ""
    return min(dates).isoformat()


def _print_file_stats(stdout, calls, blocked):
    stdout.write(f"eligible\t{len(calls)}")
    stdout.write(f"skipped\t{len(blocked)}")
    counts = Counter(reason for reason, _detail in blocked)
    for reason, count in sorted(counts.items()):
        stdout.write(f"skip_reason\t{reason}\t{count}")
    details = Counter(
        (reason, detail)
        for reason, detail in blocked
        if detail and reason in {"unmapped category", "missing role", "bad gender"}
    )
    for (reason, detail), count in sorted(details.items()):
        stdout.write(f"skip_detail\t{reason}\t{detail}\t{count}")
    city_notes = Counter(call["city_note"] for call in calls if call["city"] is None)
    for note, count in sorted(city_notes.items()):
        stdout.write(f"city_unmatched\t{note}\t{count}")
    invalid = Counter(note for call in calls for note in call["contact_notes"])
    for note, count in sorted(invalid.items()):
        stdout.write(f"contact_invalid\t{note}\t{count}")
    stdout.write(f"source_url_dropped\t{sum(1 for call in calls if call['source_url_dropped'])}")


def _select(calls, only_slug, limit, pilot):
    chosen = list(calls)
    if only_slug:
        wanted = set(only_slug)
        chosen = [call for call in chosen if call["slug"] in wanted]
    if limit:
        chosen = chosen[:limit]
    if pilot:
        chosen = _pilot(chosen, pilot)
    return chosen


def _pilot(calls, count):
    ordered = sorted(calls, key=lambda call: call["slug"])
    chosen = []

    def take(predicate):
        for call in ordered:
            if any(item["slug"] == call["slug"] for item in chosen):
                continue
            if predicate(call):
                chosen.append(call)
                return True
        return False

    take(lambda call: call["art_category"] == "stage-play" and call["multi"])
    take(lambda call: call["art_category"] == "stage-play")
    take(lambda call: call["art_category"] != "stage-play" and call["social"])
    take(lambda call: call["art_category"] != "stage-play")
    while len(chosen) < count:
        picked = {call["slug"] for call in chosen}
        rest = [call for call in ordered if call["slug"] not in picked]
        if not rest:
            break
        need_multi = not any(call["multi"] for call in chosen)
        need_social = not any(call["social"] for call in chosen)
        need_city = not any(call["other_city"] for call in chosen) and any(call["other_city"] for call in ordered)

        def rank(call):
            score = 0
            if need_multi and call["multi"]:
                score += 4
            if need_social and call["social"]:
                score += 2
            if need_city and call["other_city"]:
                score += 1
            return (-score, call["slug"])

        chosen.append(sorted(rest, key=rank)[0])
    chosen = chosen[:count]
    theatre = sum(call["art_category"] == "stage-play" for call in chosen)
    other = sum(call["art_category"] != "stage-play" for call in chosen)
    if theatre < 2 or other < 2:
        raise CommandError("pilot could not find 2 theatre and 2 film calls")
    if not any(call["multi"] for call in chosen):
        raise CommandError("pilot could not find a call with several opportunities")
    if not any(call["social"] for call in chosen):
        raise CommandError("pilot could not find an Instagram or WhatsApp contact")
    if any(call["other_city"] for call in ordered) and not any(call["other_city"] for call in chosen):
        raise CommandError("pilot could not find a city other than Tehran")
    return chosen


def _print_pilot(stdout, calls):
    stdout.write("pilot\tslug\ttitle\tcategory\tcity\topportunities\tcontacts\tdeadline")
    for call in calls:
        kinds = ",".join(item["kind"] for item in call["contacts"]) or "-"
        city = call["city_title"] or "-"
        stdout.write(
            f"pilot_row\t{call['slug']}\t{call['title']}\t{call['art_category']}\t{city}\t"
            f"{len(call['opportunities'])}\t{kinds}\t{call['deadline'] or '-'}"
        )


def _import(stdout, path, calls, apply, host, name):
    from honaryaar.models import ArtCategory

    categories = {row.slug: row for row in ArtCategory.objects.all()}
    created = skipped = 0
    records = []
    for call in calls:
        reason = _existing(call)
        if reason:
            skipped += 1
            stdout.write(f"{call['slug']}\tskip ({reason})")
            continue
        if not apply:
            created += 1
            stdout.write(f"{call['slug']}\twould create\topportunities={len(call['opportunities'])}\tcontacts={len(call['contacts'])}")
            continue
        record = _create(call, categories)
        records.append(record)
        created += 1
        stdout.write(f"{call['slug']}\tcreated\topportunities={len(record['opportunity_ids'])}\tcontacts={len(record['contact_ids'])}")
    if apply:
        manifest = _write_manifest(path, host, name, records)
        stdout.write(f"manifest\t{manifest}")
    label = "created" if apply else "would_create"
    stdout.write(f"totals\t{label}={created}\tskip={skipped}\tapply={int(bool(apply))}")


def _existing(call):
    if Project.objects.filter(slug=call["slug"]).exists():
        return "project slug exists"
    if Project.objects.filter(source_channel=call["source_channel"], source_post_id=call["source_post_id"]).exists():
        return "source post exists"
    slugs = [item["slug"] for item in call["opportunities"]]
    if Opportunity.objects.filter(slug__in=slugs).exists():
        return "opportunity slug exists"
    return ""


def _create(call, categories):
    category = categories.get(call["art_category"])
    if category is None:
        raise CommandError(f"missing art category {call['art_category']}")
    with transaction.atomic():
        project = Project(
            slug=call["slug"],
            title=call["title"],
            summary=call["summary"],
            lead_name=call["lead_name"],
            lead_role=call["lead_role"],
            city=call["city"],
            art_category=category,
            source_channel=call["source_channel"],
            source_post_id=call["source_post_id"],
            source_url=call["source_url"],
            source_posted_at=call["source_posted_at"],
            status=ProjectStatus.CASTING,
        )
        project.full_clean()
        project.save()
        opportunity_ids = []
        for item in call["opportunities"]:
            opportunity = Opportunity(
                slug=item["slug"],
                title=item["title"],
                project=project,
                role=item["role"],
                art_category=categories[item["art_category"]],
                city=item["city"],
                age_min=item["age_min"],
                age_max=item["age_max"],
                gender=item["gender"],
                count=item["count"],
                paid=item["paid"],
                pay_note=item["pay_note"],
                deadline=item["deadline"],
                description=item["description"],
                status=OpportunityStatus.OPEN,
            )
            opportunity.full_clean()
            opportunity.save()
            opportunity_ids.append(opportunity.pk)
        contact_ids = []
        for item in call["contacts"]:
            contact = ProjectContact(
                project=project,
                kind=item["kind"],
                value=item["value"],
                is_public=True,
                position=item["position"],
                source="telegram",
            )
            contact.full_clean()
            contact.save()
            contact_ids.append(contact.pk)
    return {
        "project_id": project.pk,
        "slug": project.slug,
        "opportunity_ids": opportunity_ids,
        "contact_ids": contact_ids,
    }


def _write_manifest(source, host, name, records):
    folder = source.resolve().parent / "runs"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = timezone.now().strftime("%Y%m%dT%H%M%S")
    path = folder / f"calls-{stamp}.json"
    counter = 0
    while path.exists():
        counter += 1
        path = folder / f"calls-{stamp}-{counter}.json"
    payload = {
        "created_at": timezone.now().isoformat(),
        "target_host": host,
        "target_name": name,
        "records": records,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _rollback(stdout, path, host, name, apply):
    if not path.is_file():
        raise CommandError("rollback manifest is missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("target_host") != host or payload.get("target_name") != name:
        raise CommandError("rollback manifest is for a different database")
    records = payload.get("records")
    if not isinstance(records, list):
        raise CommandError("calls manifest has no records list")
    deleted = skipped = 0
    for record in records:
        if not isinstance(record, dict):
            skipped += 1
            stdout.write("skip (bad record)")
            continue
        slug = record.get("slug") or ""
        if not apply:
            deleted += 1
            stdout.write(f"would delete\t{slug}")
            continue
        with transaction.atomic():
            ProjectContact.objects.filter(pk__in=record.get("contact_ids") or []).delete()
            Opportunity.objects.filter(pk__in=record.get("opportunity_ids") or []).delete()
            Project.objects.filter(pk=record.get("project_id")).delete()
        deleted += 1
        stdout.write(f"deleted\t{slug}")
    label = "deleted" if apply else "would_delete"
    stdout.write(f"totals\t{label}={deleted}\tskip={skipped}\tapply={int(bool(apply))}")
