from urllib.parse import urlencode

from django.db.models import Count
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from ejranow.catalog import format_date, format_datetime
from ejranow.models import Application, Invite, Match, Opportunity, Profile, Project


def _changelist(model_name, **params):
    url = reverse(f"admin:ejranow_{model_name}_changelist")
    if params:
        return f"{url}?{urlencode(params)}"
    return url


def _change(model_name, pk):
    return reverse(f"admin:ejranow_{model_name}_change", args=[pk])


def _deadline_label(deadline, today):
    label = format_date(deadline)
    days = (deadline - today).days
    if days < 0:
        return f"Overdue · {label}"
    if days == 0:
        return f"{label} · Today"
    if days == 1:
        return f"{label} · Tomorrow"
    return f"{label} · {days} days"


def _link(url, label):
    return format_html('<a href="{}">{}</a>', url, label)


def _table(headers, rows):
    return {"headers": headers, "rows": rows}


def dashboard_callback(request, context):
    today = timezone.localdate()
    deadlines = (
        Opportunity.objects.filter(status="open", deadline__isnull=False)
        .select_related("project", "city")
        .annotate(application_count=Count("applications"))
        .order_by("deadline")[:8]
    )
    applications = Application.objects.select_related("profile", "opportunity").order_by("-created_at")[:8]
    waiting_invites = (
        Invite.objects.filter(status="sent").select_related("profile", "opportunity").order_by("created_at")[:8]
    )
    missing_roles = (
        Profile.objects.filter(user__isnull=False, profile_roles__isnull=True)
        .select_related("user", "city")
        .order_by("-id")[:8]
    )

    context.update(
        {
            "title": "Dashboard",
            "reports": {
                "cards": [
                    {
                        "title": "Open opportunities",
                        "value": Opportunity.objects.filter(status="open").count(),
                        "href": _changelist("opportunity", status__exact="open"),
                    },
                    {
                        "title": "Applications to review",
                        "value": Application.objects.filter(status="submitted").count(),
                        "href": _changelist("application", status__exact="submitted"),
                    },
                    {
                        "title": "Invites waiting",
                        "value": Invite.objects.filter(status="sent").count(),
                        "href": _changelist("invite", status__exact="sent"),
                    },
                    {
                        "title": "Active matches",
                        "value": Match.objects.filter(status="active").count(),
                        "href": _changelist("match", status__exact="active"),
                    },
                    {
                        "title": "Claimed profiles",
                        "value": Profile.objects.filter(status="claimed").count(),
                        "href": _changelist("profile", status__exact="claimed"),
                    },
                    {
                        "title": "Projects without an owner",
                        "value": Project.objects.filter(owner__isnull=True).count(),
                        "href": _changelist("project", owner__isnull="True"),
                    },
                ],
                "deadlines": _table(
                    ["Opportunity", "Project", "Deadline", "Applications"],
                    [
                        [
                            _link(_change("opportunity", item.pk), item.title),
                            item.project.title,
                            _deadline_label(item.deadline, today),
                            item.application_count,
                        ]
                        for item in deadlines
                    ],
                ),
                "applications": _table(
                    ["Profile", "Opportunity", "Status", "Created"],
                    [
                        [
                            _link(_change("profile", item.profile_id), str(item.profile)),
                            _link(_change("opportunity", item.opportunity_id), item.opportunity.title),
                            item.get_status_display(),
                            format_datetime(timezone.localtime(item.created_at)),
                        ]
                        for item in applications
                    ],
                ),
                "invites": _table(
                    ["Profile", "Opportunity", "Sent"],
                    [
                        [
                            _link(_change("profile", item.profile_id), str(item.profile)),
                            _link(_change("opportunity", item.opportunity_id), item.opportunity.title),
                            format_datetime(timezone.localtime(item.created_at)),
                        ]
                        for item in waiting_invites
                    ],
                ),
                "missing_roles": _table(
                    ["Profile", "Mobile", "City"],
                    [
                        [
                            _link(_change("profile", item.pk), str(item)),
                            item.user.username if item.user_id else "",
                            item.city.title if item.city_id else "",
                        ]
                        for item in missing_roles
                    ],
                ),
            },
        }
    )
    return context
