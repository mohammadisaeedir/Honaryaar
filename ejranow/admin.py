from urllib.parse import urlencode

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from ejranow.models import (
    Application,
    ArtCategory,
    City,
    Credit,
    Invite,
    Match,
    Opportunity,
    Profile,
    ProfileMedia,
    ProfileRole,
    ProfileSkill,
    Project,
    Role,
    Skill,
    SkillGroup,
)

admin.site.unregister(User)
admin.site.unregister(Group)

admin.site.index_title = "Honaryaar"


def _count_link(url_name, params, count):
    href = reverse(url_name)
    if params:
        href = f"{href}?{urlencode(params)}"
    return format_html('<a href="{}">{}</a>', href, count)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


class ProfileRoleInline(TabularInline):
    model = ProfileRole
    extra = 0


class ProfileSkillInline(TabularInline):
    model = ProfileSkill
    extra = 0
    autocomplete_fields = ("skill",)


class CreditInline(TabularInline):
    model = Credit
    extra = 0


class ProfileMediaInline(TabularInline):
    model = ProfileMedia
    extra = 0


class SkillInline(TabularInline):
    model = Skill
    extra = 0


@admin.register(SkillGroup)
class SkillGroupAdmin(ModelAdmin):
    list_display = ("title", "slug", "priority")
    search_fields = ("title", "slug")
    ordering = ("priority", "title")
    inlines = (SkillInline,)


@admin.register(Skill)
class SkillAdmin(ModelAdmin):
    list_display = ("title", "group", "slug")
    list_filter = ("group",)
    search_fields = ("title", "slug", "group__title")
    list_select_related = ("group",)
    autocomplete_fields = ("group",)


@admin.register(Role)
class RoleAdmin(ModelAdmin):
    list_display = ("title", "slug")
    search_fields = ("title", "slug")


@admin.register(City)
class CityAdmin(ModelAdmin):
    list_display = ("title", "province", "featured", "priority")
    list_filter = ("featured", "province")
    search_fields = ("title", "province", "slug")
    ordering = ("priority", "title")


@admin.register(ArtCategory)
class ArtCategoryAdmin(ModelAdmin):
    list_display = ("title", "slug", "active")
    list_filter = ("active",)
    search_fields = ("title", "slug")


@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    list_display = (
        "name",
        "first_name",
        "last_name",
        "mobile",
        "city",
        "status",
        "project_link",
        "credit_link",
        "opportunity_link",
        "application_link",
        "invite_link",
        "match_link",
    )
    list_filter = ("status", "city")
    search_fields = ("name", "first_name", "last_name", "user__username", "city__title", "slug")
    list_select_related = ("user", "city")
    autocomplete_fields = ("user", "city")
    inlines = (ProfileRoleInline, ProfileSkillInline, CreditInline, ProfileMediaInline)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                project_count=Count("owned_projects", distinct=True),
                credit_count=Count("credits", distinct=True),
                opportunity_count=Count("owned_projects__opportunities", distinct=True),
                application_count=Count("applications", distinct=True),
                invite_count=Count("invites", distinct=True),
                match_count=Count("matches", distinct=True),
            )
        )

    @admin.display(description="Mobile")
    def mobile(self, profile):
        if profile.user_id:
            return profile.user.username
        return ""

    @admin.display(description="Projects")
    def project_link(self, profile):
        return _count_link("admin:ejranow_project_changelist", {"owner__id__exact": profile.pk}, profile.project_count)

    @admin.display(description="Credits")
    def credit_link(self, profile):
        return _count_link("admin:ejranow_credit_changelist", {"profile__id__exact": profile.pk}, profile.credit_count)

    @admin.display(description="Opportunities")
    def opportunity_link(self, profile):
        return _count_link(
            "admin:ejranow_opportunity_changelist",
            {"project__owner__id__exact": profile.pk},
            profile.opportunity_count,
        )

    @admin.display(description="Applications")
    def application_link(self, profile):
        return _count_link(
            "admin:ejranow_application_changelist",
            {"profile__id__exact": profile.pk},
            profile.application_count,
        )

    @admin.display(description="Invites")
    def invite_link(self, profile):
        return _count_link("admin:ejranow_invite_changelist", {"profile__id__exact": profile.pk}, profile.invite_count)

    @admin.display(description="Matches")
    def match_link(self, profile):
        return _count_link("admin:ejranow_match_changelist", {"profile__id__exact": profile.pk}, profile.match_count)


@admin.register(ProfileRole)
class ProfileRoleAdmin(ModelAdmin):
    list_display = ("profile", "role", "is_primary")
    list_filter = ("is_primary", "role")
    autocomplete_fields = ("profile", "role")


@admin.register(ProfileMedia)
class ProfileMediaAdmin(ModelAdmin):
    list_display = ("profile", "kind", "label")
    list_filter = ("kind",)
    search_fields = ("label", "profile__name")
    autocomplete_fields = ("profile",)


@admin.register(Credit)
class CreditAdmin(ModelAdmin):
    list_display = ("title", "role_name", "year", "profile")
    search_fields = ("title", "role_name", "profile__name")
    autocomplete_fields = ("profile",)


@admin.register(Project)
class ProjectAdmin(ModelAdmin):
    list_display = ("title", "owner", "city", "category", "status", "opportunity_link")
    list_filter = ("status", "category", "city")
    search_fields = ("title", "lead_name", "owner__name", "city__title", "slug")
    autocomplete_fields = ("owner", "category", "lead_role", "city")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(opportunity_count=Count("opportunities", distinct=True))

    @admin.display(description="Opportunities")
    def opportunity_link(self, project):
        return _count_link(
            "admin:ejranow_opportunity_changelist",
            {"project__id__exact": project.pk},
            project.opportunity_count,
        )


@admin.register(Opportunity)
class OpportunityAdmin(ModelAdmin):
    list_display = (
        "title",
        "project",
        "role",
        "city",
        "deadline",
        "gender",
        "paid",
        "status",
        "application_link",
        "invite_link",
    )
    list_filter = ("status", "paid", "gender", "city", "role")
    date_hierarchy = "deadline"
    search_fields = ("title", "project__title", "city__title", "slug")
    autocomplete_fields = ("project", "role", "city")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                application_count=Count("applications", distinct=True),
                invite_count=Count("invites", distinct=True),
            )
        )

    def lookup_allowed(self, lookup, value, request):
        if lookup.startswith("project__owner"):
            return True
        return super().lookup_allowed(lookup, value, request)

    @admin.display(description="Applications")
    def application_link(self, opportunity):
        return _count_link(
            "admin:ejranow_application_changelist",
            {"opportunity__id__exact": opportunity.pk},
            opportunity.application_count,
        )

    @admin.display(description="Invites")
    def invite_link(self, opportunity):
        return _count_link(
            "admin:ejranow_invite_changelist",
            {"opportunity__id__exact": opportunity.pk},
            opportunity.invite_count,
        )


@admin.register(Application)
class ApplicationAdmin(ModelAdmin):
    list_display = ("profile", "opportunity", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("profile__name", "opportunity__title")
    autocomplete_fields = ("profile", "opportunity")


@admin.register(Invite)
class InviteAdmin(ModelAdmin):
    list_display = ("profile", "opportunity", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("profile__name", "opportunity__title")
    autocomplete_fields = ("profile", "opportunity")


@admin.register(Match)
class MatchAdmin(ModelAdmin):
    list_display = ("profile", "opportunity", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("profile__name", "opportunity__title")
    autocomplete_fields = ("profile", "opportunity", "application", "invite")
