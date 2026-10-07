from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models


class Role(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=80)
    art_category = models.ForeignKey(
        "ArtCategory",
        on_delete=models.PROTECT,
        related_name="roles",
    )

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Province(models.TextChoices):
    EAST_AZERBAIJAN = "east-azerbaijan", "آذربایجان شرقی"
    WEST_AZERBAIJAN = "west-azerbaijan", "آذربایجان غربی"
    ARDABIL = "ardabil", "اردبیل"
    ISFAHAN = "isfahan", "اصفهان"
    ALBORZ = "alborz", "البرز"
    ILAM = "ilam", "ایلام"
    BUSHEHR = "bushehr", "بوشهر"
    TEHRAN = "tehran", "تهران"
    CHAHARMAHAL_BAKHTIARI = "chaharmahal-bakhtiari", "چهارمحال و بختیاری"
    SOUTH_KHORASAN = "south-khorasan", "خراسان جنوبی"
    RAZAVI_KHORASAN = "razavi-khorasan", "خراسان رضوی"
    NORTH_KHORASAN = "north-khorasan", "خراسان شمالی"
    KHUZESTAN = "khuzestan", "خوزستان"
    ZANJAN = "zanjan", "زنجان"
    SEMNAN = "semnan", "سمنان"
    SISTAN_BALUCHESTAN = "sistan-baluchestan", "سیستان و بلوچستان"
    FARS = "fars", "فارس"
    QAZVIN = "qazvin", "قزوین"
    QOM = "qom", "قم"
    KURDISTAN = "kurdistan", "کردستان"
    KERMAN = "kerman", "کرمان"
    KERMANSHAH = "kermanshah", "کرمانشاه"
    KOHGILUYEH_BOYER_AHMAD = "kohgiluyeh-boyer-ahmad", "کهگیلویه و بویراحمد"
    GOLESTAN = "golestan", "گلستان"
    GILAN = "gilan", "گیلان"
    LORESTAN = "lorestan", "لرستان"
    MAZANDARAN = "mazandaran", "مازندران"
    MARKAZI = "markazi", "مرکزی"
    HORMOZGAN = "hormozgan", "هرمزگان"
    HAMADAN = "hamadan", "همدان"
    YAZD = "yazd", "یزد"


class City(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=80)
    province = models.CharField(max_length=40, choices=Province.choices, blank=True)
    priority = models.PositiveSmallIntegerField(default=100)
    featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["priority", "title"]
        verbose_name_plural = "cities"

    def __str__(self):
        return self.title


class Art(models.TextChoices):
    THEATRE = "theatre", "تئاتر"
    MUSIC = "music", "موسیقی"
    FILM = "film", "سینما"
    PAINTING = "painting", "نقاشی"
    ARCHITECTURE = "architecture", "معماری"
    SCULPTURE = "sculpture", "مجسمه‌سازی"
    LITERATURE = "literature", "ادبیات"


class ArtCategory(models.Model):
    art = models.CharField(max_length=20, choices=Art.choices)
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=80)
    priority = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ["priority", "title"]
        verbose_name = "art category"
        verbose_name_plural = "art categories"

    def __str__(self):
        return self.title


class ProfileStatus(models.TextChoices):
    INDEXED = "indexed", "Indexed"
    CLAIMED = "claimed", "Claimed"


class SkillLevel(models.IntegerChoices):
    BEGINNER = 1, "Beginner"
    INTERMEDIATE = 2, "Intermediate"
    ADVANCED = 3, "Advanced"


class SkillArea(models.TextChoices):
    ACTING = "acting", "بازیگری"
    TECHNIQUE = "technique", "تکنیک بازیگری"
    SINGING = "singing", "آواز"
    DANCE = "dance", "رقص"
    COMEDY = "comedy", "کمدی"
    SPORTS = "sports", "ورزش"
    LANGUAGE = "language", "زبان و گویش"
    PRODUCTION = "production", "تولید"
    GENERAL = "general", "مهارت‌های عمومی"


class Skill(models.Model):
    group = models.CharField(max_length=20, choices=SkillArea.choices)
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=80)

    class Meta:
        ordering = ["group", "title"]

    def __str__(self):
        return self.label

    @property
    def label(self):
        group = self.get_group_display()
        if group and group != self.title:
            return f"{group}: {self.title}"
        return self.title


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
    arts = ArrayField(
        models.CharField(max_length=20, choices=Art.choices),
        default=list,
        blank=True,
        verbose_name="arts",
        help_text="Arts this person works in or is interested in.",
    )
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


class ProfileSkill(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="skill_links")
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT, related_name="profile_links")
    level = models.PositiveSmallIntegerField(choices=SkillLevel.choices, default=SkillLevel.INTERMEDIATE)

    class Meta:
        ordering = ["skill__group", "skill__title"]
        constraints = [
            models.UniqueConstraint(fields=["profile", "skill"], name="unique_profile_skill"),
        ]

    def __str__(self):
        return f"{self.profile} · {self.skill}"


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
    role = models.ForeignKey(
        Role,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="credits",
    )
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
    art_category = models.ForeignKey(
        "ArtCategory",
        on_delete=models.PROTECT,
        related_name="projects",
    )
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


class Testimonial(models.Model):
    project = models.ForeignKey(
        Project,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="testimonials",
    )
    profile = models.ForeignKey(
        Profile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="testimonials",
    )
    role = models.ForeignKey(
        Role,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="testimonials",
    )
    quote = models.TextField()
    name = models.CharField(max_length=120, blank=True)
    role_label = models.CharField(max_length=80, blank=True)
    featured = models.BooleanField(default=False)
    priority = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ["priority", "id"]

    def __str__(self):
        who = self.name
        if not who and self.profile_id:
            who = self.profile.name or self.profile.slug
        where = self.project.title if self.project_id else "عمومی"
        return f"{who or '—'} · {where}"


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
    art_category = models.ForeignKey(
        "ArtCategory",
        on_delete=models.PROTECT,
        related_name="opportunities",
    )
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
    featured = models.BooleanField(default=False)
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
