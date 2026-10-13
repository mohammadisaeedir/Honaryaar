import json
import secrets
from urllib.parse import urlencode

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.db.models import Count
from django.http import Http404
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from honaryaar.forms import ArtPickerWidget, DirectUploadWidget
from honaryaar.labels import status_chip_html
from honaryaar.media_files import MediaError
from honaryaar.media_service import (
    assign_file,
    attach_profile_picture,
    attach_project_image,
    attach_testimonial_image,
    enqueue_delete,
    parse_upload_id,
    publish_upload,
    url_for_key,
)
from honaryaar.models import (
    Application,
    Art,
    Bookmark,
    City,
    Credit,
    Invite,
    KIND_REASON_VALUES,
    KindReason,
    Match,
    Opportunity,
    ArtCategory,
    SpecialCondition,
    Profile,
    ProfileMedia,
    ProfileRole,
    ProfileSkill,
    Project,
    Role,
    SupportTicket,
    Testimonial,
    TicketKind,
    TicketStatus,
    Skill,
)
from honaryaar.support_views import close_ticket, open_thread, post_ticket_message

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
        href = reverse("admin:honaryaar_profile_change", args=[profile.pk])
        label = profile.public_name()
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


class ProfileMediaForm(forms.ModelForm):
    parent_id = ""
    upload_id = forms.CharField(
        required=False,
        label="File",
        widget=DirectUploadWidget(purpose="profile", fixed=False),
    )

    class Meta:
        model = ProfileMedia
        exclude = ("file", "thumbnail", "public_acl")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        target = self.instance.profile_id or self.parent_id or ""
        self.fields["upload_id"].widget = DirectUploadWidget(
            purpose="profile",
            kind=self.instance.kind or "photo",
            fixed=False,
            target=target,
        )

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj._pending_upload = (self.cleaned_data.get("upload_id") or "").strip()
        if commit:
            obj.save()
        return obj


class ProjectAdminForm(forms.ModelForm):
    image_upload = forms.CharField(
        required=False,
        label="Image",
        widget=DirectUploadWidget(purpose="project", kind="photo", fixed=True),
    )
    image_remove = forms.BooleanField(required=False, label="Remove image")

    class Meta:
        model = Project
        exclude = ("image", "image_thumb", "image_public_acl")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image_upload"].widget = DirectUploadWidget(
            purpose="project",
            kind="photo",
            fixed=True,
            target=self.instance.pk or "",
        )

    def clean(self):
        cleaned = super().clean()
        if not self.instance.pk and not (cleaned.get("image_upload") or "").strip():
            raise forms.ValidationError("تصویر پروژه را بارگذاری کنید.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj._pending_upload = (self.cleaned_data.get("image_upload") or "").strip()
        obj._remove_image = bool(self.cleaned_data.get("image_remove"))
        if commit:
            obj.save()
        return obj


class TestimonialAdminForm(forms.ModelForm):
    image_upload = forms.CharField(
        required=False,
        label="Image",
        widget=DirectUploadWidget(purpose="testimonial", kind="photo", fixed=True),
    )
    image_remove = forms.BooleanField(required=False, label="Remove image")

    class Meta:
        model = Testimonial
        exclude = ("image", "image_thumb", "image_public_acl")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image_upload"].widget = DirectUploadWidget(
            purpose="testimonial",
            kind="photo",
            fixed=True,
            target=self.instance.pk or "",
        )

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj._pending_upload = (self.cleaned_data.get("image_upload") or "").strip()
        obj._remove_image = bool(self.cleaned_data.get("image_remove"))
        if commit:
            obj.save()
        return obj


def _file_preview(obj, field, kind):
    stored = getattr(obj, field)
    if not getattr(obj, "pk", None) or not stored:
        return "—"
    public = getattr(obj, "is_public", True)
    public_acl = getattr(obj, "public_acl", getattr(obj, "image_public_acl", False))
    url = url_for_key(stored.name, public=public, public_acl=public_acl, kind=kind)
    if not url:
        return "—"
    if kind == "photo":
        return format_html('<img src="{}" alt="" style="max-height:72px;border-radius:8px">', url)
    return format_html('<a href="{}">فایل</a>', url)


def _picture_preview(obj, field, acl_field):
    stored = getattr(obj, field, None)
    if not getattr(obj, "pk", None) or not stored:
        return ""
    url = url_for_key(stored.name, public=True, public_acl=getattr(obj, acl_field, False), kind="photo")
    if not url:
        return ""
    return format_html('<img src="{}" alt="" style="max-height:72px;border-radius:8px">', url)


def finalize_admin_media(user, obj):
    if isinstance(obj, Profile):
        list_id = parse_upload_id(getattr(obj, "_pending_list", ""))
        banner_id = parse_upload_id(getattr(obj, "_pending_banner", ""))
        if list_id or getattr(obj, "_remove_list", False):
            attach_profile_picture(user, obj, list_id, field="list_image", remove=not list_id)
        if banner_id or getattr(obj, "_remove_banner", False):
            attach_profile_picture(user, obj, banner_id, field="banner", remove=not banner_id)
        return
    upload_id = parse_upload_id(getattr(obj, "_pending_upload", ""))
    remove = bool(getattr(obj, "_remove_image", False)) and not upload_id
    if isinstance(obj, ProfileMedia) and upload_id:
        published = publish_upload(
            user,
            upload_id,
            purpose="profile",
            target_id=obj.profile_id,
            public=obj.is_public,
        )
        enqueue_delete(obj.file.name, obj.thumbnail.name)
        obj.kind = published.kind
        obj.public_acl = published.public_acl
        assign_file(obj, "file", published.key)
        assign_file(obj, "thumbnail", published.thumb_key)
        obj.save()
        return
    if isinstance(obj, Project) and (upload_id or remove):
        attach_project_image(user, obj, upload_id, remove=remove)
        return
    if isinstance(obj, Testimonial) and (upload_id or remove):
        attach_testimonial_image(user, obj, upload_id, remove=remove)


def _save_formset_media(request, formset):
    instances = formset.save(commit=False)
    for obj in formset.deleted_objects:
        obj.delete()
    for obj in instances:
        obj.save()
        try:
            finalize_admin_media(request.user, obj)
        except MediaError as exc:
            messages.error(request, exc.message)
    formset.save_m2m()


class ProfileMediaInline(TabularInline):
    model = ProfileMedia
    form = ProfileMediaForm
    extra = 0
    fields = ("kind", "label", "position", "is_public", "upload_id", "file_preview")
    readonly_fields = ("file_preview",)

    def get_formset(self, request, obj=None, **kwargs):
        ProfileMediaForm.parent_id = str(obj.pk) if obj else ""
        return super().get_formset(request, obj, **kwargs)

    def file_preview(self, obj):
        return _file_preview(obj, "file", obj.kind or "photo")


class AdminMedia:
    css = {"all": ("css/media-upload.css",)}
    js = ("js/media-upload.js",)


@admin.register(Skill)
class SkillAdmin(ModelAdmin):
    list_display = ("title", "group", "slug")
    list_filter = ("group",)
    search_fields = ("title", "slug", "group")


@admin.register(Role)
class RoleAdmin(ModelAdmin):
    list_display = ("title", "group", "art_category", "art_name", "slug")
    list_filter = ("group", "art_category__art", "art_category")
    search_fields = ("title", "group", "slug", "art_category__title")
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
        widget=ArtPickerWidget,
        required=False,
        label="Arts",
        help_text="Arts this person works in or is interested in.",
    )
    list_upload = forms.CharField(required=False, label="Main image")
    list_remove = forms.BooleanField(required=False, label="Remove main image")
    banner_upload = forms.CharField(required=False, label="Banner")
    banner_remove = forms.BooleanField(required=False, label="Remove banner")

    class Meta:
        model = Profile
        exclude = (
            "list_image",
            "list_thumb",
            "list_public_acl",
            "banner",
            "banner_thumb",
            "banner_public_acl",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        target = self.instance.pk or ""
        self.fields["list_upload"].widget = DirectUploadWidget(
            purpose="profile_list", kind="photo", fixed=True, target=target
        )
        self.fields["banner_upload"].widget = DirectUploadWidget(
            purpose="profile_banner", kind="photo", fixed=True, target=target
        )
        self.fields["list_upload"].help_text = _picture_preview(self.instance, "list_image", "list_public_acl")
        self.fields["banner_upload"].help_text = _picture_preview(self.instance, "banner", "banner_public_acl")

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj._pending_list = (self.cleaned_data.get("list_upload") or "").strip()
        obj._remove_list = bool(self.cleaned_data.get("list_remove"))
        obj._pending_banner = (self.cleaned_data.get("banner_upload") or "").strip()
        obj._remove_banner = bool(self.cleaned_data.get("banner_remove"))
        if commit:
            obj.save()
        return obj


class StatusChipMixin:
    @admin.display(description="Status", ordering="status")
    def status_chip(self, obj):
        return status_chip_html(obj.status, obj.get_status_display())


@admin.register(Profile)
class ProfileAdmin(StatusChipMixin, ModelAdmin):
    form = ProfileAdminForm
    list_display = (
        "name",
        "user_link",
        "first_name",
        "last_name",
        "birth_date",
        "gender",
        "mobile",
        "city",
        "status_chip",
        "project_link",
        "credit_link",
        "opportunity_link",
        "application_link",
        "invite_link",
        "match_link",
    )
    list_filter = ("status", "gender", "city")
    search_fields = ("name", "user__first_name", "user__last_name", "user__username", "city__title", "slug")
    readonly_fields = ("first_name", "last_name")
    list_select_related = ("user", "city")
    autocomplete_fields = ("user", "city")
    inlines = (ProfileRoleInline, ProfileSkillInline, CreditInline, ProfileMediaInline)
    Media = AdminMedia

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            finalize_admin_media(request.user, obj)
        except MediaError as exc:
            messages.error(request, exc.message)

    def save_formset(self, request, form, formset, change):
        if formset.model is ProfileMedia:
            _save_formset_media(request, formset)
            return
        super().save_formset(request, form, formset, change)

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

    @admin.display(description="First name")
    def first_name(self, profile):
        if not profile.user_id:
            return ""
        return profile.user.first_name

    @admin.display(description="Last name")
    def last_name(self, profile):
        if not profile.user_id:
            return ""
        return profile.user.last_name

    @admin.display(description="Mobile")
    def mobile(self, profile):
        if profile.user_id:
            return profile.user.username
        return ""

    @admin.display(description="Projects")
    def project_link(self, profile):
        return _count_link("admin:honaryaar_project_changelist", {"owner__id__exact": profile.pk}, profile.project_count)

    @admin.display(description="Credits")
    def credit_link(self, profile):
        return _count_link("admin:honaryaar_credit_changelist", {"profile__id__exact": profile.pk}, profile.credit_count)

    @admin.display(description="Opportunities")
    def opportunity_link(self, profile):
        return _count_link(
            "admin:honaryaar_opportunity_changelist",
            {"project__owner__id__exact": profile.pk},
            profile.opportunity_count,
        )

    @admin.display(description="Applications")
    def application_link(self, profile):
        return _count_link(
            "admin:honaryaar_application_changelist",
            {"profile__id__exact": profile.pk},
            profile.application_count,
        )

    @admin.display(description="Invites")
    def invite_link(self, profile):
        return _count_link("admin:honaryaar_invite_changelist", {"profile__id__exact": profile.pk}, profile.invite_count)

    @admin.display(description="Matches")
    def match_link(self, profile):
        return _count_link("admin:honaryaar_match_changelist", {"profile__id__exact": profile.pk}, profile.match_count)


@admin.register(Bookmark)
class BookmarkAdmin(ModelAdmin):
    list_display = ("user", "content_type", "object_id", "target_label", "created_at")
    list_filter = ("content_type",)
    search_fields = ("user__username",)
    autocomplete_fields = ("user",)

    @admin.display(description="Target")
    def target_label(self, bookmark):
        return bookmark.target_label()


@admin.register(ProfileRole)
class ProfileRoleAdmin(ModelAdmin):
    list_display = ("profile", "role", "is_primary")
    list_filter = ("is_primary", "role")
    autocomplete_fields = ("profile", "role")


@admin.register(ProfileMedia)
class ProfileMediaAdmin(ModelAdmin):
    form = ProfileMediaForm
    list_display = ("profile", "kind", "label", "file_preview")
    list_filter = ("kind",)
    search_fields = ("label", "profile__name")
    autocomplete_fields = ("profile",)
    readonly_fields = ("file_preview",)
    Media = AdminMedia

    def file_preview(self, obj):
        return _file_preview(obj, "file", obj.kind or "photo")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            finalize_admin_media(request.user, obj)
        except MediaError as exc:
            messages.error(request, exc.message)


@admin.register(Credit)
class CreditAdmin(ModelAdmin):
    list_display = ("title", "role", "role_name", "year", "profile")
    list_select_related = ("role", "profile")
    search_fields = ("title", "role_name", "role__title", "profile__name")
    autocomplete_fields = ("profile", "role")


def _opportunity_slug():
    for _ in range(5):
        slug = f"o-{secrets.token_hex(4)}"
        if not Opportunity.objects.filter(slug=slug).exists():
            return slug
    return f"o-{secrets.token_hex(8)}"


class OpportunityAdminForm(forms.ModelForm):
    special_conditions = forms.MultipleChoiceField(
        choices=SpecialCondition.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Special conditions",
    )

    class Meta:
        model = Opportunity
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current = self.instance.special_conditions or []
        if isinstance(current, list):
            self.initial.setdefault("special_conditions", current)


class OpportunityInline(TabularInline):
    model = Opportunity
    form = OpportunityAdminForm
    extra = 0
    fields = ("title", "role", "city", "deadline", "gender", "collaboration_type", "experience_level", "special_conditions", "status")
    autocomplete_fields = ("role", "city")
    show_change_link = True
    verbose_name = "Opportunity"
    verbose_name_plural = "Opportunities"


class TestimonialInline(TabularInline):
    model = Testimonial
    form = TestimonialAdminForm
    extra = 0
    fields = ("quote", "name", "profile", "role_label", "role", "featured", "priority", "image_upload", "image_remove", "image_preview")
    readonly_fields = ("image_preview",)
    autocomplete_fields = ("profile", "role")

    def image_preview(self, obj):
        return _file_preview(obj, "image", "photo")


@admin.register(Testimonial)
class TestimonialAdmin(ModelAdmin):
    form = TestimonialAdminForm
    list_display = ("display_name", "profile", "role", "role_label", "project", "featured", "priority", "image_preview")
    list_filter = ("featured",)
    list_select_related = ("profile", "role", "project")
    search_fields = ("name", "quote", "profile__name", "role__title", "project__title")
    autocomplete_fields = ("profile", "role", "project")
    readonly_fields = ("image_preview",)
    Media = AdminMedia

    def image_preview(self, obj):
        return _file_preview(obj, "image", "photo")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            finalize_admin_media(request.user, obj)
        except MediaError as exc:
            messages.error(request, exc.message)

    @admin.display(description="Name")
    def display_name(self, item):
        if item.name:
            return item.name
        if item.profile_id:
            return item.profile.public_name()
        return ""


@admin.register(Project)
class ProjectAdmin(StatusChipMixin, ModelAdmin):
    form = ProjectAdminForm
    list_display = ("title", "owner", "city", "art_name", "art_category", "start_date", "featured", "status_chip", "opportunity_link")
    list_filter = ("status", "featured", "art_category__art", "art_category", "city")
    list_editable = ("featured",)
    search_fields = ("title", "owner__user__first_name", "owner__user__last_name", "owner__name", "city__title", "art_category__title", "slug")
    autocomplete_fields = ("owner", "art_category", "lead_role", "city")
    list_select_related = ("owner", "city", "art_category")
    readonly_fields = ("image_preview",)
    Media = AdminMedia

    @admin.display(description="Art", ordering="art_category__art")
    def art_name(self, project):
        if project.art_category_id:
            return project.art_category.get_art_display()
        return ""

    def image_preview(self, project):
        return _file_preview(project, "image", "photo")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            finalize_admin_media(request.user, obj)
        except MediaError as exc:
            messages.error(request, exc.message)

    inlines = [OpportunityInline, TestimonialInline]

    def save_formset(self, request, form, formset, change):
        if formset.model is Testimonial:
            _save_formset_media(request, formset)
            return
        if formset.model is not Opportunity:
            return super().save_formset(request, form, formset, change)
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for obj in instances:
            if not obj.slug:
                obj.slug = _opportunity_slug()
            if not obj.art_category_id:
                obj.art_category_id = form.instance.art_category_id
            if not obj.pk and not obj.city_id:
                obj.city_id = form.instance.city_id
            obj.save()
        formset.save_m2m()

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(opportunity_count=Count("opportunities", distinct=True))

    @admin.display(description="Opportunities")
    def opportunity_link(self, project):
        return _count_link(
            "admin:honaryaar_opportunity_changelist",
            {"project__id__exact": project.pk},
            project.opportunity_count,
        )


@admin.register(Opportunity)
class OpportunityAdmin(StatusChipMixin, ModelAdmin):
    form = OpportunityAdminForm
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
        "status_chip",
        "application_link",
        "invite_link",
    )
    list_filter = ("status", "paid", "featured", "gender", "collaboration_type", "experience_level", "city", "role", "art_category__art", "art_category")
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
            "admin:honaryaar_application_changelist",
            {"opportunity__id__exact": opportunity.pk},
            opportunity.application_count,
        )

    @admin.display(description="Invites")
    def invite_link(self, opportunity):
        return _count_link(
            "admin:honaryaar_invite_changelist",
            {"opportunity__id__exact": opportunity.pk},
            opportunity.invite_count,
        )


@admin.register(Application)
class ApplicationAdmin(StatusChipMixin, ModelAdmin):
    list_display = ("profile", "opportunity", "status_chip", "created_at")
    list_filter = ("status",)
    search_fields = ("profile__name", "opportunity__title")
    autocomplete_fields = ("profile", "opportunity")


@admin.register(Invite)
class InviteAdmin(StatusChipMixin, ModelAdmin):
    list_display = ("profile", "opportunity", "status_chip", "created_at")
    list_filter = ("status",)
    search_fields = ("profile__name", "opportunity__title")
    autocomplete_fields = ("profile", "opportunity")


@admin.register(Match)
class MatchAdmin(StatusChipMixin, ModelAdmin):
    list_display = ("profile", "opportunity", "status_chip", "created_at")
    list_filter = ("status",)
    search_fields = ("profile__name", "opportunity__title")
    autocomplete_fields = ("profile", "opportunity", "application", "invite")


def kind_reason_choices(kind):
    allowed = KIND_REASON_VALUES.get(kind, set())
    return [(value, label) for value, label in KindReason.choices if value in allowed]


class SupportTicketAdminForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            kind = self.data.get("kind") or ""
        elif self.instance.pk:
            kind = self.instance.kind
        else:
            kind = TicketKind.CONTACT
        self.fields["kind_reason"].choices = kind_reason_choices(kind)
        mapping = {key: kind_reason_choices(key) for key in KIND_REASON_VALUES}
        self.fields["kind"].widget.attrs["data-kind-reasons"] = json.dumps(mapping)


@admin.register(SupportTicket)
class SupportTicketAdmin(StatusChipMixin, ModelAdmin):
    form = SupportTicketAdminForm
    change_form_outer_before_template = "admin/supportticket/thread.html"
    list_display = ("kind", "kind_reason", "status_chip", "user", "target_label", "message_count", "created_at")
    list_filter = ("kind", "kind_reason", "status")
    search_fields = ("body", "user__username")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("user", "content_type")

    class Media:
        js = ("js/admin-kind-reason.js",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(message_total=Count("messages"))

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("body", "created_at", "updated_at")
        return ("created_at", "updated_at")

    def get_urls(self):
        custom = [
            path(
                "<path:object_id>/reply/",
                self.admin_site.admin_view(self.reply_view),
                name="honaryaar_supportticket_reply",
            ),
        ]
        return custom + super().get_urls()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            open_thread(obj)

    def reply_view(self, request, object_id):
        ticket = self.get_object(request, object_id)
        if ticket is None or request.method != "POST":
            raise Http404
        change_url = reverse("admin:honaryaar_supportticket_change", args=[ticket.pk])
        if request.POST.get("action") == "close":
            close_ticket(ticket)
            messages.success(request, "Ticket closed.")
            return redirect(change_url)
        body = (request.POST.get("body") or "").strip()
        if ticket.status == TicketStatus.CLOSED:
            messages.error(request, "This ticket is closed.")
        elif not body:
            messages.error(request, "Write a reply.")
        elif post_ticket_message(ticket, author=request.user, from_staff=True, body=body):
            messages.success(request, "Reply sent.")
        return redirect(change_url)

    @admin.display(description="Target")
    def target_label(self, item):
        return item.target_label()

    @admin.display(description="Messages", ordering="message_total")
    def message_count(self, item):
        return item.message_total
