"""Project lifecycle board — overview kanban + per-project task manager."""

import json
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Max, Prefetch
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from honaryaar.accounts import ensure_profile, normalize_phone
from honaryaar.forms import BoardProjectForm
from honaryaar.models import (
    LIFECYCLE_PROJECT_STATUS_VALUES,
    LIFECYCLE_PROJECT_STATUSES,
    Event,
    EventInvitee,
    Profile,
    Project,
    ProjectMember,
    ProjectStatus,
    Role,
    Task,
    TaskAssignee,
    TaskAttachment,
    TaskComment,
)
from honaryaar.slugs import unique_slug


def get_board_membership(request, project_slug):
    """Return (project, membership) or raise PermissionDenied / Http404."""
    profile = ensure_profile(request.user)
    if profile is None:
        raise PermissionDenied
    project = get_object_or_404(Project, slug=project_slug)
    membership = (
        ProjectMember.objects.filter(
            project=project,
            profile=profile,
            invite_status=ProjectMember.InviteStatus.ACCEPTED,
        )
        .select_related("role", "profile")
        .first()
    )
    if membership is None:
        raise PermissionDenied
    return project, membership


def _json_error(message, status=400):
    return JsonResponse({"error": message}, status=status)


def _board_json(view):
    @login_required
    @wraps(view)
    def wrapper(request, slug, *args, **kwargs):
        try:
            project, membership = get_board_membership(request, slug)
        except Http404:
            return _json_error("پروژه پیدا نشد.", 404)
        except PermissionDenied:
            return _json_error("دسترسی ندارید.", 403)
        try:
            return view(request, project, membership, *args, **kwargs)
        except Http404:
            return _json_error("پیدا نشد.", 404)
        except PermissionDenied:
            return _json_error("دسترسی ندارید.", 403)

    return wrapper


def _is_manager(membership):
    return membership.permission in {
        ProjectMember.Permission.OWNER,
        ProjectMember.Permission.ADMIN,
    }


def _payload(request):
    try:
        data = json.loads(request.body.decode() or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _profile_name(profile):
    if profile is None:
        return ""
    full = f"{profile.user.first_name} {profile.user.last_name}".strip()
    return full or profile.public_name()


def _task_payload(task):
    assignees = list(task.assignees.select_related("profile", "profile__user"))
    return {
        "id": task.pk,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "sort_order": task.sort_order,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "created_by": task.created_by_id,
        "assignees": [
            {"profile_id": row.profile_id, "name": _profile_name(row.profile)}
            for row in assignees
        ],
    }


def _event_payload(event):
    invitees = list(event.invitees.select_related("profile", "profile__user"))
    return {
        "id": event.pk,
        "title": event.title,
        "starts_at": event.starts_at.isoformat() if event.starts_at else None,
        "ends_at": event.ends_at.isoformat() if event.ends_at else None,
        "location": event.location,
        "audience_type": event.audience_type,
        "created_by": event.created_by_id,
        "invitees": [
            {
                "profile_id": row.profile_id,
                "name": _profile_name(row.profile),
                "attendance": row.attendance,
            }
            for row in invitees
        ],
    }


def _member_payload(row):
    return {
        "id": row.pk,
        "name": _profile_name(row.profile),
        "profile_id": row.profile_id,
        "role": row.role.title if row.role_id else None,
        "role_id": row.role_id,
        "permission": row.permission,
        "invite_status": row.invite_status,
    }


def _comment_payload(comment):
    return {
        "id": comment.pk,
        "author_name": _profile_name(comment.author),
        "author_id": comment.author_id,
        "body": comment.body,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


def _project_card(project, membership):
    tasks = list(project.tasks.all())
    open_count = sum(
        1 for task in tasks if task.status in {Task.Status.TODO, Task.Status.IN_PROGRESS}
    )
    blocked_count = sum(1 for task in tasks if task.status == Task.Status.BLOCKED)
    member_count = len(list(project.members.all()))
    return {
        "id": project.pk,
        "slug": project.slug,
        "title": project.title,
        "status": project.status,
        "art_category": project.art_category.title if project.art_category_id else "",
        "city": project.city.title if project.city_id else "",
        "open_tasks": open_count,
        "blocked_tasks": blocked_count,
        "member_count": member_count,
        "permission": membership.permission,
        "can_drag": membership.permission
        in {ProjectMember.Permission.OWNER, ProjectMember.Permission.ADMIN},
        "board_url": reverse("board_view", args=[project.slug]),
    }


def _next_sort_order(project):
    current = Task.objects.filter(project=project).aggregate(m=Max("sort_order"))["m"]
    return 0 if current is None else current + 1


def _task_for_project(project, pk):
    return get_object_or_404(Task, pk=pk, project=project)


def _is_assignee(task, profile):
    return TaskAssignee.objects.filter(task=task, profile=profile).exists()


def _owner_count(project):
    return ProjectMember.objects.filter(
        project=project,
        permission=ProjectMember.Permission.OWNER,
        invite_status=ProjectMember.InviteStatus.ACCEPTED,
    ).count()


def _parse_due_date(raw):
    if raw in (None, ""):
        return None
    if hasattr(raw, "year"):
        return raw
    value = parse_date(str(raw).strip())
    if value is None:
        raise ValueError("due_date")
    return value


def _parse_dt(raw, field):
    if raw in (None, ""):
        return None
    value = parse_datetime(str(raw).strip())
    if value is None:
        raise ValueError(field)
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value


# --- Create project + overview + detail ------------------------------------------


@login_required
@require_http_methods(["GET", "POST"])
def board_project_new(request):
    profile = ensure_profile(request.user)
    if profile is None:
        return redirect("me-profile")
    form = BoardProjectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cleaned = form.cleaned_data
        with transaction.atomic():
            project = Project.objects.create(
                slug=unique_slug(Project, cleaned["title"], fallback="project"),
                title=cleaned["title"],
                owner=profile,
                city=cleaned["city"],
                art_category=cleaned["art_category"],
                summary=cleaned["description"],
                personnage_count=cleaned["personnage_count"],
                status=ProjectStatus.CREATE,
            )
            ProjectMember.objects.create(
                project=project,
                profile=profile,
                permission=ProjectMember.Permission.OWNER,
                invite_status=ProjectMember.InviteStatus.ACCEPTED,
            )
        messages.success(request, f"پروژه «{project.title}» ساخته شد.")
        return redirect("board_view", slug=project.slug)
    return render(
        request,
        "pages/board_new.html",
        {"form": form, "owner_name": _profile_name(profile)},
    )


@login_required
@require_GET
def board_overview(request):
    profile = ensure_profile(request.user)
    if profile is None:
        return redirect("me-profile")
    memberships = (
        ProjectMember.objects.filter(
            profile=profile,
            invite_status=ProjectMember.InviteStatus.ACCEPTED,
            project__status__in=LIFECYCLE_PROJECT_STATUS_VALUES,
        )
        .select_related("project", "project__art_category", "project__city")
        .prefetch_related(
            Prefetch(
                "project__tasks",
                queryset=Task.objects.only("id", "status", "project_id"),
            ),
            Prefetch(
                "project__members",
                queryset=ProjectMember.objects.filter(
                    invite_status=ProjectMember.InviteStatus.ACCEPTED
                ).only("id", "project_id", "invite_status"),
            ),
        )
        .order_by("project__title")
    )
    columns = []
    by_status = {value: [] for value, _label in LIFECYCLE_PROJECT_STATUSES}
    for membership in memberships:
        project = membership.project
        by_status.setdefault(project.status, []).append(_project_card(project, membership))
    for value, label in LIFECYCLE_PROJECT_STATUSES:
        columns.append({"value": value, "label": label, "projects": by_status.get(value, [])})
    return render(
        request,
        "pages/board_overview.html",
        {
            "columns": columns,
            "overview_bootstrap": {
                "columns": columns,
                "statuses": [{"value": v, "label": l} for v, l in LIFECYCLE_PROJECT_STATUSES],
                "new_url": reverse("board_project_new"),
            },
        },
    )


@_board_json
@require_http_methods(["PATCH"])
def board_status_update(request, project, membership):
    if not _is_manager(membership):
        return _json_error("دسترسی ندارید.", 403)
    data = _payload(request)
    if data is None:
        return _json_error("درخواست نامعتبر است.")
    status = data.get("status") or ""
    if status not in LIFECYCLE_PROJECT_STATUS_VALUES:
        return _json_error("وضعیت نامعتبر است.")
    project.status = status
    project.save(update_fields=["status"])
    return JsonResponse({"ok": True, "status": project.status, "slug": project.slug})


@login_required
@require_GET
def board_view(request, slug):
    project, membership = get_board_membership(request, slug)
    tasks = list(
        Task.objects.filter(project=project)
        .select_related("created_by")
        .prefetch_related(
            Prefetch(
                "assignees",
                queryset=TaskAssignee.objects.select_related("profile", "profile__user"),
            )
        )
        .order_by("sort_order", "-created_at")
    )
    events = list(
        Event.objects.filter(project=project)
        .prefetch_related(
            Prefetch(
                "invitees",
                queryset=EventInvitee.objects.select_related("profile", "profile__user"),
            )
        )
        .order_by("starts_at")
    )
    all_members = list(
        ProjectMember.objects.filter(project=project)
        .exclude(invite_status=ProjectMember.InviteStatus.REMOVED)
        .select_related("profile", "profile__user", "role")
        .order_by("created_at")
    )
    accepted_members = [
        row for row in all_members if row.invite_status == ProjectMember.InviteStatus.ACCEPTED
    ]
    roles = list(Role.objects.order_by("group", "title"))
    is_lifecycle = project.status in LIFECYCLE_PROJECT_STATUS_VALUES
    board_bootstrap = {
        "slug": project.slug,
        "permission": membership.permission,
        "viewer_profile_id": membership.profile_id,
        "is_lifecycle": is_lifecycle,
        "lifecycle_statuses": [
            {"value": value, "label": label} for value, label in LIFECYCLE_PROJECT_STATUSES
        ],
        "project": {
            "title": project.title,
            "status": project.status,
            "status_label": project.get_status_display(),
            "city": project.city.title if project.city_id else "",
            "art_category": project.art_category.title if project.art_category_id else "",
            "personnage_count": project.personnage_count,
            "summary": project.summary,
        },
        "task_statuses": [{"value": v, "label": l} for v, l in Task.Status.choices],
        "tasks": [_task_payload(task) for task in tasks],
        "events": [_event_payload(event) for event in events],
        "members": [_member_payload(row) for row in all_members],
        "roles": [{"id": role.pk, "title": role.title, "group": role.group} for role in roles],
        "urls": {
            "tasks": reverse("board_tasks", args=[project.slug]),
            "tasks_reorder": reverse("board_tasks_reorder", args=[project.slug]),
            "events": reverse("board_events", args=[project.slug]),
            "members": reverse("board_members", args=[project.slug]),
            "members_invite": reverse("board_member_invite", args=[project.slug]),
            "status": reverse("board_status_update", args=[project.slug]),
            "overview": reverse("board_overview"),
        },
    }
    return render(
        request,
        "pages/board.html",
        {
            "project": project,
            "membership": membership,
            "members": accepted_members,
            "viewer_permission": membership.permission,
            "board_bootstrap": board_bootstrap,
            "is_lifecycle": is_lifecycle,
        },
    )


# --- Tasks -----------------------------------------------------------------------


@_board_json
@require_POST
def board_tasks(request, project, membership):
    if not _is_manager(membership):
        return _json_error("دسترسی ندارید.", 403)
    data = _payload(request)
    if data is None:
        return _json_error("درخواست نامعتبر است.")
    title = (data.get("title") or "").strip()
    if not title:
        return _json_error("عنوان تسک لازم است.")
    status = data.get("status") or Task.Status.TODO
    if status not in Task.Status.values:
        return _json_error("وضعیت نامعتبر است.")
    try:
        due_date = _parse_due_date(data.get("due_date"))
    except ValueError:
        return _json_error("ددلاین نامعتبر است.")
    assignee_ids = data.get("assignee_ids") or []
    if not isinstance(assignee_ids, list):
        return _json_error("assignee_ids نامعتبر است.")
    with transaction.atomic():
        task = Task.objects.create(
            project=project,
            title=title[:255],
            description=(data.get("description") or "").strip(),
            status=status,
            sort_order=_next_sort_order(project),
            due_date=due_date,
            created_by=membership.profile,
        )
        profiles = Profile.objects.filter(
            pk__in=[int(pk) for pk in assignee_ids if str(pk).isdigit()],
            project_memberships__project=project,
            project_memberships__invite_status=ProjectMember.InviteStatus.ACCEPTED,
        ).distinct()
        TaskAssignee.objects.bulk_create(
            [TaskAssignee(task=task, profile=profile) for profile in profiles]
        )
    return JsonResponse(_task_payload(task), status=201)


@_board_json
@require_http_methods(["PATCH", "DELETE"])
def board_task_detail(request, project, membership, pk):
    task = _task_for_project(project, pk)
    if request.method == "DELETE":
        if not _is_manager(membership):
            return _json_error("دسترسی ندارید.", 403)
        task.delete()
        return JsonResponse({"ok": True})

    data = _payload(request)
    if data is None:
        return _json_error("درخواست نامعتبر است.")
    manager = _is_manager(membership)
    assignee = _is_assignee(task, membership.profile)
    if not manager and not assignee:
        return _json_error("دسترسی ندارید.", 403)
    if not manager:
        allowed = {"status"}
        if set(data.keys()) - allowed:
            return _json_error("فقط وضعیت قابل تغییر است.", 403)
        if "status" in data and data["status"] not in Task.Status.values:
            return _json_error("وضعیت نامعتبر است.")
        if "status" in data:
            task.status = data["status"]
            task.save(update_fields=["status", "updated_at"])
        return JsonResponse(_task_payload(task))

    fields = []
    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return _json_error("عنوان تسک لازم است.")
        task.title = title[:255]
        fields.append("title")
    if "description" in data:
        task.description = (data.get("description") or "").strip()
        fields.append("description")
    if "status" in data:
        if data["status"] not in Task.Status.values:
            return _json_error("وضعیت نامعتبر است.")
        task.status = data["status"]
        fields.append("status")
    if "due_date" in data:
        try:
            task.due_date = _parse_due_date(data.get("due_date"))
        except ValueError:
            return _json_error("ددلاین نامعتبر است.")
        fields.append("due_date")
    if "sort_order" in data:
        try:
            task.sort_order = int(data["sort_order"])
        except (TypeError, ValueError):
            return _json_error("ترتیب نامعتبر است.")
        fields.append("sort_order")
    if fields:
        fields.append("updated_at")
        task.save(update_fields=fields)
    return JsonResponse(_task_payload(task))


@_board_json
@require_POST
def board_tasks_reorder(request, project, membership):
    if not _is_manager(membership):
        return _json_error("دسترسی ندارید.", 403)
    data = _payload(request)
    if data is None:
        return _json_error("درخواست نامعتبر است.")
    rows = data.get("tasks")
    if not isinstance(rows, list):
        return _json_error("لیست تسک نامعتبر است.")
    with transaction.atomic():
        for row in rows:
            if not isinstance(row, dict):
                return _json_error("آیتم نامعتبر است.")
            try:
                task_id = int(row["id"])
                sort_order = int(row["sort_order"])
            except (KeyError, TypeError, ValueError):
                return _json_error("آیتم نامعتبر است.")
            updated = Task.objects.filter(pk=task_id, project=project).update(sort_order=sort_order)
            if not updated:
                return _json_error("تسک پیدا نشد.", 404)
    return JsonResponse({"ok": True})


@_board_json
@require_POST
def board_task_assignees(request, project, membership, pk):
    if not _is_manager(membership):
        return _json_error("دسترسی ندارید.", 403)
    task = _task_for_project(project, pk)
    data = _payload(request)
    if data is None:
        return _json_error("درخواست نامعتبر است.")
    try:
        profile_id = int(data.get("profile_id"))
    except (TypeError, ValueError):
        return _json_error("profile_id نامعتبر است.")
    profile = Profile.objects.filter(
        pk=profile_id,
        project_memberships__project=project,
        project_memberships__invite_status=ProjectMember.InviteStatus.ACCEPTED,
    ).first()
    if profile is None:
        return _json_error("عضو پروژه پیدا نشد.", 404)
    _row, created = TaskAssignee.objects.get_or_create(task=task, profile=profile)
    return JsonResponse({"ok": True, "created": created}, status=201 if created else 200)


@_board_json
@require_http_methods(["DELETE"])
def board_task_assignee_remove(request, project, membership, pk, profile_id):
    if not _is_manager(membership):
        return _json_error("دسترسی ندارید.", 403)
    task = _task_for_project(project, pk)
    deleted, _ = TaskAssignee.objects.filter(task=task, profile_id=profile_id).delete()
    if not deleted:
        return _json_error("مسئول پیدا نشد.", 404)
    return JsonResponse({"ok": True})


@_board_json
@require_http_methods(["GET", "POST"])
def board_task_comments(request, project, membership, pk):
    task = _task_for_project(project, pk)
    if request.method == "GET":
        comments = (
            TaskComment.objects.filter(task=task)
            .select_related("author", "author__user")
            .order_by("created_at")
        )
        return JsonResponse([_comment_payload(row) for row in comments], safe=False)
    data = _payload(request)
    if data is None:
        return _json_error("درخواست نامعتبر است.")
    body = (data.get("body") or "").strip()
    if not body:
        return _json_error("متن نظر لازم است.")
    comment = TaskComment.objects.create(task=task, author=membership.profile, body=body)
    return JsonResponse(_comment_payload(comment), status=201)


@_board_json
@require_POST
def board_task_attachments(request, project, membership, pk):
    if not _is_manager(membership):
        return _json_error("دسترسی ندارید.", 403)
    task = _task_for_project(project, pk)
    uploaded = request.FILES.get("file")
    if uploaded is None:
        return _json_error("فایل لازم است.")
    label = (request.POST.get("label") or uploaded.name or "").strip()[:255]
    attachment = TaskAttachment(task=task, uploaded_by=membership.profile, label=label)
    attachment.file.save(uploaded.name, uploaded, save=True)
    try:
        file_url = attachment.file.url
    except ValueError:
        file_url = ""
    return JsonResponse({"id": attachment.pk, "file_url": file_url, "label": attachment.label}, status=201)


@_board_json
@require_http_methods(["DELETE"])
def board_task_attachment_delete(request, project, membership, pk, att_id):
    if not _is_manager(membership):
        return _json_error("دسترسی ندارید.", 403)
    task = _task_for_project(project, pk)
    attachment = get_object_or_404(TaskAttachment, pk=att_id, task=task)
    if attachment.file:
        attachment.file.delete(save=False)
    attachment.delete()
    return JsonResponse({"ok": True})


# --- Events ----------------------------------------------------------------------


@_board_json
@require_POST
def board_events(request, project, membership):
    if not _is_manager(membership):
        return _json_error("دسترسی ندارید.", 403)
    data = _payload(request)
    if data is None:
        return _json_error("درخواست نامعتبر است.")
    title = (data.get("title") or "").strip()
    if not title:
        return _json_error("عنوان رویداد لازم است.")
    audience = data.get("audience_type") or Event.AudienceType.ALL_TEAM
    if audience not in Event.AudienceType.values:
        return _json_error("نوع مخاطب نامعتبر است.")
    try:
        starts_at = _parse_dt(data.get("starts_at"), "starts_at")
    except ValueError:
        return _json_error("زمان شروع نامعتبر است.")
    if starts_at is None:
        return _json_error("زمان شروع لازم است.")
    try:
        ends_at = _parse_dt(data.get("ends_at"), "ends_at")
    except ValueError:
        return _json_error("زمان پایان نامعتبر است.")
    invitee_ids = data.get("invitee_ids") or []
    if not isinstance(invitee_ids, list):
        return _json_error("invitee_ids نامعتبر است.")
    with transaction.atomic():
        event = Event.objects.create(
            project=project,
            title=title[:255],
            starts_at=starts_at,
            ends_at=ends_at,
            location=(data.get("location") or "").strip()[:255],
            audience_type=audience,
            created_by=membership.profile,
        )
        if audience == Event.AudienceType.ALL_TEAM:
            profiles = Profile.objects.filter(
                project_memberships__project=project,
                project_memberships__invite_status=ProjectMember.InviteStatus.ACCEPTED,
            ).distinct()
        else:
            profiles = Profile.objects.filter(
                pk__in=[int(pk) for pk in invitee_ids if str(pk).isdigit()],
                project_memberships__project=project,
                project_memberships__invite_status=ProjectMember.InviteStatus.ACCEPTED,
            ).distinct()
        EventInvitee.objects.bulk_create(
            [EventInvitee(event=event, profile=profile) for profile in profiles]
        )
    return JsonResponse(_event_payload(event), status=201)


@_board_json
@require_http_methods(["PATCH", "DELETE"])
def board_event_detail(request, project, membership, pk):
    if not _is_manager(membership):
        return _json_error("دسترسی ندارید.", 403)
    event = get_object_or_404(Event, pk=pk, project=project)
    if request.method == "DELETE":
        event.delete()
        return JsonResponse({"ok": True})
    data = _payload(request)
    if data is None:
        return _json_error("درخواست نامعتبر است.")
    fields = []
    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return _json_error("عنوان رویداد لازم است.")
        event.title = title[:255]
        fields.append("title")
    if "starts_at" in data:
        try:
            starts_at = _parse_dt(data.get("starts_at"), "starts_at")
        except ValueError:
            return _json_error("زمان شروع نامعتبر است.")
        if starts_at is None:
            return _json_error("زمان شروع لازم است.")
        event.starts_at = starts_at
        fields.append("starts_at")
    if "ends_at" in data:
        try:
            event.ends_at = _parse_dt(data.get("ends_at"), "ends_at")
        except ValueError:
            return _json_error("زمان پایان نامعتبر است.")
        fields.append("ends_at")
    if "location" in data:
        event.location = (data.get("location") or "").strip()[:255]
        fields.append("location")
    if "audience_type" in data:
        if data["audience_type"] not in Event.AudienceType.values:
            return _json_error("نوع مخاطب نامعتبر است.")
        event.audience_type = data["audience_type"]
        fields.append("audience_type")
    if fields:
        event.save(update_fields=fields)
    return JsonResponse(_event_payload(event))


@_board_json
@require_POST
def board_event_attendance(request, project, membership, pk):
    event = get_object_or_404(Event, pk=pk, project=project)
    invitee = EventInvitee.objects.filter(event=event, profile=membership.profile).first()
    if invitee is None:
        return _json_error("دعوتی برای شما نیست.", 403)
    data = _payload(request)
    if data is None:
        return _json_error("درخواست نامعتبر است.")
    status = data.get("status") or ""
    if status not in {
        EventInvitee.Attendance.CONFIRMED,
        EventInvitee.Attendance.REJECTED,
    }:
        return _json_error("وضعیت حضور نامعتبر است.")
    invitee.attendance = status
    invitee.save(update_fields=["attendance"])
    return JsonResponse({"ok": True})


# --- Members ---------------------------------------------------------------------


@_board_json
@require_GET
def board_members(request, project, membership):
    rows = (
        ProjectMember.objects.filter(project=project)
        .exclude(invite_status=ProjectMember.InviteStatus.REMOVED)
        .select_related("profile", "profile__user", "role")
        .order_by("created_at")
    )
    return JsonResponse([_member_payload(row) for row in rows], safe=False)


@_board_json
@require_POST
def board_member_invite(request, project, membership):
    if not _is_manager(membership):
        return _json_error("دسترسی ندارید.", 403)
    data = _payload(request)
    if data is None:
        return _json_error("درخواست نامعتبر است.")
    phone = normalize_phone(data.get("phone") or "")
    if not phone:
        return _json_error("شماره موبایل نامعتبر است.")
    profile = Profile.objects.filter(mobile=phone).first()
    if profile is None:
        return _json_error("کاربری با این شماره پیدا نشد.")
    if profile.pk == membership.profile_id:
        return _json_error("نمی‌توانید خودتان را دعوت کنید.")
    role = None
    role_id = data.get("role_id")
    if role_id not in (None, ""):
        try:
            role = Role.objects.get(pk=int(role_id))
        except (TypeError, ValueError, Role.DoesNotExist):
            return _json_error("نقش نامعتبر است.")
    existing = ProjectMember.objects.filter(project=project, profile=profile).first()
    if existing:
        if existing.invite_status == ProjectMember.InviteStatus.ACCEPTED:
            return _json_error("این کاربر از قبل عضو پروژه است.")
        if existing.invite_status == ProjectMember.InviteStatus.INVITED:
            return _json_error("دعوت قبلاً فرستاده شده.")
        existing.invite_status = ProjectMember.InviteStatus.INVITED
        existing.permission = ProjectMember.Permission.MEMBER
        existing.role = role
        existing.invited_by = membership.profile
        existing.save(
            update_fields=["invite_status", "permission", "role", "invited_by", "updated_at"]
        )
        return JsonResponse(_member_payload(existing), status=201)
    row = ProjectMember.objects.create(
        project=project,
        profile=profile,
        role=role,
        permission=ProjectMember.Permission.MEMBER,
        invite_status=ProjectMember.InviteStatus.INVITED,
        invited_by=membership.profile,
    )
    return JsonResponse(_member_payload(row), status=201)


@_board_json
@require_http_methods(["PATCH", "DELETE"])
def board_member_detail(request, project, membership, pk):
    if not _is_manager(membership):
        return _json_error("دسترسی ندارید.", 403)
    row = get_object_or_404(
        ProjectMember.objects.select_related("profile", "profile__user", "role"),
        pk=pk,
        project=project,
    )
    if request.method == "DELETE":
        if (
            row.permission == ProjectMember.Permission.OWNER
            and row.invite_status == ProjectMember.InviteStatus.ACCEPTED
            and _owner_count(project) <= 1
        ):
            return _json_error("آخرین مالک را نمی‌توان حذف کرد.")
        row.invite_status = ProjectMember.InviteStatus.REMOVED
        row.save(update_fields=["invite_status", "updated_at"])
        return JsonResponse({"ok": True})

    data = _payload(request)
    if data is None:
        return _json_error("درخواست نامعتبر است.")
    fields = []
    if "permission" in data:
        permission = data.get("permission")
        if permission not in ProjectMember.Permission.values:
            return _json_error("سطح دسترسی نامعتبر است.")
        if (
            row.permission == ProjectMember.Permission.OWNER
            and permission != ProjectMember.Permission.OWNER
            and row.invite_status == ProjectMember.InviteStatus.ACCEPTED
            and _owner_count(project) <= 1
        ):
            return _json_error("آخرین مالک را نمی‌توان تنزل داد.")
        row.permission = permission
        fields.append("permission")
    if "role_id" in data:
        role_id = data.get("role_id")
        if role_id in (None, ""):
            row.role = None
        else:
            try:
                row.role = Role.objects.get(pk=int(role_id))
            except (TypeError, ValueError, Role.DoesNotExist):
                return _json_error("نقش نامعتبر است.")
        fields.append("role")
    if fields:
        fields.append("updated_at")
        row.save(update_fields=fields)
    return JsonResponse(_member_payload(row))


# --- Dashboards / invites --------------------------------------------------------


@login_required
@require_GET
def my_tasks_dashboard(request):
    profile = ensure_profile(request.user)
    if profile is None:
        return redirect("me-profile")
    now = timezone.now()
    invitations = list(
        EventInvitee.objects.filter(profile=profile)
        .select_related("event", "event__project")
        .order_by("event__starts_at")
    )
    upcoming_events = [row for row in invitations if row.event.starts_at >= now]
    past_events = list(reversed([row for row in invitations if row.event.starts_at < now]))
    assignments = list(
        TaskAssignee.objects.filter(profile=profile)
        .select_related("task", "task__project")
        .order_by("-task__created_at")
    )
    active_tasks = [
        row
        for row in assignments
        if row.task.status in {Task.Status.TODO, Task.Status.IN_PROGRESS, Task.Status.BLOCKED}
    ]
    done_tasks = [row for row in assignments if row.task.status == Task.Status.DONE]
    return render(
        request,
        "pages/my_tasks.html",
        {
            "upcoming_events": upcoming_events,
            "past_events": past_events,
            "active_tasks": active_tasks,
            "done_tasks": done_tasks,
        },
    )


@login_required
@require_GET
def project_invites_list(request):
    profile = ensure_profile(request.user)
    if profile is None:
        return redirect("me-profile")
    invites = (
        ProjectMember.objects.filter(
            profile=profile,
            invite_status=ProjectMember.InviteStatus.INVITED,
        )
        .select_related("project", "invited_by", "invited_by__user", "role")
        .order_by("-created_at")
    )
    return render(request, "pages/project_invites.html", {"invites": invites})


@login_required
@require_POST
def project_invite_accept(request, pk):
    profile = ensure_profile(request.user)
    if profile is None:
        return redirect("me-profile")
    invite = get_object_or_404(
        ProjectMember,
        pk=pk,
        profile=profile,
        invite_status=ProjectMember.InviteStatus.INVITED,
    )
    invite.invite_status = ProjectMember.InviteStatus.ACCEPTED
    invite.save(update_fields=["invite_status", "updated_at"])
    messages.success(request, f"عضویت در «{invite.project.title}» پذیرفته شد.")
    return redirect("board_view", slug=invite.project.slug)


@login_required
@require_POST
def project_invite_reject(request, pk):
    profile = ensure_profile(request.user)
    if profile is None:
        return redirect("me-profile")
    invite = get_object_or_404(
        ProjectMember,
        pk=pk,
        profile=profile,
        invite_status=ProjectMember.InviteStatus.INVITED,
    )
    invite.invite_status = ProjectMember.InviteStatus.REMOVED
    invite.save(update_fields=["invite_status", "updated_at"])
    messages.success(request, "دعوت رد شد.")
    return redirect("project_invites_list")
