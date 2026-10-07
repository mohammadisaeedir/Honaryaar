from urllib.parse import urlencode

from django import forms
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
    Art,
    City,
    Credit,
    Invite,
    Match,
    Opportunity,
    ArtCategory,
    Profile,
    ProfileMedia,
    ProfileRole,
    ProfileSkill,
    Project,
    Role,
    Testimonial,
    Skill,
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
    list_display = (
        "username",
        "profile_link",
        "email",
        "first_name",
        "last_name",
        "is_staff",
    )
    list_select_related = ("profile",)

    @admin.display(description="Profile")
    def profile_link(self, user):
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return ""
        href = reverse("admin:ejranow_profile_change", args=[profile.pk])
        label = profile.name or profile.slug
        return format_html('<a href="{}">{}</a>', href, label)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


class ProfileRoleInline(TabularInline):
    model = ProfileRole
    extra = 0


@admin.register(ProfileSkill)
class ProfileSkillAdmin(ModelAdmin):
    list_display = ("profile", "skill", "level")
    list_filter = ("level", "skill__group")
    search_fields = ("profile__name", "skill__title", "skill__group")
    list_select_related = ("profile", "skill")
    autocomplete_fields = ("profile", "skill")


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


@admin.register(Skill)
class SkillAdmin(ModelAdmin):
    list_display = ("title", "group", "slug")
    list_filter = ("group",)
    search_fields = ("title", "slug", "group")


@admin.register(Role)
class RoleAdmin(ModelAdmin):
    list_display = ("title", "art_category", "art_name", "slug")
    list_filter = ("art_category__art", "art_category")
    search_fields = ("title", "slug", "art_category__title")
    autocomplete_fields = ("art_category",)
    list_select_related = ("art_category",)

    @admin.display(description="Art", ordering="art_category__art")
    def art_name(self, role):
        if role.art_category_id:
            return role.art_category.get_art_display()
        return ""


@admin.register(City)
class CityAdmin(ModelAdmin):
    list_display = ("title", "province", "featured", "priority")
    list_filter = ("featured", "province")
    search_fields = ("title", "province", "slug")
    ordering = ("priority", "title")


@admin.register(ArtCategory)
class ArtCategoryAdmin(ModelAdmin):
    list_display = ("title", "art", "slug", "priority")
    list_filter = ("art",)
    search_fields = ("title", "slug")
    ordering = ("priority", "title")


class ProfileAdminForm(forms.ModelForm):
    arts = forms.MultipleChoiceField(
        choices=Art.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Arts",
        help_text="Arts this person works in or is interested in.",
    )

    class Meta:
        model = Profile
        fields = "__all__"


@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    form = ProfileAdminForm
    list_display = (
        "name",
        "user_link",
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

    @admin.display(description="User")
    def user_link(self, profile):
        if not profile.user_id:
            return ""
        href = reverse("admin:auth_user_change", args=[profile.user_id])
        return format_html('<a href="{}">{}</a>', href, profile.user.username)

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
    list_display = ("title", "role", "role_name", "year", "profile")
    list_select_related = ("role", "profile")
    search_fields = ("title", "role_name", "role__title", "profile__name")
    autocomplete_fields = ("profile", "role")


class TestimonialInline(TabularInline):
    model = Testimonial
    extra = 0
    fields = ("quote", "name", "profile", "role_label", "role", "featured", "priority")
    autocomplete_fields = ("profile", "role")


@admin.register(Testimonial)
class TestimonialAdmin(ModelAdmin):
    list_display = ("display_name", "profile", "role", "role_label", "project", "featured", "priority")
    list_filter = ("featured",)
    list_select_related = ("profile", "role", "project")
    search_fields = ("name", "quote", "profile__name", "role__title", "project__title")
    autocomplete_fields = ("profile", "role", "project")

    @admin.display(description="Name")
    def display_name(self, item):
        if item.name:
            return item.name
        if item.profile_id:
            return item.profile.name or item.profile.slug
        return ""


@admin.register(Project)
class ProjectAdmin(ModelAdmin):
    list_display = ("title", "owner", "city", "art_name", "art_category", "status", "opportunity_link")
    list_filter = ("status", "art_category__art", "art_category", "city")
    search_fields = ("title", "owner__first_name", "owner__last_name", "owner__name", "city__title", "art_category__title", "slug")
    autocomplete_fields = ("owner", "art_category", "lead_role", "city")
    list_select_related = ("owner", "city", "art_category")

    @admin.display(description="Art", ordering="art_category__art")
    def art_name(self, project):
        if project.art_category_id:
            return project.art_category.get_art_display()
        return ""
    inlines = [TestimonialInline]

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
        "art_name",
        "art_category",
        "city",
        "deadline",
        "gender",
        "paid",
        "featured",
        "status",
        "application_link",
        "invite_link",
    )
    list_filter = ("status", "paid", "featured", "gender", "city", "role", "art_category__art", "art_category")
    list_editable = ("featured",)
    date_hierarchy = "deadline"
    search_fields = ("title", "project__title", "city__title", "art_category__title", "slug")
    autocomplete_fields = ("project", "role", "city", "art_category")
    list_select_related = ("project", "role", "city", "art_category")

    @admin.display(description="Art", ordering="art_category__art")
    def art_name(self, opportunity):
        if opportunity.art_category_id:
            return opportunity.art_category.get_art_display()
        return ""

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if not initial.get("city"):
            project_id = request.GET.get("project")
            city_id = Project.objects.filter(pk=project_id).values_list("city_id", flat=True).first()
            if city_id:
                initial["city"] = city_id
        return initial

    def save_model(self, request, obj, form, change):
        if not change and not obj.city_id and obj.project_id:
            obj.city_id = obj.project.city_id
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if formfield and db_field.name == "city":
            formfield.help_text = "On a new call, leave this empty to copy the project city. Pick another city to override it."
        return formfield

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
