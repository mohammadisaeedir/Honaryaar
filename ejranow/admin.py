from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
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
    Project,
    Role,
)

admin.site.unregister(User)
admin.site.unregister(Group)

admin.site.index_title = "ejranow"


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


class CreditInline(TabularInline):
    model = Credit
    extra = 0


class ProfileMediaInline(TabularInline):
    model = ProfileMedia
    extra = 0


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
    list_display = ("name", "city", "status")
    list_filter = ("status", "city")
    search_fields = ("name", "city__title", "slug")
    autocomplete_fields = ("user", "city")
    inlines = (ProfileRoleInline, CreditInline, ProfileMediaInline)


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
    list_display = ("title", "city", "category", "status")
    list_filter = ("status", "category", "city")
    search_fields = ("title", "lead_name", "city__title", "slug")
    autocomplete_fields = ("category", "lead_role", "city")


@admin.register(Opportunity)
class OpportunityAdmin(ModelAdmin):
    list_display = ("title", "project", "role", "city", "deadline", "gender", "paid", "status")
    list_filter = ("status", "paid", "gender", "city", "role")
    date_hierarchy = "deadline"
    search_fields = ("title", "project__title", "city__title", "slug")
    autocomplete_fields = ("project", "role", "city")


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
