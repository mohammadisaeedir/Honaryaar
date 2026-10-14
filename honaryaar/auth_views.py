from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from django.db import transaction

from honaryaar.accounts import ensure_profile, user_for_phone
from honaryaar.forms import CodeForm, CreditFormSet, MediaFormSet, PhoneForm, ProfileForm, RoleFormSet
from honaryaar.media_files import NEED_FILE, NEED_LABEL, MediaError
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


PROFILE_SECTIONS = {"hero", "about", "skills", "roles", "credits", "media"}


def _apply_profile_media_action(profile, user, post):
    action = post.get("media_action")
    if action == "delete":
        raw = str(post.get("media_id") or "")
        if raw.isdigit():
            profile.media_items.filter(pk=int(raw)).delete()
        return
    if action == "visibility":
        raw = str(post.get("media_id") or "")
        if not raw.isdigit():
            return
        current = profile.media_items.filter(pk=int(raw)).first()
        if current is None:
            return
        current.is_public = post.get("is_public") == "1"
        current.save(update_fields=["is_public"])
        return
    if action not in {"add", "replace"}:
        return
    upload_id = parse_upload_id(post.get("upload_id"))
    label = (post.get("label") or "").strip()[:160]
    if action == "replace":
        raw = str(post.get("media_id") or "")
        if not raw.isdigit():
            return
        current = profile.media_items.filter(pk=int(raw)).first()
        if current is None:
            return
        if not upload_id:
            if not label:
                raise MediaError(NEED_LABEL)
            current.label = label
            current.save(update_fields=["label"])
            return
        if not label:
            raise MediaError(NEED_LABEL)
        previous = current.position
        _save_media(
            profile,
            [{
                "media_id": current.pk,
                "upload_id": upload_id,
                "label": label,
                "kind": current.kind,
                "is_public": current.is_public,
            }],
            user,
        )
        current.refresh_from_db()
        if current.position != previous:
            current.position = previous
            current.save(update_fields=["position"])
        return
    if not upload_id:
        raise MediaError(NEED_FILE)
    if not label:
        raise MediaError(NEED_LABEL)
    if action == "add":
        if profile.media_items.count() >= settings.MEDIA_PROFILE_MAX_ITEMS:
            raise MediaError(f"حداکثر {settings.MEDIA_PROFILE_MAX_ITEMS} فایل برای پروفایل مجاز است.")
        before = set(profile.media_items.values_list("pk", flat=True))
        _save_media(
            profile,
            [{"upload_id": upload_id, "label": label, "kind": "photo", "is_public": True}],
            user,
        )
        created = profile.media_items.exclude(pk__in=before).first()
        if created is not None:
            created.position = max(profile.media_items.count() - 1, 0)
            created.save(update_fields=["position"])
        return


def _credit_role_labels(formset):
    raw_ids = []
    for form in formset:
        raw = form["role"].value()
        if raw and str(raw).isdigit():
            raw_ids.append(int(raw))
    roles = Role.objects.in_bulk(raw_ids)
    for form in formset:
        raw = form["role"].value()
        role = roles.get(int(raw)) if raw and str(raw).isdigit() else None
        if role is None:
            form.role_label = ""
        elif role.group:
            form.role_label = f"{role.group} | {role.title}"
        else:
            form.role_label = role.title


def _requested_section(value):
    if value == "1":
        return "hero"
    if value in PROFILE_SECTIONS:
        return value
    return ""


@login_required
def me_profile(request):
    profile = ensure_profile(request.user)
    if profile is None:
        return render(
            request,
            "pages/me_profile.html",
            {"profile": None, "editing": False, "edit_section": ""},
        )
    role_links = list(profile.profile_roles.select_related("role"))
    skill_links = list(profile.skill_links.select_related("skill"))
    credits = list(profile.credits.select_related("role"))
    media_items = list(profile.media_items.all())
    posted = request.POST if request.method == "POST" else None
    legacy = posted is not None and "section" not in posted
    posted_section = posted.get("section", "") if posted is not None and not legacy else ""
    if posted is not None and (legacy or posted_section == "skills"):
        skill_levels = _skill_levels_from_post(posted)
    else:
        skill_levels = {link.skill_id: link.level for link in skill_links}
    if posted is not None:
        primary_index = posted.get("role_primary", "")
    else:
        primary_index = next((str(index) for index, link in enumerate(role_links) if link.is_primary), "")
    profile_data = posted if legacy or posted_section in {"hero", "about"} else None
    form = ProfileForm(
        profile_data,
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
        posted if legacy else None,
        initial=[{"role": link.role_id} for link in role_links],
        prefix="role",
    )
    credit_formset = CreditFormSet(
        posted if legacy or posted_section == "credits" else None,
        initial=[
            {"credit_id": item.id, "title": item.title, "role": item.role_id, "role_name": item.role_name, "year": item.year}
            for item in credits
        ],
        prefix="credit",
    )
    _credit_role_labels(credit_formset)
    media_formset = MediaFormSet(
        posted if legacy or posted_section == "media" else None,
        initial=[
            {"media_id": item.id, "kind": item.kind, "label": item.label}
            for item in media_items
        ],
        prefix="media",
    )
    media_by_id = {item.id: item for item in media_items}
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
    edit_section = _requested_section(request.GET.get("edit", ""))
    use_role_picker = posted is not None and posted.get("role_picker") == "1"
    if posted is not None and not legacy and posted_section not in PROFILE_SECTIONS:
        messages.error(request, "این بخش پروفایل شناخته نشد.")
    elif posted is not None and not legacy and posted_section == "hero" and posted.get("hero_action") in {"list", "banner"}:
        action = posted.get("hero_action")
        field = "list_image" if action == "list" else "banner"
        upload_name = "list_upload" if action == "list" else "banner_upload"
        remove_name = "list_remove" if action == "list" else "banner_remove"
        try:
            with transaction.atomic():
                attach_profile_picture(
                    request.user,
                    profile,
                    parse_upload_id(posted.get(upload_name)),
                    field=field,
                    remove=posted.get(remove_name) == "1",
                )
        except MediaError as exc:
            messages.error(request, exc.message)
        else:
            messages.success(request, "تصویر حذف شد." if posted.get(remove_name) == "1" else "تصویر ذخیره شد.")
        return redirect(reverse("me-profile") + "#hero")
    elif posted is not None and not legacy and posted_section == "media" and posted.get("media_action"):
        try:
            with transaction.atomic():
                _apply_profile_media_action(profile, request.user, posted)
        except MediaError as exc:
            messages.error(request, exc.message)
        else:
            messages.success(request, "فایل حذف شد." if posted.get("media_action") == "delete" else "فایل ذخیره شد.")
        return redirect(reverse("me-profile") + "?edit=media")
    elif posted is not None:
        section = "" if legacy else posted_section
        if legacy:
            valid = (
                form.is_valid()
                and (use_role_picker or role_formset.is_valid())
                and credit_formset.is_valid()
                and media_formset.is_valid()
            )
        elif section in {"hero", "about"}:
            valid = form.is_valid()
        elif section == "skills":
            valid = True
        elif section == "roles":
            valid = use_role_picker or role_formset.is_valid()
        elif section == "credits":
            valid = credit_formset.is_valid()
        else:
            valid = media_formset.is_valid()
        if valid:
            error_section = "hero" if section in {"", "hero"} else section
            try:
                with transaction.atomic():
                    if section in {"", "hero"}:
                        profile.name = form.cleaned_data["name"]
                        profile.arts = form.cleaned_data["arts"]
                        request.user.first_name = form.cleaned_data["first_name"]
                        request.user.last_name = form.cleaned_data["last_name"]
                        request.user.save(update_fields=["first_name", "last_name"])
                    if section in {"", "about"}:
                        profile.city = form.cleaned_data["city"]
                        profile.about = form.cleaned_data["about"]
                        profile.birth_date = form.cleaned_data["birth_date"]
                        profile.gender = form.cleaned_data["gender"]
                    if section == "":
                        profile.save()
                    elif section == "hero":
                        profile.save(update_fields=["name", "arts"])
                    elif section == "about":
                        profile.save(update_fields=["city", "about", "birth_date", "gender"])
                    if section in {"", "hero"}:
                        attach_profile_picture(
                            request.user,
                            profile,
                            parse_upload_id(posted.get("list_upload")),
                            field="list_image",
                            remove=posted.get("list_remove") == "1",
                        )
                        attach_profile_picture(
                            request.user,
                            profile,
                            parse_upload_id(posted.get("banner_upload")),
                            field="banner",
                            remove=posted.get("banner_remove") == "1",
                        )
                    if section in {"", "skills"}:
                        _save_skills(profile, skill_levels)
                    if section in {"", "roles"}:
                        if use_role_picker:
                            chosen_roles, primary_role = _roles_from_picker(posted)
                        else:
                            chosen_roles, primary_role = _roles_from_rows(role_formset.cleaned_data, primary_index)
                        _save_roles(profile, chosen_roles, primary_role)
                    if section in {"", "credits"}:
                        _save_credits(profile, credit_formset.cleaned_data)
                    if section in {"", "media"}:
                        error_section = "media"
                        _save_media(profile, media_formset.cleaned_data, request.user)
            except MediaError as exc:
                media_error = exc.message
                messages.error(request, exc.message)
                edit_section = error_section
            else:
                messages.success(request, "پروفایل ذخیره شد.")
                if section in {"hero", "about"}:
                    return redirect("me-profile")
                if section:
                    return redirect(reverse("me-profile") + "?edit=" + section)
                return redirect("me-profile")
        elif legacy:
            if form.errors:
                edit_section = "hero"
            elif not use_role_picker and not role_formset.is_valid():
                edit_section = "roles"
            elif not credit_formset.is_valid():
                edit_section = "credits"
            elif not media_formset.is_valid():
                edit_section = "media"
            else:
                edit_section = "about"
        else:
            edit_section = section
    skill_catalog, skill_chosen = skill_picker_payload(skill_levels)
    if posted is not None and (legacy or posted_section == "roles") and use_role_picker:
        picked_roles, primary_role = _roles_from_picker(request.POST)
        role_state = {role.pk: primary_role is not None and role.pk == primary_role.pk for role in picked_roles}
    else:
        role_state = {link.role_id: link.is_primary for link in role_links}
    role_catalog, role_chosen = role_picker_payload(role_state)
    return render(
        request,
        "pages/me_profile.html",
        {
            "form": form,
            "profile": profile,
            "editing": False,
            "open_info": edit_section == "hero",
            "open_sheet": edit_section if edit_section in {"about", "skills", "roles", "credits", "media"} else "",
            "edit_section": edit_section,
            "role_links": role_links,
            "role_catalog": role_catalog,
            "role_chosen": role_chosen,
            "skill_links": skill_links,
            "skill_catalog": skill_catalog,
            "skill_chosen": skill_chosen,
            "roles": Role.objects.order_by("group", "title"),
            "credits": credits,
            "media_items": media_items,
            "credit_formset": credit_formset,
            "media_formset": media_formset,
            "media_error": media_error,
            "media_max_items": settings.MEDIA_PROFILE_MAX_ITEMS,
            "media_max_photo": settings.MEDIA_MAX_IMAGE_BYTES,
            "media_max_video": settings.MEDIA_MAX_VIDEO_BYTES,
            "media_max_audio": settings.MEDIA_MAX_AUDIO_BYTES,
        },
    )
