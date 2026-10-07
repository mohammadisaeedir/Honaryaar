from collections import defaultdict

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ejranow.accounts import ensure_profile, user_for_phone
from ejranow.forms import CodeForm, CreditFormSet, MediaFormSet, PhoneForm, ProfileForm, RoleFormSet
from ejranow.models import Credit, ProfileMedia, ProfileRole, ProfileSkill, Role, Skill, SkillArea


def _safe_next(value):
    if not value or not value.startswith("/") or value.startswith("//") or value.startswith("/admin"):
        return ""
    return value


def login_phone(request):
    nxt = _safe_next(request.POST.get("next") or request.GET.get("next"))
    if request.user.is_authenticated:
        return redirect(nxt or "home")
    form = PhoneForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        request.session["login_phone"] = form.cleaned_data["phone"]
        request.session["login_next"] = nxt
        return redirect("login-code")
    return render(request, "pages/login.html", {"form": form, "next": nxt})


def login_code(request):
    nxt = request.session.get("login_next") or ""
    if request.user.is_authenticated:
        return redirect(nxt or "home")
    phone = request.session.get("login_phone")
    if not phone:
        return redirect("login")
    form = CodeForm(phone, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = user_for_phone(phone)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session.pop("login_phone", None)
        request.session.pop("login_next", None)
        return redirect(nxt or "home")
    return render(request, "pages/login_code.html", {"form": form, "phone": phone})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("home")


def _save_credits(profile, rows):
    owned = {item.id: item for item in profile.credits.all()}
    for row in rows:
        if not row:
            continue
        credit_id = row.get("credit_id")
        current = owned.get(credit_id)
        if credit_id and current is None:
            continue
        if row.get("delete"):
            if current:
                current.delete()
            continue
        if not row.get("title"):
            continue
        if current:
            current.title = row["title"]
            current.role = row.get("role")
            current.role_name = row["role_name"]
            current.year = row["year"]
            current.save()
        else:
            Credit.objects.create(
                profile=profile,
                title=row["title"],
                role=row.get("role"),
                role_name=row["role_name"],
                year=row["year"],
            )


def _save_media(profile, rows):
    owned = {item.id: item for item in profile.media_items.all()}
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
        if not row.get("label"):
            continue
        if current:
            current.kind = row["kind"]
            current.label = row["label"]
            current.save()
        else:
            ProfileMedia.objects.create(profile=profile, kind=row["kind"], label=row["label"])


def _skill_levels_from_post(post):
    levels = {}
    for key, value in post.items():
        if not key.startswith("skill-"):
            continue
        raw_id = key.removeprefix("skill-")
        if raw_id.isdigit() and value in {"1", "2", "3"}:
            levels[int(raw_id)] = int(value)
    return levels


def _skill_groups(levels):
    grouped = defaultdict(list)
    for skill in Skill.objects.all():
        grouped[skill.group].append(skill)
    groups = []
    for value, label in SkillArea.choices:
        rows = []
        selected = 0
        for skill in grouped.get(value, []):
            level = levels.get(skill.pk, 0)
            rows.append({"skill": skill, "level": level})
            if level:
                selected += 1
        if rows:
            groups.append({"group": {"title": label}, "rows": rows, "selected": selected})
    return groups


def _save_skills(profile, levels):
    valid = set(Skill.objects.filter(pk__in=levels).values_list("pk", flat=True))
    chosen = {pk: levels[pk] for pk in valid}
    current = ProfileSkill.objects.filter(profile=profile)
    if not chosen:
        current.delete()
        return
    current.exclude(skill_id__in=chosen).delete()
    for skill_id, level in chosen.items():
        ProfileSkill.objects.update_or_create(
            profile=profile,
            skill_id=skill_id,
            defaults={"level": level},
        )


def _roles_from_rows(rows, primary_index):
    chosen = []
    seen = set()
    for row in rows:
        if not row or row.get("delete") or not row.get("role"):
            continue
        role = row["role"]
        if role.pk in seen:
            continue
        seen.add(role.pk)
        chosen.append(role)
    primary = None
    if str(primary_index).isdigit():
        index = int(primary_index)
        if 0 <= index < len(rows):
            row = rows[index] or {}
            if row.get("role") and not row.get("delete"):
                primary = row["role"]
    if primary not in chosen and chosen:
        primary = chosen[0]
    return chosen, primary


def _save_roles(profile, roles, primary):
    chosen = list(roles)
    current = ProfileRole.objects.filter(profile=profile)
    if chosen:
        current.exclude(role__in=chosen).delete()
    else:
        current.delete()
        return
    for role in chosen:
        link, _created = ProfileRole.objects.get_or_create(profile=profile, role=role)
        should_primary = primary is not None and link.role_id == primary.id
        if link.is_primary != should_primary:
            link.is_primary = should_primary
            link.save(update_fields=["is_primary"])


@login_required
def me_profile(request):
    profile = ensure_profile(request.user)
    editing = request.GET.get("edit") == "1"
    role_links = list(profile.profile_roles.select_related("role"))
    skill_links = list(profile.skill_links.select_related("skill"))
    if request.method == "POST":
        skill_levels = _skill_levels_from_post(request.POST)
        primary_index = request.POST.get("role_primary", "")
    else:
        skill_levels = {link.skill_id: link.level for link in skill_links}
        primary_index = next((str(index) for index, link in enumerate(role_links) if link.is_primary), "")
    form = ProfileForm(
        request.POST or None,
        initial={
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "city": profile.city_id,
            "about": profile.about,
            "arts": profile.arts or [],
        },
    )
    role_formset = RoleFormSet(
        request.POST or None,
        initial=[{"role": link.role_id} for link in role_links],
        prefix="role",
    )
    credit_formset = CreditFormSet(
        request.POST or None,
        initial=[
            {"credit_id": item.id, "title": item.title, "role": item.role_id, "role_name": item.role_name, "year": item.year}
            for item in profile.credits.all()
        ],
        prefix="credit",
    )
    media_formset = MediaFormSet(
        request.POST or None,
        initial=[
            {"media_id": item.id, "kind": item.kind, "label": item.label}
            for item in profile.media_items.all()
        ],
        prefix="media",
    )
    if request.method == "POST":
        editing = True
        if (
            form.is_valid()
            and role_formset.is_valid()
            and credit_formset.is_valid()
            and media_formset.is_valid()
        ):
            profile.first_name = form.cleaned_data["first_name"]
            profile.last_name = form.cleaned_data["last_name"]
            profile.name = f"{profile.first_name} {profile.last_name}".strip()
            profile.city = form.cleaned_data["city"]
            profile.about = form.cleaned_data["about"]
            profile.arts = form.cleaned_data["arts"]
            profile.save()
            _save_skills(profile, skill_levels)
            chosen_roles, primary_role = _roles_from_rows(role_formset.cleaned_data, primary_index)
            _save_roles(profile, chosen_roles, primary_role)
            _save_credits(profile, credit_formset.cleaned_data)
            _save_media(profile, media_formset.cleaned_data)
            request.user.first_name = profile.first_name
            request.user.last_name = profile.last_name
            request.user.save(update_fields=["first_name", "last_name"])
            return redirect("me-profile")
    return render(
        request,
        "pages/me_profile.html",
        {
            "form": form,
            "profile": profile,
            "editing": editing,
            "role_links": role_links,
            "role_formset": role_formset,
            "primary_index": primary_index,
            "skill_links": skill_links,
            "skill_groups": _skill_groups(skill_levels),
            "roles": Role.objects.all(),
            "credit_formset": credit_formset,
            "media_formset": media_formset,
        },
    )
