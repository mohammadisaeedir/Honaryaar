from datetime import date

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.forms import BaseFormSet, formset_factory

from honaryaar.accounts import code_matches, normalize_phone
from honaryaar.jalali_widget import JalaliDateWidget
from honaryaar.labels import CHIP_LABELS, COLLABORATION_TYPES, EXPERIENCE_LEVELS, MEDIA_LABELS, SPECIAL_CONDITIONS
from honaryaar.models import (
    CONTACT_REASONS,
    REPORT_REASONS,
    TICKET_REASONS,
    Art,
    ArtCategory,
    Bookmark,
    City,
    Opportunity,
    Profile,
    ProjectStatus,
    Role,
)


class PhoneForm(forms.Form):
    phone = forms.CharField(
        error_messages={"required": "شماره موبایل را وارد کنید."},
    )

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if not phone:
            raise forms.ValidationError("شماره موبایل را درست وارد کنید.")
        return phone


class CodeForm(forms.Form):
    code = forms.CharField(
        error_messages={"required": "کد را وارد کنید."},
    )

    def __init__(self, phone, *args, **kwargs):
        self.phone = phone
        super().__init__(*args, **kwargs)

    def clean_code(self):
        code = self.cleaned_data["code"]
        if not code_matches(self.phone, code):
            raise forms.ValidationError("کد درست نیست.")
        return code


class ArtPickerWidget(forms.CheckboxSelectMultiple):
    template_name = "widgets/art_picker.html"


class GenderPickerWidget(forms.RadioSelect):
    template_name = "widgets/gender_picker.html"


class SkillPickerWidget(forms.Widget):
    template_name = "components/skill_picker.html"

    class Media:
        css = {"all": ("css/skill-picker.css",)}
        js = ("js/skill-picker.js",)

    def __init__(self, catalog=None, chosen=None, attrs=None):
        super().__init__(attrs)
        self.catalog = catalog or []
        self.chosen = chosen or []

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["skill_catalog"] = self.catalog
        context["skill_chosen"] = self.chosen
        return context


class RolePickerWidget(forms.Widget):
    template_name = "components/role_picker.html"

    class Media:
        css = {"all": ("css/skill-picker.css",)}
        js = ("js/role-picker.js",)

    def __init__(self, catalog=None, chosen=None, attrs=None):
        super().__init__(attrs)
        self.catalog = catalog or []
        self.chosen = chosen or []

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["role_catalog"] = self.catalog
        context["role_chosen"] = self.chosen
        return context


class ReasonPickerWidget(forms.RadioSelect):
    template_name = "widgets/reason_picker.html"


class ProfileForm(forms.Form):
    first_name = forms.CharField(max_length=60, required=False)
    last_name = forms.CharField(max_length=60, required=False)
    name = forms.CharField(max_length=120, required=False)
    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        required=False,
        empty_label="انتخاب شهر",
    )
    about = forms.CharField(required=False)
    birth_date = forms.DateField(
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=JalaliDateWidget(attrs={"class": "field jalali-date__text"}),
    )
    gender = forms.ChoiceField(
        required=False,
        choices=[("", "انتخاب جنسیت"), ("male", "مرد"), ("female", "زن")],
        widget=GenderPickerWidget,
    )
    arts = forms.MultipleChoiceField(choices=Art.choices, required=False, widget=ArtPickerWidget)

    def clean_first_name(self):
        return (self.cleaned_data.get("first_name") or "").strip()

    def clean_last_name(self):
        return (self.cleaned_data.get("last_name") or "").strip()

    def clean_name(self):
        return (self.cleaned_data.get("name") or "").strip()

    def clean_about(self):
        return self.cleaned_data["about"].strip()

    def clean_birth_date(self):
        value = self.cleaned_data.get("birth_date")
        if value and value > date.today():
            raise forms.ValidationError("تاریخ تولد نمی‌تواند در آینده باشد.")
        return value


class RoleRowForm(forms.Form):
    role = forms.ModelChoiceField(queryset=Role.objects.all(), required=False, empty_label="انتخاب نقش")
    delete = forms.BooleanField(required=False)


class BaseRoleFormSet(BaseFormSet):
    def clean(self):
        seen = set()
        for form in self.forms:
            cleaned = form.cleaned_data
            if not cleaned or cleaned.get("delete"):
                continue
            role = cleaned.get("role")
            if not role:
                continue
            if role.pk in seen:
                form.add_error("role", "این نقش تکرار شده است.")
            seen.add(role.pk)


RoleFormSet = formset_factory(RoleRowForm, formset=BaseRoleFormSet, extra=0)


class CreditRowForm(forms.Form):
    credit_id = forms.IntegerField(required=False)
    title = forms.CharField(required=False, max_length=160)
    role = forms.ModelChoiceField(queryset=Role.objects.all(), required=False, empty_label="انتخاب نقش")
    role_name = forms.CharField(required=False, max_length=120)
    year = forms.CharField(required=False, max_length=20)
    delete = forms.BooleanField(required=False)

    def clean(self):
        cleaned = super().clean()
        title = (cleaned.get("title") or "").strip()
        role_name = (cleaned.get("role_name") or "").strip()
        year = (cleaned.get("year") or "").strip()
        cleaned["title"] = title
        cleaned["role_name"] = role_name
        cleaned["year"] = year
        if cleaned.get("delete") or not any((title, role_name, year, cleaned.get("role"))):
            return cleaned
        if not title or not role_name:
            raise forms.ValidationError("عنوان و نام نقش سابقه را با هم وارد کنید.")
        return cleaned


class MediaRowForm(forms.Form):
    media_id = forms.IntegerField(required=False)
    upload_id = forms.CharField(required=False)
    kind = forms.ChoiceField(choices=[(key, label) for key, label in MEDIA_LABELS.items()], required=False)
    label = forms.CharField(required=False, max_length=160)
    delete = forms.BooleanField(required=False)

    def clean(self):
        cleaned = super().clean()
        label = (cleaned.get("label") or "").strip()
        cleaned["label"] = label
        if cleaned.get("delete") or not label:
            return cleaned
        if not cleaned.get("kind"):
            cleaned["kind"] = "photo"
        return cleaned


CreditFormSet = formset_factory(CreditRowForm, extra=0)
MediaFormSet = formset_factory(MediaRowForm, extra=0)


class ProjectCreateForm(forms.Form):
    title = forms.CharField(
        max_length=160,
        error_messages={"required": "نام پروژه را وارد کنید."},
    )
    city = forms.ModelChoiceField(queryset=City.objects.all(), required=False)
    art_category = forms.ModelChoiceField(
        queryset=ArtCategory.objects.order_by("priority", "title"),
        error_messages={"required": "نوع هنر را انتخاب کنید."},
    )
    summary = forms.CharField(required=False)
    start_date = forms.DateField(
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=JalaliDateWidget(attrs={"class": "field jalali-date__text"}),
    )
    status = forms.ChoiceField(
        choices=[(value, CHIP_LABELS[value]) for value, _label in ProjectStatus.choices],
        initial=ProjectStatus.DRAFT,
    )
    image_upload = forms.CharField(required=False)
    image_remove = forms.BooleanField(required=False)

    def clean_title(self):
        value = self.cleaned_data["title"].strip()
        if not value:
            raise forms.ValidationError("نام پروژه را وارد کنید.")
        return value

    def clean_summary(self):
        return self.cleaned_data["summary"].strip()


AGE_FLOOR = 16
AGE_CEILING = 80


class OpportunityForm(forms.Form):
    title = forms.CharField(
        max_length=160,
        error_messages={"required": "نام نقش را وارد کنید."},
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        error_messages={"required": "نقش را انتخاب کنید."},
    )
    deadline = forms.DateField(
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=JalaliDateWidget(attrs={"class": "field jalali-date__text"}),
    )
    description = forms.CharField(required=False)
    city = forms.ModelChoiceField(queryset=City.objects.all(), required=False)
    collaboration_type = forms.ChoiceField(choices=[("", "انتخاب نوع همکاری")] + COLLABORATION_TYPES, required=False)
    experience_level = forms.ChoiceField(choices=[("", "انتخاب سطح تجربه")] + EXPERIENCE_LEVELS, required=False)
    special_conditions = forms.MultipleChoiceField(choices=SPECIAL_CONDITIONS, required=False)
    age_min = forms.IntegerField(required=False, min_value=AGE_FLOOR, max_value=AGE_CEILING)
    age_max = forms.IntegerField(required=False, min_value=AGE_FLOOR, max_value=AGE_CEILING)

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("age_min")
        end = cleaned.get("age_max")
        if start is None and end is None:
            return cleaned
        if start is None or end is None:
            self.add_error("age_min", "هر دو سر رنج سنی را مشخص کنید.")
            return cleaned
        if start > end:
            self.add_error("age_min", "شروع رنج سنی از پایان آن بیشتر است.")
            return cleaned
        if start == AGE_FLOOR and end == AGE_CEILING:
            cleaned["age_min"] = None
            cleaned["age_max"] = None
        return cleaned

    def clean_title(self):
        value = self.cleaned_data["title"].strip()
        if not value:
            raise forms.ValidationError("نام نقش را وارد کنید.")
        return value

    def clean_description(self):
        return self.cleaned_data["description"].strip()


class ApplyForm(forms.Form):
    message = forms.CharField(required=False)

    def clean_message(self):
        return self.cleaned_data["message"].strip()


def _invite_name(profile):
    full = f"{profile.user.first_name} {profile.user.last_name}".strip()
    return full or profile.public_name()


class InviteForm(forms.Form):
    opportunity = forms.ModelChoiceField(
        queryset=Opportunity.objects.none(),
        error_messages={"required": "فرصت را انتخاب کنید."},
    )
    profile = forms.ModelChoiceField(
        queryset=Profile.objects.none(),
        error_messages={"required": "هنرمند را انتخاب کنید."},
    )
    message = forms.CharField(required=False)

    def __init__(self, project, owner, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["opportunity"].queryset = project.opportunities.all()
        profile_type = ContentType.objects.get_for_model(Profile)
        saved_ids = Bookmark.objects.filter(
            user_id=owner.user_id,
            content_type=profile_type,
        ).values_list("object_id", flat=True)
        self.fields["profile"].queryset = (
            Profile.objects.filter(pk__in=saved_ids)
            .exclude(pk=owner.pk)
            .select_related("user")
            .order_by("user__first_name", "user__last_name", "name")
        )
        self.fields["profile"].label_from_instance = _invite_name

    def clean_message(self):
        return self.cleaned_data["message"].strip()


class ContactForm(forms.Form):
    kind_reason = forms.ChoiceField(
        choices=CONTACT_REASONS,
        widget=ReasonPickerWidget,
        error_messages={"required": "موضوع را انتخاب کنید."},
    )
    body = forms.CharField(error_messages={"required": "پیام را بنویسید."})

    def clean_body(self):
        return self.cleaned_data["body"].strip()


class ReportForm(forms.Form):
    kind_reason = forms.ChoiceField(
        choices=REPORT_REASONS,
        widget=ReasonPickerWidget,
        error_messages={"required": "دلیل گزارش را انتخاب کنید."},
    )
    body = forms.CharField(error_messages={"required": "توضیح را بنویسید."})

    def clean_body(self):
        return self.cleaned_data["body"].strip()


class TicketReplyForm(forms.Form):
    body = forms.CharField(
        widget=forms.Textarea(attrs={"class": "field", "rows": 4}),
        error_messages={"required": "پیام را بنویسید."},
    )

    def clean_body(self):
        return self.cleaned_data["body"].strip()


class TicketForm(forms.Form):
    kind_reason = forms.ChoiceField(
        choices=TICKET_REASONS,
        widget=ReasonPickerWidget,
        error_messages={"required": "موضوع را انتخاب کنید."},
    )
    body = forms.CharField(error_messages={"required": "پیام را بنویسید."})

    def clean_body(self):
        return self.cleaned_data["body"].strip()


class DirectUploadWidget(forms.Widget):
    template_name = "widgets/direct_upload.html"

    def __init__(self, purpose, kind="photo", fixed=True, target="", attrs=None):
        self.purpose = purpose
        self.kind = kind
        self.fixed = fixed
        self.target = target
        super().__init__(attrs)

    def get_context(self, name, value, attrs):
        from django.conf import settings
        from django.urls import reverse

        context = super().get_context(name, value, attrs)
        context["widget"].update(
            {
                "purpose": self.purpose,
                "kind": self.kind,
                "fixed": self.fixed,
                "target": self.target or "",
                "start_url": reverse("media-upload-start"),
                "max_photo": settings.MEDIA_MAX_IMAGE_BYTES,
                "max_video": settings.MEDIA_MAX_VIDEO_BYTES,
                "max_audio": settings.MEDIA_MAX_AUDIO_BYTES,
            }
        )
        return context
