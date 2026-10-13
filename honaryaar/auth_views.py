from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from django.db import transaction

from honaryaar.accounts import ensure_profile, user_for_phone
from honaryaar.forms import CodeForm, CreditFormSet, MediaFormSet, PhoneForm, ProfileForm, RoleFormSet
from honaryaar.media_files import MediaError
from honaryaar.media_service import attach_profile_picture, parse_upload_id, save_profile_media, url_for_key
from honaryaar.models import Credit, ProfileMedia, ProfileRole, ProfileSkill, Role, Skill, SkillArea


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
        messages.success(request, "وارد شدید.")
        return redirect(nxt or "home")
    return render(request, "pages/login_code.html", {"form": form, "phone": phone})


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "از حساب خارج شدید.")
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


def _save_media(profile, rows, user):
    prepared = []
    for row in rows:
        if not row:
            prepared.append(row)
            continue
        item = dict(row)
        item["upload_id"] = parse_upload_id(row.get("upload_id"))
        prepared.append(item)
    save_profile_media(profile, prepared, user)


def _skill_levels_from_post(post):
    levels = {}
    for key, value in post.items():
        if not key.startswith("skill-"):
            continue
        raw_id = key.removeprefix("skill-")
        if raw_id.isdigit() and value in {"1", "2", "3", "4", "5"}:
            levels[int(raw_id)] = int(value)
    return levels


def skill_picker_payload(levels):
    labels = dict(SkillArea.choices)
    catalog = [
        {"id": skill.pk, "title": skill.title, "category": labels.get(skill.group, skill.group)}
        for skill in Skill.objects.all()
    ]
    by_id = {item["id"]: item for item in catalog}
    chosen = []
    for skill_id, level in levels.items():
        item = by_id.get(skill_id)
        if item and level:
            chosen.append({**item, "level": int(level)})
    return catalog, chosen


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


def _roles_from_picker(post):
    ids = []
    for key, value in post.items():
        if not key.startswith("role-"):
            continue
        raw_id = key.removeprefix("role-")
        if raw_id.isdigit() and value == "1":
            ids.append(int(raw_id))
    found = {role.pk: role for role in Role.objects.filter(pk__in=ids)}
    chosen = [found[pk] for pk in ids if pk in found]
    primary = None
    raw_primary = str(post.get("role_primary") or "")
    if raw_primary.isdigit():
        primary = found.get(int(raw_primary))
    if primary not in chosen and chosen:
        primary = chosen[0]
    return chosen, primary


def role_picker_payload(chosen):
    catalog = [
        {"id": role.pk, "title": role.title, "category": role.group}
        for role in Role.objects.all()
    ]
    by_id = {item["id"]: item for item in catalog}
    selected = []
    for role_id, is_primary in chosen.items():
        item = by_id.get(role_id)
        if item:
            selected.append({**item, "primary": bool(is_primary)})
    if selected and not any(item["primary"] for item in selected):
        selected[0]["primary"] = True
    return catalog, selected


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
    if profile is None:
        return render(
            request,
            "pages/me_profile.html",
            {"profile": None, "editing": False},
        )
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
            "first_name": profile.user.first_name,
            "last_name": profile.user.last_name,
            "name": profile.name,
            "city": profile.city_id,
            "about": profile.about,
            "birth_date": profile.birth_date,
            "gender": profile.gender,
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
    media_by_id = {item.id: item for item in profile.media_items.all()}
    for media_form in media_formset:
        raw = media_form["media_id"].value()
        current = media_by_id.get(int(raw)) if raw and str(raw).isdigit() else None
        media_form.preview_url = ""
        media_form.preview_kind = current.kind if current else "photo"
        if current and current.file:
            media_form.preview_url = url_for_key(
                current.thumbnail.name or current.file.name,
                public=current.is_public,
                public_acl=current.public_acl,
                kind=current.kind,
            )
    media_error = ""
    save_error_tab = ""
    use_role_picker = request.method == "POST" and request.POST.get("role_picker") == "1"
    if request.method == "POST":
        editing = True
        if (
            form.is_valid()
            and (use_role_picker or role_formset.is_valid())
            and credit_formset.is_valid()
            and media_formset.is_valid()
        ):
            save_error_tab = "identity"
            try:
                with transaction.atomic():
                    profile.name = form.cleaned_data["name"]
                    profile.city = form.cleaned_data["city"]
                    profile.about = form.cleaned_data["about"]
                    profile.birth_date = form.cleaned_data["birth_date"]
                    profile.gender = form.cleaned_data["gender"]
                    profile.arts = form.cleaned_data["arts"]
                    profile.save()
                    attach_profile_picture(
                        request.user,
                        profile,
                        parse_upload_id(request.POST.get("list_upload")),
                        field="list_image",
                        remove=request.POST.get("list_remove") == "1",
                    )
                    attach_profile_picture(
                        request.user,
                        profile,
                        parse_upload_id(request.POST.get("banner_upload")),
                        field="banner",
                        remove=request.POST.get("banner_remove") == "1",
                    )
                    _save_skills(profile, skill_levels)
                    if use_role_picker:
                        chosen_roles, primary_role = _roles_from_picker(request.POST)
                    else:
                        chosen_roles, primary_role = _roles_from_rows(role_formset.cleaned_data, primary_index)
                    _save_roles(profile, chosen_roles, primary_role)
                    _save_credits(profile, credit_formset.cleaned_data)
                    save_error_tab = "media"
                    _save_media(profile, media_formset.cleaned_data, request.user)
                    request.user.first_name = form.cleaned_data["first_name"]
                    request.user.last_name = form.cleaned_data["last_name"]
                    request.user.save(update_fields=["first_name", "last_name"])
            except MediaError as exc:
                media_error = exc.message
                messages.error(request, exc.message)
            else:
                messages.success(request, "پروفایل ذخیره شد.")
                return redirect("me-profile")
    edit_tab = "identity"
    if media_error:
        edit_tab = save_error_tab or "media"
    elif request.method == "POST" and form.errors:
        edit_tab = "identity"
    elif request.method == "POST" and not use_role_picker and not role_formset.is_valid():
        edit_tab = "roles"
    elif request.method == "POST" and not credit_formset.is_valid():
        edit_tab = "credits"
    elif request.method == "POST" and not media_formset.is_valid():
        edit_tab = "media"
    skill_catalog, skill_chosen = skill_picker_payload(skill_levels) if editing else ([], [])
    if editing and use_role_picker:
        picked_roles, primary_role = _roles_from_picker(request.POST)
        role_state = {role.pk: primary_role is not None and role.pk == primary_role.pk for role in picked_roles}
    elif editing:
        role_state = {link.role_id: link.is_primary for link in role_links}
    else:
        role_state = {}
    role_catalog, role_chosen = role_picker_payload(role_state) if editing else ([], [])
    return render(
        request,
        "pages/me_profile.html",
        {
            "form": form,
            "profile": profile,
            "editing": editing,
            "role_links": role_links,
            "role_catalog": role_catalog,
            "role_chosen": role_chosen,
            "skill_links": skill_links,
            "skill_catalog": skill_catalog,
            "skill_chosen": skill_chosen,
            "roles": Role.objects.all(),
            "credit_formset": credit_formset,
            "media_formset": media_formset,
            "edit_tab": edit_tab,
            "media_error": media_error,
            "media_max_items": settings.MEDIA_PROFILE_MAX_ITEMS,
            "media_max_photo": settings.MEDIA_MAX_IMAGE_BYTES,
            "media_max_video": settings.MEDIA_MAX_VIDEO_BYTES,
            "media_max_audio": settings.MEDIA_MAX_AUDIO_BYTES,
        },
    )
