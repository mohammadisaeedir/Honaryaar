from django import forms

from ejranow.accounts import code_matches, normalize_phone
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
    first_name = forms.CharField(
        max_length=60,
        error_messages={"required": "نام را وارد کنید."},
    )
    last_name = forms.CharField(
        max_length=60,
        error_messages={"required": "نام خانوادگی را وارد کنید."},
    )
    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        required=False,
        empty_label="انتخاب شهر",
    )
    about = forms.CharField(required=False)

    def clean_first_name(self):
        value = self.cleaned_data["first_name"].strip()
        if not value:
            raise forms.ValidationError("نام را وارد کنید.")
        return value

    def clean_last_name(self):
        value = self.cleaned_data["last_name"].strip()
        if not value:
            raise forms.ValidationError("نام خانوادگی را وارد کنید.")
        return value

    def clean_about(self):
        return self.cleaned_data["about"].strip()


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
