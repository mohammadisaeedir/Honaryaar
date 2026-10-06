from django import forms
from django.forms import BaseFormSet, formset_factory

from ejranow.accounts import code_matches, normalize_phone
from ejranow.labels import MEDIA_LABELS
from ejranow.models import City, Opportunity, Profile, Role


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


class ProfileForm(forms.Form):
    first_name = forms.CharField(max_length=60, required=False)
    last_name = forms.CharField(max_length=60, required=False)
    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        required=False,
        empty_label="انتخاب شهر",
    )
    about = forms.CharField(required=False)

    def clean_first_name(self):
        return (self.cleaned_data.get("first_name") or "").strip()

    def clean_last_name(self):
        return (self.cleaned_data.get("last_name") or "").strip()

    def clean_about(self):
        return self.cleaned_data["about"].strip()


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
        if cleaned.get("delete") or not any((title, role_name, year)):
            return cleaned
        if not title or not role_name:
            raise forms.ValidationError("عنوان و نقش سابقه را با هم وارد کنید.")
        return cleaned


class MediaRowForm(forms.Form):
    media_id = forms.IntegerField(required=False)
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


class ProjectOpportunityForm(forms.Form):
    title = forms.CharField(
        max_length=160,
        error_messages={"required": "نام پروژه را وارد کنید."},
    )
    city = forms.ModelChoiceField(queryset=City.objects.all(), required=False)
    summary = forms.CharField(required=False)
    opportunity_title = forms.CharField(
        max_length=160,
        error_messages={"required": "نام نقش را وارد کنید."},
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        error_messages={"required": "نقش را انتخاب کنید."},
    )
    deadline = forms.DateField(required=False, input_formats=["%Y-%m-%d"])
    description = forms.CharField(required=False)

    def clean_title(self):
        value = self.cleaned_data["title"].strip()
        if not value:
            raise forms.ValidationError("نام پروژه را وارد کنید.")
        return value

    def clean_opportunity_title(self):
        value = self.cleaned_data["opportunity_title"].strip()
        if not value:
            raise forms.ValidationError("نام نقش را وارد کنید.")
        return value

    def clean_summary(self):
        return self.cleaned_data["summary"].strip()

    def clean_description(self):
        return self.cleaned_data["description"].strip()


class OpportunityForm(forms.Form):
    title = forms.CharField(
        max_length=160,
        error_messages={"required": "نام نقش را وارد کنید."},
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        error_messages={"required": "نقش را انتخاب کنید."},
    )
    deadline = forms.DateField(required=False, input_formats=["%Y-%m-%d"])
    description = forms.CharField(required=False)

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
        self.fields["profile"].queryset = (
            Profile.objects.exclude(pk=owner.pk).exclude(name="").order_by("name")
        )

    def clean_message(self):
        return self.cleaned_data["message"].strip()
