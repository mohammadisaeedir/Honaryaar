import secrets
from collections import defaultdict
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from honaryaar.accounts import ensure_profile
from honaryaar.catalog import format_jalali_numeric
from honaryaar.forms import ApplyForm, InviteForm, OpportunityForm, ProjectCreateForm
from honaryaar.labels import APPLICATION_LABELS
from honaryaar.media_files import MediaError
from honaryaar.media_service import attach_project_image, parse_upload_id, project_image_url
from honaryaar.models import (
    Application,
    ApplicationStatus,
    City,
    Invite,
    InviteStatus,
    Match,
    MatchStatus,
    Opportunity,
    OpportunityStatus,
    Project,
)


def _profile_or_redirect(request):
    profile = ensure_profile(request.user)
    if profile is None:
        return None, redirect("me-profile")
    return profile, None


def _slug(model, prefix):
    for _ in range(5):
        slug = f"{prefix}-{secrets.token_hex(4)}"
        if not model.objects.filter(slug=slug).exists():
            return slug
    return f"{prefix}-{secrets.token_hex(8)}"


def _manager_name(profile):
    full = f"{profile.user.first_name} {profile.user.last_name}".strip()
    return full or profile.public_name()


def _apply_opportunity(opportunity, cleaned, project):
    opportunity.title = cleaned["title"]
    opportunity.role = cleaned["role"]
    opportunity.city = cleaned["city"] or project.city
    opportunity.deadline = cleaned["deadline"]
    opportunity.description = cleaned["description"]
    opportunity.art_category = project.art_category
    opportunity.collaboration_type = cleaned["collaboration_type"]
    opportunity.experience_level = cleaned["experience_level"]
    opportunity.special_conditions = cleaned["special_conditions"]
    opportunity.age_min = cleaned["age_min"]
    opportunity.age_max = cleaned["age_max"]


def _project_step(slug, invite=""):
    params = {"step": "opportunities"}
    if invite:
        params["invite"] = invite
    return f"{reverse('me-project', args=[slug])}?{urlencode(params)}"


def _ensure_match(profile, opportunity, application=None, invite=None):
    match, created = Match.objects.get_or_create(
        profile=profile,
        opportunity=opportunity,
        defaults={
            "application": application,
            "invite": invite,
            "status": MatchStatus.ACTIVE,
        },
    )
    if created:
        return match
    if application and match.application_id is None:
        match.application = application
    if invite and match.invite_id is None:
        match.invite = invite
    match.status = MatchStatus.ACTIVE
    match.save()
    return match


def _list(request, page_title, items, empty_icon, empty_text, add_url="", add_label="", pin_action=False, bookmarks=None, saved_tab=False):
    return render(
        request,
        "pages/me_list.html",
        {
            "page_title": page_title,
            "items": items,
            "empty_icon": empty_icon,
            "empty_text": empty_text,
            "add_url": add_url,
            "add_label": add_label,
            "pin_action": pin_action,
            "bookmarks": bookmarks or [],
            "saved_tab": saved_tab,
        },
    )


@login_required
def my_projects(request):
    profile, bounce = _profile_or_redirect(request)
    if bounce:
        return bounce
    projects = profile.owned_projects.prefetch_related("opportunities").select_related("city")
    items = []
    for project in projects:
        meta = f"{project.opportunities.count()} فرصت"
        if project.city_id:
            meta = f"{meta} · {project.city}"
        items.append(
            {
                "url": reverse("me-project", args=[project.slug]),
                "title": project.title,
                "meta": meta,
                "tone": project.status,
                "image": project_image_url(project),
            }
        )
    return _list(
        request,
        "پروژه‌ها",
        items,
        "projects",
        "هنوز پروژه‌ای نساخته‌اید.",
        reverse("me-project-new"),
        "افزودن پروژه",
        pin_action=True,
    )


@login_required
def project_new(request):
    profile, bounce = _profile_or_redirect(request)
    if bounce:
        return bounce
    form = ProjectCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        upload_id = parse_upload_id(form.cleaned_data.get("image_upload"))
        try:
            with transaction.atomic():
                project = Project.objects.create(
                    slug=_slug(Project, "p"),
                    title=form.cleaned_data["title"],
                    owner=profile,
                    city=form.cleaned_data["city"],
                    art_category=form.cleaned_data["art_category"],
                    summary=form.cleaned_data["summary"],
                    start_date=form.cleaned_data["start_date"],
                    status=form.cleaned_data["status"],
                )
                attach_project_image(request.user, project, upload_id, required=True)
        except MediaError as exc:
            form.add_error(None, exc.message)
        else:
            messages.success(request, f"پروژه «{project.title}» ساخته شد.")
            return redirect(_project_step(project.slug))
    return render(
        request,
        "pages/me_project_new.html",
        {"form": form, "owner_name": _manager_name(profile)},
    )


@login_required
def project_manage(request, slug):
    profile, bounce = _profile_or_redirect(request)
    if bounce:
        return bounce
    project = get_object_or_404(
        Project.objects.select_related("city", "art_category", "owner", "owner__user"),
        slug=slug,
        owner=profile,
    )
    action = request.POST.get("action") if request.method == "POST" else ""
    project_form = ProjectCreateForm(
        request.POST if action == "project" else None,
        initial={
            "title": project.title,
            "city": project.city_id,
            "art_category": project.art_category_id,
            "summary": project.summary,
            "start_date": project.start_date,
            "status": project.status,
        },
    )
    opportunity_initial = {"city": project.city_id} if project.city_id else None
    opportunity_form = OpportunityForm(
        request.POST if action == "opportunity" else None,
        initial=opportunity_initial,
    )
    invite_form = InviteForm(project, profile, request.POST if action == "invite" else None)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "project" and project_form.is_valid():
            upload_id = parse_upload_id(project_form.cleaned_data.get("image_upload"))
            try:
                with transaction.atomic():
                    project.title = project_form.cleaned_data["title"]
                    project.city = project_form.cleaned_data["city"]
                    project.art_category = project_form.cleaned_data["art_category"]
                    project.summary = project_form.cleaned_data["summary"]
                    project.start_date = project_form.cleaned_data["start_date"]
                    project.status = project_form.cleaned_data["status"]
                    project.save(update_fields=["title", "city", "art_category", "summary", "start_date", "status"])
                    attach_project_image(
                        request.user,
                        project,
                        upload_id,
                        remove=project_form.cleaned_data.get("image_remove"),
                    )
            except MediaError as exc:
                project_form.add_error(None, exc.message)
            else:
                messages.success(request, "پروژه ذخیره شد.")
                return redirect(_project_step(project.slug))
        if action == "opportunity-city":
            opportunity = get_object_or_404(project.opportunities, pk=request.POST.get("opportunity"))
            city_id = request.POST.get("city") or None
            opportunity.city = City.objects.filter(pk=city_id).first() if city_id else None
            opportunity.save(update_fields=["city"])
            messages.success(request, "شهر فرصت ذخیره شد.")
            return redirect(_project_step(project.slug))
        if action == "opportunity-delete":
            opportunity = get_object_or_404(project.opportunities, pk=request.POST.get("opportunity"))
            title = opportunity.title
            opportunity.delete()
            messages.success(request, f"فرصت «{title}» حذف شد.")
            return redirect(_project_step(project.slug))
        if action == "opportunity" and opportunity_form.is_valid():
            cleaned = opportunity_form.cleaned_data
            existing_id = request.POST.get("opportunity")
            if existing_id:
                opportunity = get_object_or_404(project.opportunities, pk=existing_id)
                _apply_opportunity(opportunity, cleaned, project)
                opportunity.save()
                messages.success(request, f"فرصت «{cleaned['title']}» ذخیره شد.")
            else:
                opportunity = Opportunity(
                    slug=_slug(Opportunity, "o"),
                    project=project,
                    status=OpportunityStatus.OPEN,
                )
                _apply_opportunity(opportunity, cleaned, project)
                opportunity.save()
                messages.success(request, f"فرصت «{cleaned['title']}» اضافه شد.")
            return redirect(_project_step(project.slug))
        if action == "invite" and invite_form.is_valid():
            invited = invite_form.cleaned_data["opportunity"]
            _invite, created = Invite.objects.get_or_create(
                profile=invite_form.cleaned_data["profile"],
                opportunity=invited,
                defaults={"message": invite_form.cleaned_data["message"]},
            )
            if not created:
                invite_form.add_error(None, "این دعوت قبلاً فرستاده شده.")
            else:
                messages.success(request, "دعوت فرستاده شد.")
                return redirect(_project_step(project.slug, invite=invited.pk))
    applications = Application.objects.filter(opportunity__project=project).select_related(
        "profile",
        "opportunity",
        "opportunity__role",
    )
    grouped = defaultdict(list)
    for application in applications:
        grouped[application.opportunity_id].append(application)
    opportunities = list(
        project.opportunities.select_related("role", "city").prefetch_related(
            Prefetch(
                "invites",
                queryset=Invite.objects.select_related("profile", "profile__user"),
            )
        )
    )
    for opportunity in opportunities:
        opportunity.application_rows = grouped[opportunity.id]
        opportunity.invite_rows = list(opportunity.invites.all())
        for invite in opportunity.invite_rows:
            invite.guest_name = _manager_name(invite.profile)
    saved_artists = list(invite_form.fields["profile"].queryset)
    for person in saved_artists:
        person.invite_name = _manager_name(person)
    invite_focus = ""
    if invite_form.errors:
        posted = request.POST.get("opportunity") or ""
        if posted.isdigit() and project.opportunities.filter(pk=posted).exists():
            invite_focus = posted
    elif request.GET.get("invite", "").isdigit() and project.opportunities.filter(pk=request.GET["invite"]).exists():
        invite_focus = request.GET["invite"]
    step = "general"
    if request.GET.get("step") == "opportunities" or opportunity_form.errors or invite_form.errors:
        step = "opportunities"
    return render(
        request,
        "pages/me_project.html",
        {
            "project": project,
            "owner_name": _manager_name(project.owner) if project.owner_id else "",
            "project_form": project_form,
            "opportunities": opportunities,
            "opportunity_form": opportunity_form,
            "invite_form": invite_form,
            "saved_artists": saved_artists,
            "step": step,
            "invite_focus": invite_focus,
            "opportunity_editor": [
                {
                    "id": item.pk,
                    "title": item.title,
                    "role": item.role_id,
                    "city": item.city_id or "",
                    "deadline": format_jalali_numeric(item.deadline) if item.deadline else "",
                    "description": item.description,
                    "collaboration_type": item.collaboration_type,
                    "experience_level": item.experience_level,
                    "special_conditions": item.special_conditions or [],
                    "age_min": item.age_min or 16,
                    "age_max": item.age_max or 80,
                }
                for item in opportunities
            ],
        },
    )


@login_required
@require_POST
def application_status(request, pk):
    profile, bounce = _profile_or_redirect(request)
    if bounce:
        return bounce
    application = get_object_or_404(
        Application.objects.select_related("opportunity__project", "profile"),
        pk=pk,
        opportunity__project__owner=profile,
    )
    status = request.POST.get("status", "")
    if status not in ApplicationStatus.values:
        raise Http404
    application.status = status
    application.save(update_fields=["status"])
    if status == ApplicationStatus.MATCHED:
        _ensure_match(application.profile, application.opportunity, application=application)
    else:
        Match.objects.filter(application=application, status=MatchStatus.ACTIVE).update(
            status=MatchStatus.CLOSED
        )
    label = APPLICATION_LABELS.get(status, status)
    messages.success(request, f"وضعیت درخواست به «{label}» تغییر کرد.")
    return redirect(_project_step(application.opportunity.project.slug))


@login_required
@require_POST
def apply(request, slug):
    profile, bounce = _profile_or_redirect(request)
    if bounce:
        return bounce
    opportunity = get_object_or_404(
        Opportunity.objects.select_related("project"),
        slug=slug,
        status=OpportunityStatus.OPEN,
    )
    if opportunity.project.owner_id == profile.pk:
        return redirect("me-project", slug=opportunity.project.slug)
    form = ApplyForm(request.POST)
    message = form.cleaned_data["message"] if form.is_valid() else ""
    _application, created = Application.objects.get_or_create(
        profile=profile,
        opportunity=opportunity,
        defaults={"message": message},
    )
    if created:
        messages.success(request, "درخواست شما ثبت شد.")
    else:
        messages.success(request, "این درخواست را قبلاً فرستاده‌اید.")
    nxt = request.POST.get("next", "")
    if nxt.startswith("/") and not nxt.startswith("//"):
        return redirect(nxt)
    return redirect("opportunity", slug=slug)


def _record(request, title, rows, subtitle="", body="", public_url="", invite=None):
    return render(
        request,
        "pages/me_record.html",
        {
            "title": title,
            "subtitle": subtitle,
            "rows": rows,
            "body": body,
            "public_url": public_url,
            "invite": invite,
        },
    )


@login_required
def my_applications(request):
    profile, bounce = _profile_or_redirect(request)
    if bounce:
        return bounce
    applications = profile.applications.select_related("opportunity", "opportunity__project")
    items = [
        {
            "url": reverse("me-application", args=[item.pk]),
            "title": item.opportunity.title,
            "meta": item.opportunity.project.title,
            "tone": item.status,
            "image": project_image_url(item.opportunity.project),
        }
        for item in applications
    ]
    return _list(
        request,
        "درخواست‌های من",
        items,
        "applications",
        "هنوز درخواستی نفرستاده‌اید.",
        reverse("opportunities"),
        "مشاهده فرصت‌ها",
    )


@login_required
def application_detail(request, pk):
    profile, bounce = _profile_or_redirect(request)
    if bounce:
        return bounce
    application = get_object_or_404(
        Application.objects.select_related("opportunity", "opportunity__project", "opportunity__role"),
        pk=pk,
        profile=profile,
    )
    opportunity = application.opportunity
    return _record(
        request,
        opportunity.title,
        [
            {"label": "پروژه", "value": opportunity.project.title},
            {"label": "نقش", "value": opportunity.role.title},
            {"label": "وضعیت", "status": application.status},
        ],
        subtitle="درخواست شما",
        body=application.message,
        public_url=reverse("opportunity", args=[opportunity.slug]),
    )


@login_required
def my_invites(request):
    profile, bounce = _profile_or_redirect(request)
    if bounce:
        return bounce
    invites = profile.invites.select_related("opportunity", "opportunity__project")
    items = [
        {
            "url": reverse("me-invite", args=[item.pk]),
            "title": item.opportunity.title,
            "meta": item.opportunity.project.title,
            "tone": item.status,
            "image": project_image_url(item.opportunity.project),
        }
        for item in invites
    ]
    return _list(request, "دعوت‌ها", items, "invites", "دعوتی برای شما نیست.")


@login_required
def invite_detail(request, pk):
    profile, bounce = _profile_or_redirect(request)
    if bounce:
        return bounce
    if request.method == "POST":
        invite = get_object_or_404(
            Invite.objects.select_related("opportunity"),
            pk=pk,
            profile=profile,
            status=InviteStatus.SENT,
        )
        decision = request.POST.get("decision")
        if decision == "accept":
            invite.status = InviteStatus.ACCEPTED
            invite.save(update_fields=["status"])
            _ensure_match(profile, invite.opportunity, invite=invite)
            messages.success(request, "دعوت را قبول کردید.")
        elif decision == "decline":
            invite.status = InviteStatus.DECLINED
            invite.save(update_fields=["status"])
            Match.objects.filter(invite=invite, status=MatchStatus.ACTIVE).update(status=MatchStatus.CLOSED)
            messages.success(request, "دعوت را رد کردید.")
        return redirect("me-invite", pk=invite.pk)
    invite = get_object_or_404(
        Invite.objects.select_related("opportunity", "opportunity__project", "opportunity__role"),
        pk=pk,
        profile=profile,
    )
    opportunity = invite.opportunity
    return _record(
        request,
        opportunity.title,
        [
            {"label": "پروژه", "value": opportunity.project.title},
            {"label": "نقش", "value": opportunity.role.title},
            {"label": "وضعیت", "status": invite.status},
        ],
        subtitle="دعوت برای شما",
        body=invite.message,
        public_url=reverse("opportunity", args=[opportunity.slug]),
        invite=invite,
    )


@login_required
def my_collaborations(request):
    profile, bounce = _profile_or_redirect(request)
    if bounce:
        return bounce
    from honaryaar.views import bookmark_rows

    matches = profile.matches.select_related("opportunity", "opportunity__project")
    items = [
        {
            "url": reverse("me-collaboration", args=[item.pk]),
            "title": item.opportunity.title,
            "meta": item.opportunity.project.title,
            "tone": item.status,
            "image": project_image_url(item.opportunity.project),
        }
        for item in matches
    ]
    return _list(
        request,
        "همکاری‌ها",
        items,
        "collaborations",
        "همکاری وقتی ساخته می‌شود که درخواستی به نتیجه برسد یا دعوتی را قبول کنید.",
        bookmarks=bookmark_rows(request.user),
        saved_tab=True,
    )


@login_required
def collaboration_detail(request, pk):
    profile, bounce = _profile_or_redirect(request)
    if bounce:
        return bounce
    match = get_object_or_404(
        Match.objects.select_related("opportunity", "opportunity__project", "opportunity__role"),
        pk=pk,
        profile=profile,
    )
    opportunity = match.opportunity
    return _record(
        request,
        opportunity.title,
        [
            {"label": "پروژه", "value": opportunity.project.title},
            {"label": "نقش", "value": opportunity.role.title},
            {"label": "وضعیت", "status": match.status},
        ],
        subtitle="همکاری",
        public_url=reverse("opportunity", args=[opportunity.slug]),
    )


@login_required
def my_matches(request):
    return redirect("me-collaborations")


