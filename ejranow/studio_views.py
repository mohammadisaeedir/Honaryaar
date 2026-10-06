import secrets
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from ejranow.accounts import ensure_profile
from ejranow.forms import ApplyForm, InviteForm, OpportunityForm, ProjectOpportunityForm
from ejranow.labels import APPLICATION_LABELS, INVITE_LABELS, MATCH_LABELS
from ejranow.models import (
    Application,
    ApplicationStatus,
    ArtCategory,
    Invite,
    InviteStatus,
    Match,
    MatchStatus,
    Opportunity,
    OpportunityStatus,
    Project,
    ProjectStatus,
)


def _profile_or_redirect(request):
    return ensure_profile(request.user), None


def _slug(model, prefix):
    for _ in range(5):
        slug = f"{prefix}-{secrets.token_hex(4)}"
        if not model.objects.filter(slug=slug).exists():
            return slug
    return f"{prefix}-{secrets.token_hex(8)}"


def _theatre():
    return ArtCategory.objects.filter(active=True).first() or ArtCategory.objects.first()


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


def _list(request, page_title, items, empty_icon, empty_text, add_url="", add_label="", pin_action=False):
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
    form = ProjectOpportunityForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        category = _theatre()
        if category is None:
            form.add_error(None, "دسته‌ای برای پروژه ثبت نشده است.")
        else:
            project = Project.objects.create(
                slug=_slug(Project, "p"),
                title=form.cleaned_data["title"],
                owner=profile,
                city=form.cleaned_data["city"],
                category=category,
                lead_name=profile.name,
                summary=form.cleaned_data["summary"],
                status=ProjectStatus.CASTING,
            )
            Opportunity.objects.create(
                slug=_slug(Opportunity, "o"),
                title=form.cleaned_data["opportunity_title"],
                project=project,
                role=form.cleaned_data["role"],
                city=project.city,
                deadline=form.cleaned_data["deadline"],
                description=form.cleaned_data["description"],
                production="نمایش صحنه‌ای",
                status=OpportunityStatus.OPEN,
            )
            return redirect("me-project", slug=project.slug)
    return render(request, "pages/me_project_new.html", {"form": form})


@login_required
def project_manage(request, slug):
    profile, bounce = _profile_or_redirect(request)
    if bounce:
        return bounce
    project = get_object_or_404(
        Project.objects.select_related("city", "category"),
        slug=slug,
        owner=profile,
    )
    action = request.POST.get("action") if request.method == "POST" else ""
    opportunity_form = OpportunityForm(request.POST if action == "opportunity" else None)
    invite_form = InviteForm(project, profile, request.POST if action == "invite" else None)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "opportunity" and opportunity_form.is_valid():
            Opportunity.objects.create(
                slug=_slug(Opportunity, "o"),
                title=opportunity_form.cleaned_data["title"],
                project=project,
                role=opportunity_form.cleaned_data["role"],
                city=project.city,
                deadline=opportunity_form.cleaned_data["deadline"],
                description=opportunity_form.cleaned_data["description"],
                production="نمایش صحنه‌ای",
                status=OpportunityStatus.OPEN,
            )
            return redirect("me-project", slug=project.slug)
        if action == "invite" and invite_form.is_valid():
            _invite, created = Invite.objects.get_or_create(
                profile=invite_form.cleaned_data["profile"],
                opportunity=invite_form.cleaned_data["opportunity"],
                defaults={"message": invite_form.cleaned_data["message"]},
            )
            if not created:
                invite_form.add_error(None, "این دعوت قبلاً فرستاده شده.")
            else:
                return redirect("me-project", slug=project.slug)
    applications = Application.objects.filter(opportunity__project=project).select_related(
        "profile",
        "opportunity",
        "opportunity__role",
    )
    grouped = defaultdict(list)
    for application in applications:
        grouped[application.opportunity_id].append(application)
    opportunities = list(project.opportunities.select_related("role"))
    for opportunity in opportunities:
        opportunity.application_rows = grouped[opportunity.id]
    return render(
        request,
        "pages/me_project.html",
        {
            "project": project,
            "opportunities": opportunities,
            "opportunity_form": opportunity_form,
            "invite_form": invite_form,
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
    return redirect("me-project", slug=application.opportunity.project.slug)


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
    Application.objects.get_or_create(
        profile=profile,
        opportunity=opportunity,
        defaults={"message": message},
    )
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
            "meta": f"{item.opportunity.project.title} · {APPLICATION_LABELS.get(item.status, item.status)}",
            "tone": item.status,
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
            {"label": "وضعیت", "value": APPLICATION_LABELS.get(application.status, application.status)},
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
            "meta": f"{item.opportunity.project.title} · {INVITE_LABELS.get(item.status, item.status)}",
            "tone": item.status,
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
        elif decision == "decline":
            invite.status = InviteStatus.DECLINED
            invite.save(update_fields=["status"])
            Match.objects.filter(invite=invite, status=MatchStatus.ACTIVE).update(status=MatchStatus.CLOSED)
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
            {"label": "وضعیت", "value": INVITE_LABELS.get(invite.status, invite.status)},
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
    matches = profile.matches.select_related("opportunity", "opportunity__project")
    items = [
        {
            "url": reverse("me-collaboration", args=[item.pk]),
            "title": item.opportunity.title,
            "meta": f"{item.opportunity.project.title} · {MATCH_LABELS.get(item.status, item.status)}",
            "tone": item.status,
        }
        for item in matches
    ]
    return _list(
        request,
        "همکاری‌ها",
        items,
        "collaborations",
        "همکاری وقتی ساخته می‌شود که درخواستی به نتیجه برسد یا دعوتی را قبول کنید.",
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
            {"label": "وضعیت", "value": MATCH_LABELS.get(match.status, match.status)},
        ],
        subtitle="همکاری",
        public_url=reverse("opportunity", args=[opportunity.slug]),
    )


@login_required
def my_matches(request):
    return redirect("me-collaborations")


