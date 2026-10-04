from django.conf import settings
from django.db import models


class Role(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=80)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class City(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=80)
    province = models.CharField(max_length=80, blank=True)
    priority = models.PositiveSmallIntegerField(default=100)
    featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["priority", "title"]
        verbose_name_plural = "cities"

    def __str__(self):
        return self.title


class ArtCategory(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=80)
    active = models.BooleanField(default=False)

    class Meta:
        ordering = ["title"]
        verbose_name_plural = "art categories"

    def __str__(self):
        return self.title


class ProfileStatus(models.TextChoices):
    INDEXED = "indexed", "Indexed"
    CLAIMED = "claimed", "Claimed"


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="profile",
    )
    slug = models.SlugField(unique=True)
    first_name = models.CharField(max_length=60, blank=True)
    last_name = models.CharField(max_length=60, blank=True)
    name = models.CharField(max_length=120, blank=True)
    city = models.ForeignKey(
        "City",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="profiles",
    )
    about = models.TextField(blank=True)
    skills = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=20,
        choices=ProfileStatus.choices,
        default=ProfileStatus.INDEXED,
    )
    roles = models.ManyToManyField("Role", through="ProfileRole", related_name="profiles")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        if self.name:
            return self.name
        if self.user_id:
            return self.user.username
        return self.slug


class ProfileRole(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="profile_roles")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="profile_roles")
    is_primary = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["profile", "role"], name="unique_profile_role"),
        ]

    def __str__(self):
        return f"{self.profile} · {self.role}"


class MediaKind(models.TextChoices):
    PHOTO = "photo", "Photo"
    VIDEO = "video", "Video"
    AUDIO = "audio", "Audio"


class ProfileMedia(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="media_items")
    kind = models.CharField(max_length=20, choices=MediaKind.choices, default=MediaKind.PHOTO)
    label = models.CharField(max_length=160)

    class Meta:
        ordering = ["id"]
        verbose_name_plural = "profile media"

    def __str__(self):
        return f"{self.profile} · {self.label}"


class Credit(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="credits")
    title = models.CharField(max_length=160)
    role_name = models.CharField(max_length=120)
    year = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.title} · {self.role_name}"


class ProjectStatus(models.TextChoices):
    CASTING = "casting", "در حال جذب بازیگر"
    OPEN_CALL = "open_call", "فراخوان باز"


class Project(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=160)
    owner = models.ForeignKey(
        "Profile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_projects",
    )
    city = models.ForeignKey(
        "City",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="projects",
    )
    category = models.ForeignKey(ArtCategory, on_delete=models.PROTECT, related_name="projects")
    lead_name = models.CharField(max_length=120, blank=True)
    lead_role = models.ForeignKey(
        Role,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="led_projects",
    )
    summary = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.CASTING,
    )

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class OpportunityStatus(models.TextChoices):
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"


class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    ANY = "any", "No difference"


class Opportunity(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=160)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="opportunities")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="opportunities")
    production = models.CharField(max_length=80, blank=True)
    city = models.ForeignKey(
        "City",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="opportunities",
    )
    age_min = models.PositiveSmallIntegerField(null=True, blank=True)
    age_max = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, default=Gender.ANY)
    count = models.PositiveSmallIntegerField(default=1)
    paid = models.BooleanField(default=False)
    pay_note = models.CharField(max_length=240, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    requirements = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=20,
        choices=OpportunityStatus.choices,
        default=OpportunityStatus.OPEN,
    )

    class Meta:
        ordering = ["title"]
        verbose_name_plural = "opportunities"

    def __str__(self):
        return f"{self.project} · {self.title}"


class ApplicationStatus(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    REJECTED = "rejected", "Rejected"
    SHORTLISTED = "shortlisted", "Shortlisted"
    CONVERSATION = "conversation", "Conversation"
    MATCHED = "matched", "Matched"


class Application(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="applications")
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="applications")
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.SUBMITTED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "opportunity"],
                name="unique_application",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.profile} → {self.opportunity}"


class InviteStatus(models.TextChoices):
    SENT = "sent", "Sent"
    DECLINED = "declined", "Declined"
    ACCEPTED = "accepted", "Accepted"


class Invite(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="invites")
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="invites")
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=InviteStatus.choices,
        default=InviteStatus.SENT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["profile", "opportunity"], name="unique_invite"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.opportunity} → {self.profile}"


class MatchStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    CLOSED = "closed", "Closed"


class Match(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="matches")
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="matches")
    application = models.ForeignKey(
        Application,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="matches",
    )
    invite = models.ForeignKey(
        Invite,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="matches",
    )
    status = models.CharField(
        max_length=20,
        choices=MatchStatus.choices,
        default=MatchStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["profile", "opportunity"], name="unique_match"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.profile} × {self.opportunity}"
