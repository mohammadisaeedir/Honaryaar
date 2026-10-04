import secrets
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ejranow.accounts import ready_profile
from ejranow.forms import ApplyForm, InviteForm, OpportunityForm, ProjectOpportunityForm
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
    profile = ready_profile(request.user)
    if profile is None:
        return None, redirect("/me/profile/?edit=1")
    return profile, None


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


@login_required
def my_projects(request):
    profile, bounce = _profile_or_redirect(request)
    if bounce:
        return bounce
    projects = profile.owned_projects.prefetch_related("opportunities")
    return render(request, "pages/me_projects.html", {"projects": projects})


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


@login_required
def my_matches(request):
    profile, bounce = _profile_or_redirect(request)
    if bounce:
        return bounce
    applications = profile.applications.select_related("opportunity", "opportunity__project")
    invites = profile.invites.select_related("opportunity", "opportunity__project")
    matches = profile.matches.select_related("opportunity", "opportunity__project")
    return render(
        request,
        "pages/me_matches.html",
        {"applications": applications, "invites": invites, "matches": matches},
    )


@login_required
@require_POST
def invite_reply(request, pk):
    profile, bounce = _profile_or_redirect(request)
    if bounce:
        return bounce
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
    return redirect("me-matches")
