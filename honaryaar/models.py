import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from honaryaar.storage import MediaStorage


class Role(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=80)
    group = models.CharField(max_length=80)
    art_category = models.ForeignKey(
        "ArtCategory",
        on_delete=models.PROTECT,
        related_name="roles",
    )

    class Meta:
        ordering = ["group", "title"]
        constraints = [
            models.UniqueConstraint(fields=["group", "title"], name="unique_role_group_title"),
        ]

    def __str__(self):
        if self.group:
            return f"{self.title} · {self.group}"
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
    ONE = 1, "1"
    TWO = 2, "2"
    THREE = 3, "3"
    FOUR = 4, "4"
    FIVE = 5, "5"


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


class ProfileGender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="profile",
    )
    slug = models.SlugField(
        max_length=150,
        unique=True,
        help_text="Public address. Always the same as the user's username.",
    )
    mobile = models.CharField(
        max_length=11,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Mobile",
        help_text="Phone number from registration. Separate from the username.",
    )
    name = models.CharField(max_length=120, blank=True, verbose_name="Art name")
    city = models.ForeignKey(
        "City",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="profiles",
    )
    about = models.TextField(blank=True)
    birth_date = models.DateField(null=True, blank=True, verbose_name="Birth date")
    gender = models.CharField(max_length=20, choices=ProfileGender.choices, blank=True, verbose_name="Gender")
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
    views = models.PositiveIntegerField(default=0)
    roles = models.ManyToManyField("Role", through="ProfileRole", related_name="profiles")
    list_image = models.FileField(max_length=300, blank=True, upload_to="", storage=MediaStorage())
    list_thumb = models.FileField(max_length=300, blank=True, upload_to="", storage=MediaStorage())
    list_public_acl = models.BooleanField(default=False)
    banner = models.FileField(max_length=300, blank=True, upload_to="", storage=MediaStorage())
    banner_thumb = models.FileField(max_length=300, blank=True, upload_to="", storage=MediaStorage())
    banner_public_acl = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def _assign_identity(self):
        from honaryaar.accounts import normalize_phone

        raw = (self.mobile or "").strip()
        if raw:
            phone = normalize_phone(raw)
            if not phone:
                raise ValidationError({"mobile": _("Enter a mobile number like 09123456789.")})
            self.mobile = phone
        else:
            self.mobile = None
        if self.user_id:
            username = self.user.username
            if username:
                self.slug = username

    def clean(self):
        super().clean()
        self._assign_identity()

    def save(self, *args, **kwargs):
        slug_before = self.slug
        mobile_before = self.mobile
        self._assign_identity()
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            fields = set(update_fields)
            if self.slug != slug_before:
                fields.add("slug")
            if self.mobile != mobile_before:
                fields.add("mobile")
            kwargs["update_fields"] = list(fields)
        super().save(*args, **kwargs)

    def public_name(self):
        art_name = (self.name or "").strip()
        if art_name:
            return art_name
        if self.user_id:
            full = f"{self.user.first_name} {self.user.last_name}".strip()
            if full:
                return full
            return self.user.username
        return self.slug

    def __str__(self):
        return self.public_name()


class ContactKind(models.TextChoices):
    PHONE = "phone", "Phone"
    WHATSAPP = "whatsapp", "WhatsApp"
    TELEGRAM = "telegram", "Telegram"
    INSTAGRAM = "instagram", "Instagram"
    EMAIL = "email", "Email"
    WEBSITE = "website", "Website"
    YOUTUBE = "youtube", "YouTube"
    APARAT = "aparat", "Aparat"
    TWITCH = "twitch", "Twitch"
    SPOTIFY = "spotify", "Spotify"
    SOUNDCLOUD = "soundcloud", "SoundCloud"
    IMDB = "imdb", "IMDb"
    LINKEDIN = "linkedin", "LinkedIn"
    PINTEREST = "pinterest", "Pinterest"


class ProfileContact(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="contacts")
    kind = models.CharField(max_length=20, choices=ContactKind.choices)
    value = models.CharField(max_length=200)
    is_public = models.BooleanField(default=True)
    position = models.PositiveSmallIntegerField(default=0)
    source = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["profile_id", "position", "id"]
        verbose_name = "contact"
        verbose_name_plural = "contacts"
        constraints = [
            models.UniqueConstraint(fields=["profile", "kind", "value"], name="unique_profile_contact"),
        ]
        indexes = [
            models.Index(fields=["kind"]),
        ]

    def clean(self):
        super().clean()
        from honaryaar.contacts import normalize_contact

        self.value = normalize_contact(self.kind, self.value)

    def save(self, *args, **kwargs):
        from honaryaar.contacts import normalize_contact

        self.value = normalize_contact(self.kind, self.value)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.kind}: {self.value}"


class ProfileSkill(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="skill_links")
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT, related_name="profile_links")
    level = models.PositiveSmallIntegerField(choices=SkillLevel.choices, default=SkillLevel.TWO)

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
    file = models.FileField(max_length=300, blank=True, upload_to="", storage=MediaStorage())
    thumbnail = models.FileField(max_length=300, blank=True, upload_to="", storage=MediaStorage())
    position = models.PositiveIntegerField(default=0)
    is_public = models.BooleanField(default=True)
    public_acl = models.BooleanField(default=False)

    class Meta:
        ordering = ["position", "id"]
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
    # Casting / catalogue (existing)
    DRAFT = "draft", "پیش‌نویس"
    CASTING = "casting", "در حال جذب"
    COMPLETED = "completed", "اتمام"
    # Lifecycle board (projects created via /me/projects/new-board/)
    CREATE = "create", "خلق"
    DEVELOP = "develop", "توسعه"
    PRODUCE = "produce", "تولید"
    PERFORM = "perform", "اجرا"
    AFTER = "after", "پس‌اجرا"


class PermitStatus(models.TextChoices):
    PENDING = "pending", "در حال دریافت مجوز"
    RECEIVED = "received", "دریافت شده"
    NONE = "none", "ندارد"


class ContractStatus(models.TextChoices):
    SIGNED = "signed", "دارای قرارداد"
    DRAFTING = "drafting", "در حال تنظیم قرارداد"
    NONE = "none", "بدون قرارداد / نیاز نیست"
    WAITING = "waiting", "در انتظار"


PUBLIC_PROJECT_STATUSES = (ProjectStatus.CASTING, ProjectStatus.COMPLETED)
LIFECYCLE_PROJECT_STATUS_VALUES = frozenset(
    {
        ProjectStatus.CREATE,
        ProjectStatus.DEVELOP,
        ProjectStatus.PRODUCE,
        ProjectStatus.PERFORM,
        ProjectStatus.AFTER,
    }
)
LIFECYCLE_PROJECT_STATUSES = tuple(
    (value, label)
    for value, label in ProjectStatus.choices
    if value in LIFECYCLE_PROJECT_STATUS_VALUES
)


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
    lead_name = models.CharField(max_length=120, blank=True)
    source_channel = models.CharField(max_length=60, blank=True)
    source_post_id = models.PositiveIntegerField(null=True, blank=True)
    source_url = models.URLField(max_length=300, blank=True)
    source_posted_at = models.DateTimeField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True, verbose_name="Production start")
    end_date = models.DateField(null=True, blank=True, verbose_name="Production end")
    budget = models.CharField(max_length=80, blank=True, verbose_name="Budget")
    permit = models.CharField(max_length=20, choices=PermitStatus.choices, blank=True, verbose_name="Permit")
    contract = models.CharField(max_length=20, choices=ContractStatus.choices, blank=True, verbose_name="Contract")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Publication date")
    featured = models.BooleanField(default=False, verbose_name="Featured")
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.DRAFT,
    )
    views = models.PositiveIntegerField(default=0)
    personnage_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="تعداد پرسوناژ",
    )
    image = models.FileField(max_length=300, blank=True, upload_to="", storage=MediaStorage())
    image_thumb = models.FileField(max_length=300, blank=True, upload_to="", storage=MediaStorage())
    image_public_acl = models.BooleanField(default=False)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_channel", "source_post_id"],
                condition=models.Q(source_post_id__isnull=False),
                name="unique_project_source_post",
            ),
        ]

    def save(self, *args, **kwargs):
        if not (self.slug or "").strip():
            from honaryaar.slugs import unique_slug

            self.slug = unique_slug(Project, self.title, fallback="project", exclude_pk=self.pk)
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                fields = list(update_fields)
                if "slug" not in fields:
                    fields.append("slug")
                kwargs["update_fields"] = fields
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


_PROJECT_CONTACT_KINDS = {
    ContactKind.PHONE,
    ContactKind.WHATSAPP,
    ContactKind.TELEGRAM,
    ContactKind.INSTAGRAM,
    ContactKind.EMAIL,
    ContactKind.WEBSITE,
}


class ProjectContact(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="contacts")
    kind = models.CharField(max_length=20, choices=ContactKind.choices)
    value = models.CharField(max_length=200)
    is_public = models.BooleanField(default=True)
    position = models.PositiveSmallIntegerField(default=0)
    source = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["project_id", "position", "id"]
        verbose_name = "Project contact"
        verbose_name_plural = "Project contacts"
        constraints = [
            models.UniqueConstraint(fields=["project", "kind", "value"], name="unique_project_contact"),
        ]
        indexes = [
            models.Index(fields=["kind"]),
        ]

    def clean(self):
        super().clean()
        self._normalize()

    def save(self, *args, **kwargs):
        self._normalize()
        super().save(*args, **kwargs)

    def _normalize(self):
        from honaryaar.contacts import normalize_contact

        if self.kind not in _PROJECT_CONTACT_KINDS:
            raise ValidationError({"kind": "This contact kind is not allowed on a project."})
        self.value = normalize_contact(self.kind, self.value)

    def __str__(self):
        return f"{self.project} · {self.kind}"


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
    image = models.FileField(max_length=300, blank=True, upload_to="", storage=MediaStorage())
    image_thumb = models.FileField(max_length=300, blank=True, upload_to="", storage=MediaStorage())
    image_public_acl = models.BooleanField(default=False)

    class Meta:
        ordering = ["priority", "id"]

    def __str__(self):
        who = self.name
        if not who and self.profile_id:
            who = self.profile.public_name()
        where = self.project.title if self.project_id else "عمومی"
        return f"{who or '—'} · {where}"


class UploadStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    VALIDATED = "validated", "Validated"
    PUBLISHED = "published", "Published"
    FAILED = "failed", "Failed"
    EXPIRED = "expired", "Expired"
    ABANDONED = "abandoned", "Abandoned"


class PendingUpload(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="media_uploads",
    )
    purpose = models.CharField(max_length=20)
    target_id = models.PositiveBigIntegerField(null=True, blank=True)
    key = models.CharField(max_length=300)
    thumb_key = models.CharField(max_length=300, blank=True)
    requested_kind = models.CharField(max_length=20, default="photo")
    kind = models.CharField(max_length=20, blank=True)
    content_type = models.CharField(max_length=80, blank=True)
    declared_size = models.PositiveBigIntegerField()
    actual_size = models.PositiveBigIntegerField(null=True, blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=20, choices=UploadStatus.choices, default=UploadStatus.PENDING)
    error = models.CharField(max_length=200, blank=True)
    public_acl = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "expires_at"]),
            models.Index(fields=["purpose", "target_id", "status"]),
        ]

    def __str__(self):
        return f"{self.purpose} · {self.status}"


class StorageCleanup(models.Model):
    key = models.CharField(max_length=300, unique=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.key


class MediaMigrationRecord(models.Model):
    model_label = models.CharField(max_length=80)
    object_id = models.CharField(max_length=64)
    field_name = models.CharField(max_length=40)
    source = models.TextField()
    source_hash = models.CharField(max_length=64)
    previous_value = models.TextField(blank=True)
    destination_key = models.CharField(max_length=300, blank=True)
    thumb_key = models.CharField(max_length=300, blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    byte_size = models.PositiveBigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, default="planned")
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["model_label", "object_id", "field_name", "source_hash"],
                name="unique_media_migration_source",
            )
        ]

    def __str__(self):
        return f"{self.model_label}#{self.object_id} · {self.status}"


class OpportunityStatus(models.TextChoices):
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"


class PayType(models.TextChoices):
    NEGOTIABLE = "negotiable", "توافقی"
    GIFT = "gift", "در حد هدیه"
    BOX_OFFICE = "box_office", "درصدی از گیشه"
    FIXED = "fixed", "مبلغ مشخص"


class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    ANY = "any", "No difference"


class CollaborationType(models.TextChoices):
    PROJECT_HIRE = "project_hire", "Project hire"
    CONTRACTOR = "contractor", "Contractor"
    SALARY = "salary", "Wage"
    DAILY = "daily", "Daily rate"
    HOURLY = "hourly", "Hourly"
    SESSION = "session", "Per session"
    PERCENTAGE = "percentage", "Percentage"
    PARTNERSHIP = "partnership", "Partnership"
    EQUITY = "equity", "Equity share"
    HONORARY = "honorary", "Honorary"
    INTERNSHIP = "internship", "Internship"
    VOLUNTEER = "volunteer", "Volunteer"
    LONG_TERM = "long_term", "Long-term"
    TEMPORARY = "temporary", "Temporary"


class ExperienceLevel(models.TextChoices):
    BEGINNER = "beginner", "Beginner"
    INTERMEDIATE = "intermediate", "Intermediate"
    PROFESSIONAL = "professional", "Professional"


class SpecialCondition(models.TextChoices):
    URGENT = "urgent", "Urgent"
    NO_TEST = "no_test", "No audition"
    TEST_REQUIRED = "test_required", "Audition required"
    PAID = "paid", "Paid"
    STUDENT = "student", "Student project"
    SPONSORED = "sponsored", "Sponsored"


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
    collaboration_type = models.CharField(
        max_length=20,
        choices=CollaborationType.choices,
        blank=True,
        verbose_name="Collaboration type",
    )
    experience_level = models.CharField(
        max_length=20,
        choices=ExperienceLevel.choices,
        blank=True,
        verbose_name="Experience",
    )
    special_conditions = models.JSONField(default=list, blank=True, verbose_name="Special conditions")
    count = models.PositiveSmallIntegerField(default=1)
    paid = models.BooleanField(default=False)
    pay_type = models.CharField(max_length=20, blank=True, choices=PayType.choices)
    pay_amount = models.PositiveIntegerField(null=True, blank=True)
    featured = models.BooleanField(default=False)
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
    views = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["title"]
        verbose_name_plural = "opportunities"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(paid=False, pay_type="", pay_amount__isnull=True)
                    | models.Q(
                        paid=True,
                        pay_type__in=[
                            PayType.NEGOTIABLE,
                            PayType.GIFT,
                            PayType.BOX_OFFICE,
                        ],
                        pay_amount__isnull=True,
                    )
                    | models.Q(paid=True, pay_type=PayType.FIXED, pay_amount__gt=0)
                ),
                name="opportunity_pay_consistent",
            ),
        ]

    def clean(self):
        super().clean()
        self._check_pay()

    def _check_pay(self):
        from honaryaar.pay import normalize_pay

        paid, pay_type, pay_amount, problems = normalize_pay(self.paid, self.pay_type, self.pay_amount)
        if problems:
            raise ValidationError(problems)
        self.paid = paid
        self.pay_type = pay_type
        self.pay_amount = pay_amount

    def save(self, *args, **kwargs):
        if not (self.slug or "").strip():
            from honaryaar.slugs import opportunity_slug

            project_slug = self.project.slug if self.project_id else ""
            role_slug = self.role.slug if self.role_id else ""
            role_title = self.role.title if self.role_id else self.title
            self.slug = opportunity_slug(
                project_slug,
                role_slug=role_slug,
                role_title=role_title,
                model=Opportunity,
                exclude_pk=self.pk,
            )
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                fields = list(update_fields)
                if "slug" not in fields:
                    fields.append("slug")
                kwargs["update_fields"] = fields
        self._check_pay()
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            fields = list(kwargs["update_fields"])
            for name in ("pay_type", "pay_amount"):
                if name not in fields:
                    fields.append(name)
            kwargs["update_fields"] = fields
        super().save(*args, **kwargs)

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


class ProjectMember(models.Model):
    class Permission(models.TextChoices):
        OWNER = "owner", "مالک"
        ADMIN = "admin", "مدیر"
        MEMBER = "member", "عضو"

    class InviteStatus(models.TextChoices):
        INVITED = "invited", "دعوت‌شده"
        ACCEPTED = "accepted", "پذیرفته‌شده"
        REMOVED = "removed", "حذف‌شده"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="project_memberships")
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    permission = models.CharField(
        max_length=10,
        choices=Permission.choices,
        default=Permission.MEMBER,
    )
    invite_status = models.CharField(
        max_length=10,
        choices=InviteStatus.choices,
        default=InviteStatus.INVITED,
    )
    invited_by = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_project_invites",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "عضو پروژه"
        verbose_name_plural = "اعضای پروژه"
        constraints = [
            models.UniqueConstraint(fields=["project", "profile"], name="unique_project_member"),
        ]

    def __str__(self):
        return f"{self.profile} · {self.project}"


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "انجام‌نشده"
        IN_PROGRESS = "in_progress", "در حال انجام"
        BLOCKED = "blocked", "بلاک‌شده"
        DONE = "done", "انجام‌شده"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=255, verbose_name="عنوان")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    sort_order = models.PositiveIntegerField(default=0)
    due_date = models.DateField(null=True, blank=True, verbose_name="ددلاین")
    created_by = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        verbose_name = "تسک"
        verbose_name_plural = "تسک‌ها"

    def __str__(self):
        return self.title


class TaskAssignee(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="assignees")
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="task_assignments")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["task", "profile"], name="unique_task_assignee"),
        ]

    def __str__(self):
        return f"{self.task} · {self.profile}"


class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(Profile, on_delete=models.CASCADE)
    body = models.TextField(verbose_name="متن")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.task} · {self.created_at:%Y-%m-%d}"


class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)
    file = models.FileField(max_length=300, upload_to="task-attachments/", storage=MediaStorage())
    label = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.label or self.file.name


class Event(models.Model):
    class AudienceType(models.TextChoices):
        ALL_TEAM = "all_team", "کل تیم"
        SPECIFIC = "specific", "افراد خاص"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=255, verbose_name="عنوان")
    starts_at = models.DateTimeField(verbose_name="شروع")
    ends_at = models.DateTimeField(null=True, blank=True, verbose_name="پایان")
    location = models.CharField(max_length=255, blank=True, verbose_name="مکان")
    audience_type = models.CharField(
        max_length=10,
        choices=AudienceType.choices,
        default=AudienceType.ALL_TEAM,
    )
    created_by = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at"]
        verbose_name = "رویداد"
        verbose_name_plural = "رویدادها"

    def __str__(self):
        return self.title


class EventInvitee(models.Model):
    class Attendance(models.TextChoices):
        PENDING = "pending", "در انتظار"
        CONFIRMED = "confirmed", "تأیید"
        REJECTED = "rejected", "رد"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="invitees")
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="event_invitations")
    attendance = models.CharField(
        max_length=10,
        choices=Attendance.choices,
        default=Attendance.PENDING,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "profile"], name="unique_event_invitee"),
        ]

    def __str__(self):
        return f"{self.event} · {self.profile}"


class TicketKind(models.TextChoices):
    CONTACT = "contact", "Contact"
    REPORT = "report", "Report"
    TICKET = "ticket", "Ticket"


class TicketStatus(models.TextChoices):
    OPEN = "open", "Open"
    ANSWERED = "answered", "Answered"
    CLOSED = "closed", "Closed"


class KindReason(models.TextChoices):
    GENERAL = "general", "Public"
    COLLABORATION = "collaboration", "Collaboration"
    COMPLAINT = "complaint", "Criticism and complaint"
    ACCOUNT = "account", "Account"
    PROFILE = "profile", "Profile"
    PROJECT = "project", "Project"
    OPPORTUNITY = "opportunity", "Opportunity"
    TECHNICAL = "technical", "Technical"
    WRONG = "wrong", "Wrong information"
    OWNERSHIP = "ownership", "Ownership mismatch"
    SPAM = "spam", "Spam"
    OTHER = "other", "Other"


CONTACT_REASONS = (
    (KindReason.GENERAL, "عمومی"),
    (KindReason.COLLABORATION, "همکاری"),
    (KindReason.COMPLAINT, "انتقاد و شکایت"),
    (KindReason.OTHER, "سایر"),
)
TICKET_REASONS = (
    (KindReason.ACCOUNT, "حساب کاربری"),
    (KindReason.PROFILE, "پروفایل"),
    (KindReason.PROJECT, "پروژه"),
    (KindReason.OPPORTUNITY, "فراخوان"),
    (KindReason.TECHNICAL, "مشکل فنی"),
    (KindReason.OTHER, "سایر"),
)
REPORT_REASONS = (
    (KindReason.WRONG, "اطلاعات نادرست"),
    (KindReason.OWNERSHIP, "مغایرت مالکیت"),
    (KindReason.SPAM, "اسپم"),
    (KindReason.OTHER, "سایر"),
)
KIND_REASON_VALUES = {
    TicketKind.CONTACT: {value for value, _label in CONTACT_REASONS},
    TicketKind.TICKET: {value for value, _label in TICKET_REASONS},
    TicketKind.REPORT: {value for value, _label in REPORT_REASONS},
}
REPORT_TARGET_MODELS = {"profile", "project", "opportunity"}
BOOKMARK_TARGET_MODELS = {"profile", "project", "opportunity"}


class Bookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to={"app_label": "honaryaar", "model__in": ["profile", "project", "opportunity"]},
    )
    object_id = models.PositiveBigIntegerField()
    target = GenericForeignKey("content_type", "object_id")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "content_type", "object_id"],
                name="unique_bookmark_target",
            ),
        ]

    def clean(self):
        super().clean()
        if not self.content_type_id or self.content_type.model not in BOOKMARK_TARGET_MODELS:
            raise ValidationError({"content_type": "A bookmark points at a profile, project, or opportunity."})

    def __str__(self):
        return f"{self.user} · {self.target_label() or self.object_id}"

    def target_label(self):
        item = self.target
        if item is None:
            return ""
        if hasattr(item, "public_name"):
            return item.public_name()
        return getattr(item, "title", "")


class SupportTicket(models.Model):
    kind = models.CharField(max_length=20, choices=TicketKind.choices)
    kind_reason = models.CharField(max_length=20, choices=KindReason.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="support_tickets",
    )
    content_type = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        limit_choices_to={"app_label": "honaryaar", "model__in": ["profile", "project", "opportunity"]},
    )
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")
    status = models.CharField(max_length=20, choices=TicketStatus.choices, default=TicketStatus.OPEN)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                name="support_ticket_requires_user",
                condition=models.Q(kind=TicketKind.TICKET, user__isnull=False) | ~models.Q(kind=TicketKind.TICKET),
            ),
            models.CheckConstraint(
                name="support_ticket_kind_reason",
                condition=(
                    models.Q(
                        kind=TicketKind.CONTACT,
                        kind_reason__in=[value for value, _label in CONTACT_REASONS],
                    )
                    | models.Q(
                        kind=TicketKind.TICKET,
                        kind_reason__in=[value for value, _label in TICKET_REASONS],
                    )
                    | models.Q(
                        kind=TicketKind.REPORT,
                        kind_reason__in=[value for value, _label in REPORT_REASONS],
                    )
                ),
            ),
            models.CheckConstraint(
                name="support_ticket_target",
                condition=(
                    models.Q(kind=TicketKind.REPORT, content_type__isnull=False, object_id__isnull=False)
                    | models.Q(
                        kind__in=[TicketKind.CONTACT, TicketKind.TICKET],
                        content_type__isnull=True,
                        object_id__isnull=True,
                    )
                ),
            ),
        ]

    def clean(self):
        super().clean()
        allowed = KIND_REASON_VALUES.get(self.kind, set())
        if self.kind_reason not in allowed:
            raise ValidationError({"kind_reason": _("This reason does not belong to the selected kind.")})
        has_target = bool(self.content_type_id and self.object_id)
        if self.kind == TicketKind.REPORT:
            if not has_target or self.content_type.model not in REPORT_TARGET_MODELS:
                raise ValidationError({"content_type": _("A report points at a profile, project, or opportunity.")})
        elif self.content_type_id or self.object_id:
            raise ValidationError({"content_type": _("Only a report has a target.")})
        if self.kind == TicketKind.TICKET and not self.user_id:
            raise ValidationError({"user": _("A ticket requires a user.")})

    def __str__(self):
        return f"{self.get_kind_display()} #{self.pk}"

    def target_label(self):
        item = self.target
        if item is None:
            return ""
        if hasattr(item, "public_name"):
            return item.public_name()
        return getattr(item, "title", "")

    def kind_reason_label(self):
        labels = dict(CONTACT_REASONS + TICKET_REASONS + REPORT_REASONS)
        return labels.get(self.kind_reason, self.kind_reason)

    def status_label(self):
        return {"open": "باز", "answered": "پاسخ‌داده‌شده", "closed": "بسته"}.get(self.status, self.status)

    def latest_body(self):
        cached = getattr(self, "_prefetched_objects_cache", {}).get("messages")
        if cached is not None:
            rows = list(cached)
            return rows[-1].body if rows else self.body
        last = self.messages.order_by("-created_at").first()
        return last.body if last else self.body


class TicketMessage(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ticket_messages",
    )
    from_staff = models.BooleanField(default=False)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]

    def __str__(self):
        return f"{self.ticket_id} · {self.created_at:%Y-%m-%d %H:%M}"

    def sender_name(self):
        user = self.author
        if user is None:
            return ""
        name = f"{user.first_name} {user.last_name}".strip()
        return name or user.get_username()
