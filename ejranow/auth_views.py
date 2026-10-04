from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ejranow.accounts import ensure_profile, user_for_phone
from ejranow.forms import CodeForm, PhoneForm, ProfileForm


def _safe_next(value):
    if not value or not value.startswith("/") or value.startswith("//") or value.startswith("/admin"):
        return ""
    return value


def login_phone(request):
    nxt = _safe_next(request.POST.get("next") or request.GET.get("next"))
    if request.user.is_authenticated:
        return redirect(nxt or "me-profile")
    form = PhoneForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        request.session["login_phone"] = form.cleaned_data["phone"]
        request.session["login_next"] = nxt
        return redirect("login-code")
    return render(request, "pages/login.html", {"form": form, "next": nxt})


def login_code(request):
    nxt = request.session.get("login_next") or ""
    if request.user.is_authenticated:
        return redirect(nxt or "me-profile")
    phone = request.session.get("login_phone")
    if not phone:
        return redirect("login")
    form = CodeForm(phone, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = user_for_phone(phone)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session.pop("login_phone", None)
        request.session.pop("login_next", None)
        return redirect(nxt or "me-profile")
    return render(request, "pages/login_code.html", {"form": form, "phone": phone})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def me_profile(request):
    profile = ensure_profile(request.user)
    complete = bool(profile.first_name and profile.last_name)
    editing = request.GET.get("edit") == "1" or not complete
    form = ProfileForm(
        request.POST or None,
        initial={
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "city": profile.city_id,
            "about": profile.about,
        },
    )
    if request.method == "POST":
        editing = True
        if form.is_valid():
            profile.first_name = form.cleaned_data["first_name"]
            profile.last_name = form.cleaned_data["last_name"]
            profile.name = f"{profile.first_name} {profile.last_name}"
            profile.city = form.cleaned_data["city"]
            profile.about = form.cleaned_data["about"]
            profile.save()
            request.user.first_name = profile.first_name
            request.user.last_name = profile.last_name
            request.user.save(update_fields=["first_name", "last_name"])
            return redirect("me-profile")
    return render(
        request,
        "pages/me_profile.html",
        {"form": form, "profile": profile, "editing": editing},
    )
