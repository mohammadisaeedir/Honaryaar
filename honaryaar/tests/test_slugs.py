import io
import re
import shutil
import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from honaryaar.admin import OpportunityAdminForm, ProjectAdminForm
from honaryaar.media_service import complete_upload, start_upload
from honaryaar.models import ArtCategory, Opportunity, PendingUpload, Profile, Project, Role
from honaryaar.slugs import opportunity_slug, slugify, unique_slug
from honaryaar.storage import reset_backend

MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="honaryaar-slugs-"))
SETTINGS = dict(
    MEDIA_STORAGE_TESTING=True,
    MEDIA_ROOT=MEDIA_ROOT,
    MEDIA_STORAGE_PREFIX="dev",
    MEDIA_MIGRATION_HOSTS="",
    PARSPACK_ACCESS_KEY_ID="",
    PARSPACK_SECRET_ACCESS_KEY="",
    PARSPACK_ENDPOINT_URL="",
    PARSPACK_BUCKET_NAME="",
    PARSPACK_REGION_NAME="",
    PARSPACK_PUBLIC_MEDIA_BASE_URL="",
)
_RANDOM = re.compile(r"^[po]-[0-9a-f]{8,16}$")


def jpeg():
    image = Image.new("RGB", (8, 4), "red")
    handle = io.BytesIO()
    image.save(handle, format="JPEG")
    return handle.getvalue()


class SlugHelperTests(TestCase):
    def setUp(self):
        self.category = ArtCategory.objects.create(art="theatre", slug="slug-stage", title="نمایش آزمایش")
        self.role = Role.objects.get(slug="actor")

    def test_persian_title_uses_the_word_list_and_letters(self):
        self.assertEqual(slugify("فراخوان بازیگر برای فیلم کوتاه", fallback="project"), "call-actor-brai-film-short")
        self.assertEqual(slugify("سریال", fallback="project"), "series")
        self.assertLessEqual(len(slugify("نمایش " * 30, fallback="project")), 40)
        self.assertIsNone(_RANDOM.fullmatch(slugify("p-abcdef12345678", fallback="project")))

    def test_collision_adds_a_number(self):
        first = Project.objects.create(title="فراخوان بازیگر", art_category=self.category, status="draft")
        second = Project.objects.create(title="فراخوان بازیگر", art_category=self.category, status="draft")
        self.assertEqual(first.slug, "call-actor")
        self.assertEqual(second.slug, "call-actor-2")
        self.assertEqual(
            unique_slug(Project, "فراخوان بازیگر", fallback="project"),
            "call-actor-3",
        )

    def test_empty_title_falls_back(self):
        project = Project.objects.create(title="", art_category=self.category, status="draft")
        self.assertEqual(project.slug, "project")
        self.assertEqual(opportunity_slug("", role_slug="", role_title="", model=Opportunity), "opportunity")
        opening = Opportunity.objects.create(
            title="",
            project=project,
            role=self.role,
            art_category=self.category,
        )
        self.assertEqual(opening.slug, "project-actor")

    def test_existing_slug_stays(self):
        project = Project.objects.create(slug="kept-slug", title="فراخوان", art_category=self.category, status="draft")
        project.title = "سریال"
        project.save()
        self.assertEqual(project.slug, "kept-slug")

    def test_admin_save_without_slug(self):
        form = ProjectAdminForm(
            data={
                "title": "فراخوان فیلم",
                "art_category": self.category.pk,
                "status": "draft",
                "views": "0",
                "summary": "",
                "slug": "",
                "image_upload": "pending",
            }
        )
        self.assertNotIn("slug", form.errors)
        self.assertTrue(form.is_valid(), form.errors)
        project = form.save()
        self.assertEqual(project.slug, "call-film")

        opening = OpportunityAdminForm(
            data={
                "title": "بازیگر",
                "project": project.pk,
                "role": self.role.pk,
                "art_category": self.category.pk,
                "slug": "",
                "gender": "any",
                "count": 1,
                "status": "open",
                "views": "0",
                "paid": "",
                "featured": "",
                "description": "",
                "pay_note": "",
                "requirements": "[]",
                "special_conditions": [],
            }
        )
        self.assertNotIn("slug", opening.errors)
        self.assertTrue(opening.is_valid(), opening.errors)
        saved = opening.save()
        self.assertEqual(saved.slug, "call-film-actor")
        self.assertIsNone(_RANDOM.fullmatch(saved.slug))


@override_settings(**SETTINGS)
class StudioSlugTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        reset_backend()
        self.user = User.objects.create_user("slug-artist", password="secret")
        self.profile = Profile.objects.create(user=self.user, slug="slug-artist", name="هنرمند", status="claimed")
        self.category = ArtCategory.objects.create(art="film", slug="slug-film", title="فیلم آزمایش")
        self.role = Role.objects.get(slug="actor")

    def test_studio_creation_uses_a_readable_slug(self):
        self.client.force_login(self.user)
        payload = jpeg()
        started = start_upload(
            self.user,
            {"purpose": "project", "kind": "photo", "size": len(payload), "filename": "a.jpg"},
        )
        upload = PendingUpload.objects.get(pk=started["id"])
        path = MEDIA_ROOT / upload.key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        with self.captureOnCommitCallbacks(execute=True):
            complete_upload(self.user, upload.id)
        created = self.client.post(
            reverse("me-project-new"),
            {
                "title": "فراخوان سریال",
                "art_category": self.category.pk,
                "status": "draft",
                "summary": "",
                "image_upload": str(upload.id),
            },
        )
        self.assertEqual(created.status_code, 302)
        project = Project.objects.get(title="فراخوان سریال")
        self.assertEqual(project.slug, "call-series")
        self.assertIsNone(_RANDOM.fullmatch(project.slug))
        added = self.client.post(
            reverse("me-project", args=[project.slug]),
            {"action": "opportunity", "title": "بازیگر", "role": self.role.pk, "description": ""},
        )
        self.assertEqual(added.status_code, 302)
        opening = project.opportunities.get()
        self.assertEqual(opening.slug, "call-series-actor")
        self.assertIsNone(_RANDOM.fullmatch(opening.slug))
