import io
import json
import shutil
import tempfile
from pathlib import Path

from django.contrib.auth.models import AnonymousUser, User
from django.core.management import call_command
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from honaryaar.admin import ProjectAdminForm
from honaryaar.catalog import _artist_dict, _project_dict
from honaryaar.media_files import MediaError, detect, process_image
from honaryaar.media_service import (
    attach_project_image,
    attach_testimonial_image,
    complete_upload,
    delete_key,
    save_profile_media,
    start_upload,
)
from honaryaar.models import (
    ArtCategory,
    MediaMigrationRecord,
    PendingUpload,
    Profile,
    ProfileMedia,
    Project,
    StorageCleanup,
    Testimonial,
    UploadStatus,
)
from honaryaar.management.commands.migrate_media import remote_allowed
from honaryaar.storage import choose_media_url, key_in_scope, merge_cors, reset_backend

MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="honaryaar-media-"))
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


def jpeg(size=(8, 4), color="red", orientation=None):
    image = Image.new("RGB", size, color)
    handle = io.BytesIO()
    if orientation:
        exif = image.getexif()
        exif[274] = orientation
        image.save(handle, format="JPEG", exif=exif)
    else:
        image.save(handle, format="JPEG")
    return handle.getvalue()


def video():
    return b"\x00\x00\x00\x18ftypisom" + b"\x00" * 16


def audio():
    return b"RIFF" + (28).to_bytes(4, "little") + b"WAVE" + b"fmt " + b"\x00" * 16


@override_settings(**SETTINGS)
class MediaStorageTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        reset_backend()
        self.user = User.objects.create_user("artist", password="secret")
        self.profile = Profile.objects.create(user=self.user, slug="artist", name="هنرمند", status="claimed")
        self.category = ArtCategory.objects.create(art="film", slug="film-feature", title="فیلم")

    def _start(self, user, purpose, kind, payload, target=None, replacing=False):
        body = {
            "purpose": purpose,
            "kind": kind,
            "size": len(payload),
            "key": "production/client-supplied.jpg",
            "filename": "ignored.mp4",
            "content_type": "text/plain",
        }
        if target is not None:
            body["target_id"] = target
        if replacing:
            body["replacing"] = True
        started = start_upload(user, body)
        upload = PendingUpload.objects.get(pk=started["id"])
        path = MEDIA_ROOT / upload.key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return upload

    def _publish_profile(self, upload, label="نمونه"):
        with self.captureOnCommitCallbacks(execute=True):
            save_profile_media(
                self.profile,
                [{"upload_id": str(upload.id), "kind": upload.requested_kind, "label": label}],
                self.user,
            )
        return self.profile.media_items.get()

    def test_server_key_and_three_profile_kinds(self):
        published = {}
        for kind, payload in (("photo", jpeg()), ("video", video()), ("audio", audio())):
            upload = self._start(self.user, "profile", kind, payload)
            self.assertTrue(upload.key.startswith(f"dev/profiles/pending/{self.user.id}/"))
            self.assertNotIn("client-supplied", upload.key)
            self.assertNotIn("production/", upload.key)
            with self.captureOnCommitCallbacks(execute=True):
                done = complete_upload(self.user, upload.id)
            self.assertEqual(done["kind"], kind)
            self.assertTrue(done["preview_url"])
            upload.refresh_from_db()
            self.assertEqual(upload.status, UploadStatus.VALIDATED)
            item = self._publish_profile(upload, label=kind)
            published[kind] = item
            self.profile.media_items.all().delete()
        self.assertEqual(set(published), {"photo", "video", "audio"})

    def test_permissions_invalid_and_oversized(self):
        stranger = User.objects.create_user("stranger", password="secret")
        upload = self._start(self.user, "profile", "photo", jpeg())
        with self.assertRaises(MediaError) as denied:
            complete_upload(stranger, upload.id)
        self.assertEqual(denied.exception.status, 403)

        with self.assertRaises(MediaError) as large:
            start_upload(self.user, {"purpose": "profile", "kind": "photo", "size": 6 * 1024 * 1024})
        self.assertIn("حجم", str(large.exception))

        bad = self._start(self.user, "profile", "photo", b"this is not an image file!!")
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(MediaError) as invalid:
                complete_upload(self.user, bad.id)
        self.assertIn("قالب", str(invalid.exception))
        bad.refresh_from_db()
        self.assertEqual(bad.status, UploadStatus.FAILED)
        self.assertFalse((MEDIA_ROOT / bad.key).exists())

        short = b"\xff\xd8\xff" + b"\x00" * 8
        mismatch = self._start(self.user, "profile", "photo", short)
        PendingUpload.objects.filter(pk=mismatch.id).update(declared_size=len(short) + 5)
        with self.assertRaises(MediaError) as sized:
            complete_upload(self.user, mismatch.id)
        self.assertIn("حجم", str(sized.exception))

        anonymous = self.client.post(
            reverse("media-upload-start"),
            data=json.dumps({"purpose": "profile", "kind": "photo", "size": 10}),
            content_type="application/json",
        )
        self.assertEqual(anonymous.status_code, 401)
        self.assertIn("وارد شوید", anonymous.json()["error"])

    def test_replacement_keeps_old_file_until_commit(self):
        old = f"dev/profiles/{self.profile.id}/old.jpg"
        (MEDIA_ROOT / old).parent.mkdir(parents=True, exist_ok=True)
        (MEDIA_ROOT / old).write_bytes(jpeg())
        item = ProfileMedia.objects.create(profile=self.profile, kind="photo", label="قدیم", position=0)
        item.file.name = old
        item.save(update_fields=["file"])
        upload = self._start(self.user, "profile", "photo", jpeg(color="blue"), replacing=True)
        with self.captureOnCommitCallbacks(execute=True):
            complete_upload(self.user, upload.id)

        with self.assertRaises(RuntimeError):
            with self.captureOnCommitCallbacks(execute=True):
                from django.db import transaction

                with transaction.atomic():
                    save_profile_media(
                        self.profile,
                        [{"media_id": item.id, "upload_id": str(upload.id), "kind": "photo", "label": "جدید"}],
                        self.user,
                    )
                    raise RuntimeError("rollback")
        item.refresh_from_db()
        self.assertEqual(item.file.name, old)
        self.assertTrue((MEDIA_ROOT / old).is_file())

        upload.refresh_from_db()
        self.assertEqual(upload.status, UploadStatus.VALIDATED)
        with self.captureOnCommitCallbacks(execute=True):
            save_profile_media(
                self.profile,
                [{"media_id": item.id, "upload_id": str(upload.id), "kind": "photo", "label": "جدید"}],
                self.user,
            )
        item.refresh_from_db()
        self.assertNotEqual(item.file.name, old)
        self.assertTrue(item.file.name.startswith(f"dev/profiles/{self.profile.id}/"))
        self.assertTrue((MEDIA_ROOT / item.file.name).is_file())
        self.assertFalse((MEDIA_ROOT / old).exists())

    def test_project_and_testimonial_images(self):
        self.client.force_login(self.user)
        page = self.client.get(reverse("me-project-new"))
        self.assertContains(page, "برای پروژهٔ جدید تصویر لازم است.")
        refused = self.client.post(
            reverse("me-project-new"),
            {"title": "بدون تصویر", "art_category": self.category.pk, "status": "draft", "summary": ""},
        )
        self.assertEqual(refused.status_code, 200)
        self.assertContains(refused, "تصویر پروژه را بارگذاری کنید.")
        self.assertFalse(Project.objects.filter(title="بدون تصویر").exists())

        upload = self._start(self.user, "project", "photo", jpeg())
        with self.captureOnCommitCallbacks(execute=True):
            complete_upload(self.user, upload.id)
        created = self.client.post(
            reverse("me-project-new"),
            {
                "title": "با تصویر",
                "art_category": self.category.pk,
                "status": "draft",
                "summary": "خلاصه",
                "image_upload": str(upload.id),
            },
        )
        self.assertEqual(created.status_code, 302)
        project = Project.objects.get(title="با تصویر")
        self.assertTrue(project.image.name.startswith(f"dev/projects/{project.id}/"))
        self.assertFalse(_project_dict(project)["image_public"])

        blank = Project.objects.create(
            slug="blank",
            title="قدیمی",
            owner=self.profile,
            art_category=self.category,
            status="casting",
        )
        card = _project_dict(blank)
        self.assertEqual(card["image_key"], "")
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        html = render_to_string(
            "components/project/project_card.html",
            {"project": card, "bookmarked_projects": []},
            request=request,
        )
        self.assertIn("mark-fallback.svg", html)

        admin_form = ProjectAdminForm(
            data={
                "slug": "admin-new",
                "title": "ادمین",
                "art_category": self.category.pk,
                "status": "draft",
                "summary": "",
                "featured": "",
                "image_upload": "",
            }
        )
        self.assertFalse(admin_form.is_valid())

        staff = User.objects.create_user("editor", password="secret", is_staff=True)
        quote = Testimonial.objects.create(project=blank, quote="عالی بود", name="سارا")
        with self.assertRaises(MediaError) as blocked:
            start_upload(self.user, {"purpose": "testimonial", "kind": "photo", "size": 20, "target_id": quote.id})
        self.assertEqual(blocked.exception.status, 403)
        portrait = self._start(staff, "testimonial", "photo", jpeg(), target=quote.id)
        with self.captureOnCommitCallbacks(execute=True):
            complete_upload(staff, portrait.id)
            attach_testimonial_image(staff, quote, portrait.id)
        quote.refresh_from_db()
        self.assertTrue(quote.image.name.startswith(f"dev/testimonials/{quote.id}/"))

        other = User.objects.create_user("other", password="secret")
        Profile.objects.create(user=other, slug="other", name="دیگری", status="claimed")
        with self.assertRaises(MediaError) as foreign:
            start_upload(
                other,
                {"purpose": "project", "kind": "photo", "size": len(jpeg()), "target_id": project.id},
            )
        self.assertEqual(foreign.exception.status, 403)

    def test_private_catalog_and_players(self):
        upload = self._start(self.user, "profile", "video", video())
        with self.captureOnCommitCallbacks(execute=True):
            complete_upload(self.user, upload.id)
            save_profile_media(
                self.profile,
                [{"upload_id": str(upload.id), "kind": "video", "label": "پشت صحنه"}],
                self.user,
            )
        item = self.profile.media_items.get()
        item.is_public = False
        item.save(update_fields=["is_public"])
        listed = _artist_dict(self.profile)["media"][0]
        self.assertEqual(listed["key"], "")
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        gallery = render_to_string(
            "components/artist/media_gallery.html",
            {"media": [_artist_dict(self.profile)["media"][0] | {"kind": "ویدیو"}]},
            request=request,
        )
        self.assertIn("پشت صحنه", gallery)
        self.assertNotIn("<video", gallery)
        public = dict(listed, key=item.file.name, public=True, public_acl=False, kind="ویدیو")
        shown = render_to_string("components/artist/media_gallery.html", {"media": [public]}, request=request)
        self.assertIn("<video", shown)
        self.assertIn("controls", shown)
        self.assertNotIn("autoplay", shown)
        letter = render_to_string(
            "components/testimonial/card.html",
            {"item": {"quote": "خوب", "name": "سارا", "role": "", "project_slug": "", "image_key": "", "image_thumb_key": "", "image_public": False, "image_public_acl": False}},
            request=request,
        )
        self.assertIn(">س<", letter)

    def test_environment_isolation_and_cleanup(self):
        outside = MEDIA_ROOT / "production" / "secret.bin"
        outside.parent.mkdir(parents=True)
        outside.write_bytes(b"keep")
        self.assertFalse(key_in_scope("production/secret.bin"))
        self.assertFalse(delete_key("production/secret.bin"))
        self.assertTrue(outside.is_file())

        stale_key = f"dev/profiles/pending/{self.user.id}/stale"
        (MEDIA_ROOT / stale_key).parent.mkdir(parents=True, exist_ok=True)
        (MEDIA_ROOT / stale_key).write_bytes(b"stale")
        PendingUpload.objects.create(
            owner=self.user,
            purpose="profile",
            target_id=self.profile.id,
            key=stale_key,
            declared_size=5,
            requested_kind="photo",
            status=UploadStatus.PENDING,
            expires_at=timezone.now() - timezone.timedelta(hours=2),
        )
        call_command("cleanup_media")
        self.assertFalse((MEDIA_ROOT / stale_key).exists())
        self.assertEqual(PendingUpload.objects.get().status, UploadStatus.ABANDONED)

    def test_migration_dry_run_failure_resume_and_rollback(self):
        item = ProfileMedia.objects.create(profile=self.profile, kind="photo", label="قدیمی")
        source = "legacy/photo.jpg"
        item.file.name = source
        item.save(update_fields=["file"])
        call_command("migrate_media", "--dry-run")
        item.refresh_from_db()
        self.assertEqual(item.file.name, source)
        self.assertFalse(MediaMigrationRecord.objects.exists())

        call_command("migrate_media")
        item.refresh_from_db()
        self.assertEqual(item.file.name, source)
        failed = MediaMigrationRecord.objects.get()
        self.assertEqual(failed.status, "failed")

        path = MEDIA_ROOT / source
        path.parent.mkdir(parents=True)
        path.write_bytes(jpeg())
        call_command("migrate_media")
        item.refresh_from_db()
        self.assertTrue(item.file.name.startswith(f"dev/profiles/{self.profile.id}/"))
        self.assertTrue(path.is_file())
        applied = MediaMigrationRecord.objects.get()
        self.assertEqual(applied.status, "applied")
        copied = MEDIA_ROOT / item.file.name
        call_command("migrate_media")
        self.assertEqual(MediaMigrationRecord.objects.get().status, "applied")
        self.assertTrue(copied.is_file())

        untouched = ProfileMedia.objects.create(profile=self.profile, kind="photo", label="بدون فایل")
        manifest = MEDIA_ROOT / "manifest.json"
        manifest.write_text(
            json.dumps(
                [
                    {
                        "model": "honaryaar.profilemedia",
                        "id": untouched.id,
                        "field": "file",
                        "source": "https://evil.example/a.jpg",
                    }
                ]
            ),
            encoding="utf-8",
        )
        call_command("migrate_media", f"--manifest={manifest}")
        untouched.refresh_from_db()
        self.assertEqual(untouched.file.name, "")
        self.assertTrue(
            MediaMigrationRecord.objects.filter(status="failed", error__icontains="untrusted").exists()
        )

        call_command("migrate_media", "--rollback")
        item.refresh_from_db()
        self.assertEqual(item.file.name, source)
        self.assertEqual(item.thumbnail.name, "")
        self.assertTrue(copied.is_file())
        self.assertFalse(remote_allowed("https://evil.example/a.jpg"))
        self.assertFalse(remote_allowed("http://169.254.169.254/latest"))

    def test_image_processing_and_cors_merge(self):
        turned = process_image(jpeg(orientation=6), "image/jpeg")
        opened = Image.open(io.BytesIO(turned[0]))
        self.assertEqual(opened.size, (4, 8))
        self.assertNotIn(274, opened.getexif())
        wide = process_image(jpeg(size=(3000, 10)), "image/jpeg")
        self.assertEqual(Image.open(io.BytesIO(wide[0])).size[0], 2560)
        small = process_image(jpeg(size=(20, 10)), "image/jpeg")
        self.assertEqual(Image.open(io.BytesIO(small[0])).size, (20, 10))
        self.assertLessEqual(max(Image.open(io.BytesIO(small[2])).size), 20)
        self.assertEqual(detect(video(), "video")[0], "video")
        self.assertEqual(detect(audio(), "audio")[0], "audio")
        with self.assertRaises(MediaError):
            detect(jpeg(), "video")

        merged = merge_cors(
            {"CORSRules": [{"AllowedOrigins": ["https://other.example"], "AllowedMethods": ["DELETE"]}]},
            {
                "CORSRules": [
                    {
                        "AllowedOrigins": ["http://127.0.0.1:8000"],
                        "AllowedMethods": ["GET", "HEAD", "PUT"],
                        "AllowedHeaders": ["content-type"],
                        "ExposeHeaders": ["ETag"],
                        "MaxAgeSeconds": 600,
                    }
                ]
            },
        )
        self.assertEqual(merged["CORSRules"][0]["AllowedMethods"], ["DELETE"])
        self.assertIn("http://127.0.0.1:8000", merged["CORSRules"][1]["AllowedOrigins"])
        self.assertEqual(
            choose_media_url(
                key="dev/projects/1/a.jpg",
                public=False,
                public_acl=True,
                base="https://cdn.example",
                endpoint="https://storage.example",
                bucket="media",
                signed="https://signed.example/a",
            ),
            "https://signed.example/a",
        )

    def test_profile_page_renders(self):
        self.client.force_login(self.user)
        page = self.client.get(reverse("me-profile") + "?edit=1")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "data-media-upload")
