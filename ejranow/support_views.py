from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ejranow.accounts import current_profile
from ejranow.catalog import artist_by_slug, opportunity_by_slug, project_by_slug
from ejranow.forms import ContactForm, ReportForm, TicketForm, TicketReplyForm
from ejranow.models import (
    Opportunity,
    Profile,
    Project,
    SupportTicket,
    TicketKind,
    TicketMessage,
    TicketStatus,
)


def open_thread(ticket):
    TicketMessage.objects.create(
        ticket=ticket,
        author=ticket.user,
        from_staff=False,
        body=ticket.body,
    )


def post_ticket_message(ticket, *, author, from_staff, body):
    if ticket.status == TicketStatus.CLOSED:
        return False
    with transaction.atomic():
        TicketMessage.objects.create(
            ticket=ticket,
            author=author,
            from_staff=from_staff,
            body=body,
        )
        ticket.status = TicketStatus.ANSWERED if from_staff else TicketStatus.OPEN
        ticket.save(update_fields=["status", "updated_at"])
    return True


def close_ticket(ticket):
    if ticket.status == TicketStatus.CLOSED:
        return
    ticket.status = TicketStatus.CLOSED
    ticket.save(update_fields=["status", "updated_at"])


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ticket = SupportTicket.objects.create(
            kind=TicketKind.CONTACT,
            kind_reason=form.cleaned_data["kind_reason"],
            user=request.user if request.user.is_authenticated else None,
            body=form.cleaned_data["body"],
        )
        open_thread(ticket)
        return redirect("/contact/?sent=1")
    return render(
        request,
        "pages/contact.html",
        {"form": form, "sent": request.GET.get("sent") == "1"},
    )


def report_page_state(request, target):
    draft = request.session.get("report_draft")
    sent = request.GET.get("reported") == "1"
    open_modal = sent or request.GET.get("report") == "1"
    if draft and draft.get("target") == target:
        request.session.pop("report_draft", None)
        form = ReportForm(
            {"kind_reason": draft.get("kind_reason", ""), "body": draft.get("body", "")},
        )
        form.is_valid()
        return {"report_form": form, "report_open": True, "report_sent": False}
    return {"report_form": ReportForm(), "report_open": open_modal, "report_sent": sent}


def _report(request, *, back, target, obj):
    if request.method != "POST":
        return redirect(f"{back}?report=1")
    form = ReportForm(request.POST)
    if form.is_valid():
        ticket = SupportTicket.objects.create(
            kind=TicketKind.REPORT,
            kind_reason=form.cleaned_data["kind_reason"],
            user=request.user if request.user.is_authenticated else None,
            content_type=ContentType.objects.get_for_model(obj),
            object_id=obj.pk,
            body=form.cleaned_data["body"],
        )
        open_thread(ticket)
        request.session.pop("report_draft", None)
        return redirect(f"{back}?reported=1")
    request.session["report_draft"] = {
        "target": target,
        "kind_reason": request.POST.get("kind_reason", ""),
        "body": request.POST.get("body", ""),
    }
    return redirect(f"{back}?report=1")


def report_artist(request, slug):
    if artist_by_slug(slug) is None:
        raise Http404
    profile = get_object_or_404(Profile, slug=slug)
    return _report(
        request,
        back=reverse("artist", args=[slug]),
        target=f"artist:{slug}",
        obj=profile,
    )


def report_project(request, slug):
    project_page = project_by_slug(slug)
    if project_page is None:
        raise Http404
    project = get_object_or_404(Project, slug=slug)
    return _report(
        request,
        back=reverse("project", args=[slug]),
        target=f"project:{slug}",
        obj=project,
    )


def report_opportunity(request, slug):
    page = opportunity_by_slug(slug)
    if page is None:
        raise Http404
    opportunity = get_object_or_404(Opportunity.objects.select_related("project"), slug=slug)
    return _report(
        request,
        back=reverse("opportunity", args=[slug]),
        target=f"opportunity:{slug}",
        obj=opportunity,
    )


@login_required
def my_tickets(request):
    form = TicketForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ticket = SupportTicket.objects.create(
            kind=TicketKind.TICKET,
            kind_reason=form.cleaned_data["kind_reason"],
            user=request.user,
            body=form.cleaned_data["body"],
        )
        open_thread(ticket)
        messages.success(request, "تیکت ثبت شد.")
        return redirect("me-tickets")
    tickets = request.user.support_tickets.filter(kind=TicketKind.TICKET).prefetch_related("messages")
    return render(
        request,
        "pages/me_tickets.html",
        {
            "form": form,
            "form_open": request.method == "POST",
            "open_tickets": tickets.filter(status__in=[TicketStatus.OPEN, TicketStatus.ANSWERED]),
            "closed_tickets": tickets.filter(status=TicketStatus.CLOSED),
            "profile": current_profile(request.user),
        },
    )


@login_required
def my_ticket(request, pk):
    ticket = get_object_or_404(
        request.user.support_tickets.filter(kind=TicketKind.TICKET).prefetch_related("messages"),
        pk=pk,
    )
    form = TicketReplyForm()
    if request.method == "POST":
        if request.POST.get("action") == "close":
            close_ticket(ticket)
            messages.success(request, "تیکت بسته شد.")
            return redirect("me-ticket", pk=ticket.pk)
        if ticket.status == TicketStatus.CLOSED:
            messages.error(request, "این تیکت بسته شده است.")
            return redirect("me-ticket", pk=ticket.pk)
        form = TicketReplyForm(request.POST)
        if form.is_valid():
            post_ticket_message(
                ticket,
                author=request.user,
                from_staff=False,
                body=form.cleaned_data["body"],
            )
            messages.success(request, "پاسخ ثبت شد.")
            return redirect("me-ticket", pk=ticket.pk)
    return render(
        request,
        "pages/me_ticket.html",
        {
            "ticket": ticket,
            "messages_list": ticket.messages.all(),
            "form": form,
            "profile": current_profile(request.user),
        },
    )
