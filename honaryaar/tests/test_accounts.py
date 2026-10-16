import csv
import io
import json
import re

from django.contrib.auth.models import Permission, User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from honaryaar.accounts import ensure_profile, user_for_phone
from honaryaar.admin import HonaryaarUserChangeForm
from honaryaar.models import Profile


def catalog_json(page, element_id):
    html = page.content.decode()
    marker = f'id="{element_id}" type="application/json">'
    start = html.index(marker) + len(marker)
    return json.loads(html[start:html.index("</script>", start)])


class FilterPreviewTests(TestCase):
    def test_long_choice_lists_keep_five_and_count_the_rest(self):
        from honaryaar.catalog import choice_group

        group = choice_group("city", "شهر", [(str(i), f"شهر {i}") for i in range(12)], ["9"])
        self.assertTrue(group["find"])
        self.assertEqual(group["rest"], 7)
        self.assertEqual(sum(option["shown"] for option in group["options"]), 5)
        short = choice_group("gender", "جنسیت", [("male", "مرد"), ("female", "زن")], "")
        self.assertFalse(short["find"])
        self.assertEqual(short["rest"], 0)
        roles = choice_group(
            "role",
            "نقش",
            [("actor", "بازیگر", "اجرا"), ("writer", "نویسنده", "متن")],
            [],
        )
        self.assertEqual([item["name"] for item in roles["categories"]], ["اجرا", "متن"])
        self.assertEqual(roles["categories"][0]["options"][0]["label"], "بازیگر")


class BookmarkFilterRoleTests(TestCase):
    def test_saved_filter_shows_the_primary_role(self):
        from django.contrib.contenttypes.models import ContentType

        from honaryaar.models import ArtCategory, Bookmark, ProfileRole, Role

        viewer = user_for_phone("09120000111")
        artist = user_for_phone("09120000112")
        artist.first_name = "سارا"
        artist.last_name = "محمدی"
        artist.save()
        category = ArtCategory.objects.create(art="theatre", slug="filter-role-art", title="تئاتر")
        main = Role.objects.create(slug="filter-lead", title="نقش اصلی فیلتر", group="فیلتر", art_category=category)
        other = Role.objects.create(slug="filter-extra", title="نقش فرعی فیلتر", group="فیلتر دیگر", art_category=category)
        ProfileRole.objects.create(profile=artist.profile, role=other, is_primary=False)
        ProfileRole.objects.create(profile=artist.profile, role=main, is_primary=True)
        Bookmark.objects.create(
            user=viewer,
            content_type=ContentType.objects.get_for_model(artist.profile),
            object_id=artist.profile.pk,
        )
        self.client.force_login(viewer)
        page = self.client.get(reverse("artists"))
        self.assertContains(page, "سارا محمدی")
        self.assertContains(page, 'class="saved-list__role">نقش اصلی فیلتر')
        self.assertNotContains(page, 'class="saved-list__role">نقش فرعی فیلتر')


class ProductionDataSwitchTests(TestCase):
    def test_production_database_is_read_only(self):
        from django.core.exceptions import ImproperlyConfigured

        from honaryaar.settings import production_database

        params = production_database("postgresql://user:secret@ep-example.neon.tech/honaryaar?sslmode=require")
        self.assertEqual(params["HOST"], "ep-example.neon.tech")
        self.assertEqual(params["NAME"], "honaryaar")
        self.assertIn("default_transaction_read_only=on", params["OPTIONS"]["options"])
        with self.assertRaises(ImproperlyConfigured):
            production_database("localhost")

    def test_account_menu_switches_live_data_for_superuser(self):
        from unittest.mock import patch

        from django.contrib.sessions.models import Session

        from honaryaar.data_source import ProductionPreviewRouter, _preview
        from honaryaar.models import Profile

        router = ProductionPreviewRouter()
        self.assertIsNone(router.db_for_read(Profile))
        superuser = User.objects.create_superuser("data-switch", "switch@example.com", "secret-pass")
        self.client.force_login(superuser)
        menu = self.client.get(reverse("admin:index"))
        self.assertContains(menu, reverse("admin-data-source"))
        blocked = self.client.post(reverse("admin-data-source"), {"source": "production", "next": "/admin/"})
        self.assertEqual(blocked.status_code, 302)
        self.assertNotIn("data_source", self.client.session)

        with patch("honaryaar.data_source.production_configured", return_value=True):
            switched = self.client.post(
                reverse("admin-data-source"),
                {"source": "production", "next": "/admin/honaryaar/profile/"},
            )
            marker = _preview.set(True)
            try:
                self.assertEqual(router.db_for_read(Profile), "production")
                self.assertEqual(router.db_for_write(Profile), "production")
                self.assertEqual(router.db_for_read(Session), "default")
                self.assertEqual(router.db_for_write(Session), "default")
            finally:
                _preview.reset(marker)
        self.assertRedirects(switched, "/admin/honaryaar/profile/", fetch_redirect_response=False)
        self.assertEqual(self.client.session["data_source"], "production")

        staff = User.objects.create_user("data-staff", "data-staff@example.com", "secret-pass", is_staff=True)
        self.client.force_login(staff)
        hidden = self.client.get(reverse("admin:index"))
        self.assertNotContains(hidden, reverse("admin-data-source"))
        denied = self.client.post(reverse("admin-data-source"), {"source": "production"})
        self.assertEqual(denied.status_code, 403)


class AdminLanguageTests(TestCase):
    def test_persian_turns_the_admin_rtl(self):
        user = User.objects.create_superuser("lang-switch", "lang@example.com", "secret-pass")
        self.client.force_login(user)
        menu = self.client.get(reverse("admin:index"))
        self.assertContains(menu, reverse("admin-language"))
        self.assertContains(menu, "فارسی")
        self.assertContains(menu, 'dir="ltr"')

        switched = self.client.post(reverse("admin-language"), {"language": "fa", "next": "/admin/"})
        self.assertRedirects(switched, "/admin/", fetch_redirect_response=False)
        self.assertEqual(self.client.session["admin_lang"], "fa")
        page = self.client.get(reverse("admin:index"))
        self.assertContains(page, 'dir="rtl"')
        self.assertContains(page, "پیشخوان")
        self.assertContains(page, "شهرها")
        self.assertContains(page, "دسته‌های هنری")
        self.assertContains(page, "روشن")
        self.assertNotContains(page, "Basic data")
        cities = self.client.get(reverse("admin:honaryaar_city_changelist"))
        self.assertContains(cities, "انتخاب شهر برای ویرایش")
        self.assertContains(cities, "حذف شهر انتخاب‌شده")
        self.assertNotContains(cities, "های انتخاب شده")

        back = self.client.post(reverse("admin-language"), {"language": "en", "next": "/admin/"})
        self.assertRedirects(back, "/admin/", fetch_redirect_response=False)
        self.assertNotIn("admin_lang", self.client.session)
        restored = self.client.get(reverse("admin:index"))
        self.assertContains(restored, 'dir="ltr"')


class PageViewTests(TestCase):
    def test_opening_a_profile_counts_once_per_session(self):
        from honaryaar.accounts import ensure_profile

        from honaryaar.models import Profile

        user = User.objects.create_user("page-view", "page-view@example.com", "secret-pass")
        profile = ensure_profile(user)
        page = self.client.get(reverse("artist", args=[profile.slug]))
        self.assertContains(page, "بار مشاهده شده است")
        self.assertContains(page, 'dir="ltr"')
        profile.refresh_from_db()
        self.assertEqual(profile.views, 1)
        self.client.get(reverse("artist", args=[profile.slug]))
        profile.refresh_from_db()
        self.assertEqual(profile.views, 1)
        self.assertEqual(Profile.objects.get(pk=profile.pk).views, 1)


class AdminTableOrderTests(TestCase):
    def test_changelists_show_id_and_newest_first(self):
        from django.contrib import admin
        from django.test import RequestFactory

        from honaryaar.admin import CreditInline
        from honaryaar.models import City, Profile

        user = User.objects.create_superuser("table-order", "table@example.com", "secret-pass")
        request = RequestFactory().get("/admin/")
        request.user = user
        for model, model_admin in admin.site._registry.items():
            self.assertEqual(model_admin.get_list_display(request)[0], "row_id", model._meta.label)
            self.assertEqual(model_admin.get_ordering(request), ("-pk",), model._meta.label)

        inline = CreditInline(Profile, admin.site)
        self.assertEqual(inline.get_fields(request)[0], "row_id")
        self.assertEqual(inline.get_ordering(request), ("-pk",))

        self.client.force_login(user)
        older = City.objects.create(title="Older city", slug="older-city", priority=1)
        newer = City.objects.create(title="Newer city", slug="newer-city", priority=100)
        page = self.client.get(reverse("admin:honaryaar_city_changelist"))
        html = page.content.decode()
        self.assertContains(page, "column-row_id")
        self.assertLess(html.index(f'value="{newer.pk}"'), html.index(f'value="{older.pk}"'))


class DocumentErdTests(TestCase):
    def test_erd_is_listed_and_built_from_current_models(self):
        from honaryaar.erd import render_erd

        page = render_erd()
        self.assertIn("ProfileContact", page)
        self.assertIn('Profile ||--o{ ProfileContact : "profile"', page)
        self.assertIn("PendingUpload", page)
        self.assertIn("کلید عمومی", page)

        user = User.objects.create_superuser("erd-reader", "erd@example.com", "secret-pass")
        self.client.force_login(user)
        listing = self.client.get(reverse("admin-documents"))
        self.assertContains(listing, "Entity relationship")
        self.assertContains(listing, reverse("admin-document", args=["erd"]))
        document = self.client.get(reverse("admin-document", args=["erd"]))
        self.assertContains(document, "ProfileContact")

        other = User.objects.create_user("erd-staff", "staff-erd@example.com", "secret-pass", is_staff=True)
        self.client.force_login(other)
        denied = self.client.get(reverse("admin-documents"))
        self.assertEqual(denied.status_code, 403)


class AccountIdentityTests(TestCase):
    def test_registration_stores_phone_apart_from_username(self):
        response = self.client.post(reverse("login"), {"phone": "۰۹۱۲۳۴۵۶۷۸۹"})
        self.assertRedirects(response, reverse("login-code"))
        response = self.client.post(reverse("login-code"), {"code": "6789"})
        self.assertRedirects(response, reverse("home"))

        user = User.objects.get(profile__mobile="09123456789")
        self.assertRegex(user.username, r"^[a-z0-9]{5}$")
        self.assertNotIn("-", user.username)
        self.assertEqual(user.profile.slug, user.username)
        self.assertFalse(user.has_usable_password())

        again = user_for_phone("09123456789")
        self.assertEqual(again.pk, user.pk)
        self.assertEqual(Profile.objects.filter(mobile="09123456789").count(), 1)

    def test_each_phone_gets_its_own_account(self):
        first = user_for_phone("09120000000")
        second = user_for_phone("09120000001")
        self.assertNotEqual(first.pk, second.pk)
        self.assertNotEqual(first.username, second.username)
        self.assertEqual(first.profile.mobile, "09120000000")
        self.assertEqual(second.profile.mobile, "09120000001")

    def test_mobile_stays_unique(self):
        user_for_phone("09121111111")
        other = User.objects.create_user("other-name")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Profile.objects.create(user=other, slug="other-name", mobile="09121111111", status="claimed")

    def test_renaming_username_moves_the_profile_address(self):
        user = user_for_phone("09122222222")
        user.username = "reza-stage"
        user.save()
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.slug, "reza-stage")

    def test_profile_without_a_phone_keeps_username_as_address(self):
        user = User.objects.create_user("niloofar")
        profile = ensure_profile(user)
        self.assertEqual(profile.slug, "niloofar")
        self.assertIsNone(profile.mobile)

    def test_admin_user_change_accepts_the_current_username(self):
        user = user_for_phone("09126667788")
        form = HonaryaarUserChangeForm(instance=user)
        form.cleaned_data = {"username": user.username}
        self.assertEqual(form.clean_username(), user.username)

        staff = User.objects.create_superuser("staff2", "staff2@example.com", "secret")
        self.client.force_login(staff)
        response = self.client.post(
            reverse("admin:auth_user_change", args=[user.pk]),
            {
                "username": user.username,
                "first_name": "Ali",
                "last_name": "",
                "email": "",
                "is_active": "on",
                "date_joined_0": "2026-01-01",
                "date_joined_1": "12:00:00",
            },
        )
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Ali")
        self.assertEqual(user.profile.slug, user.username)

    def test_gender_is_two_icon_buttons(self):
        user = user_for_phone("09127778899")
        self.client.force_login(user)
        page = self.client.get(reverse("me-profile") + "?edit=about")
        self.assertContains(page, "gender-male")
        self.assertContains(page, "gender-female")
        self.assertContains(page, "مرد")
        self.assertContains(page, "زن")
        self.assertNotContains(page, 'class="field field-select" name="gender"')
        saved = self.client.post(
            reverse("me-profile"),
            {
                "first_name": "",
                "last_name": "",
                "name": "",
                "city": "",
                "about": "",
                "birth_date": "",
                "gender": "female",
                "role-TOTAL_FORMS": "0",
                "role-INITIAL_FORMS": "0",
                "role-MIN_NUM_FORMS": "0",
                "role-MAX_NUM_FORMS": "1000",
                "credit-TOTAL_FORMS": "0",
                "credit-INITIAL_FORMS": "0",
                "credit-MIN_NUM_FORMS": "0",
                "credit-MAX_NUM_FORMS": "1000",
                "media-TOTAL_FORMS": "0",
                "media-INITIAL_FORMS": "0",
                "media-MIN_NUM_FORMS": "0",
                "media-MAX_NUM_FORMS": "1000",
            },
        )
        self.assertEqual(saved.status_code, 302)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.gender, "female")

        staff = User.objects.create_superuser("staff3", "staff3@example.com", "secret")
        self.client.force_login(staff)
        admin_page = self.client.get(reverse("admin:honaryaar_profile_change", args=[user.profile.pk]))
        self.assertContains(admin_page, "gender-male")
        self.assertContains(admin_page, "gender-female")

    def test_skill_picker_searches_and_saves_a_level(self):
        from honaryaar.models import ProfileSkill, Skill

        user = user_for_phone("09128889900")
        skill = Skill.objects.filter(group="acting").first()
        self.assertIsNotNone(skill)
        self.client.force_login(user)
        page = self.client.get(reverse("me-profile") + "?edit=skills")
        self.assertContains(page, "data-skill-picker")
        self.assertContains(page, "data-levels=\"5\"")
        self.assertContains(page, "data-search-typewriter")
        self.assertContains(page, "مثلاً: گیتار")
        self.assertContains(page, "افزودن مهارت")
        self.assertIn(
            {"id": skill.pk, "title": skill.title, "category": skill.get_group_display()},
            catalog_json(page, "skill-catalog"),
        )
        self.assertNotContains(page, f"{skill.get_group_display()}: {skill.title}")
        self.assertNotContains(page, "skill-cats")
        saved = self.client.post(
            reverse("me-profile"),
            {
                "first_name": "",
                "last_name": "",
                "name": "",
                "city": "",
                "about": "",
                "birth_date": "",
                "gender": "",
                "skill_picker": "1",
                f"skill-{skill.pk}": "5",
                "role-TOTAL_FORMS": "0",
                "role-INITIAL_FORMS": "0",
                "role-MIN_NUM_FORMS": "0",
                "role-MAX_NUM_FORMS": "1000",
                "credit-TOTAL_FORMS": "0",
                "credit-INITIAL_FORMS": "0",
                "credit-MIN_NUM_FORMS": "0",
                "credit-MAX_NUM_FORMS": "1000",
                "media-TOTAL_FORMS": "0",
                "media-INITIAL_FORMS": "0",
                "media-MIN_NUM_FORMS": "0",
                "media-MAX_NUM_FORMS": "1000",
            },
        )
        self.assertEqual(saved.status_code, 302)
        stored = ProfileSkill.objects.get(profile=user.profile, skill=skill)
        self.assertEqual(stored.level, 5)

        staff = User.objects.create_superuser("staff4", "staff4@example.com", "secret")
        self.client.force_login(staff)
        admin_page = self.client.get(reverse("admin:honaryaar_profile_change", args=[user.profile.pk]))
        self.assertContains(admin_page, "data-inline-modal")
        self.assertContains(admin_page, "skill_links-TOTAL_FORMS")
        self.assertContains(admin_page, skill.title)
        self.assertNotContains(admin_page, "data-skill-picker")
        admin_data = {
            "user": user.pk,
            "name": "",
            "mobile": user.profile.mobile,
            "city": "",
            "about": "",
            "birth_date": "",
            "gender": "",
            "status": user.profile.status,
            "list_upload": "",
            "banner_upload": "",
            "skill_links-TOTAL_FORMS": "1",
            "skill_links-INITIAL_FORMS": "1",
            "skill_links-MIN_NUM_FORMS": "0",
            "skill_links-MAX_NUM_FORMS": "1000",
            "skill_links-0-id": str(stored.pk),
            "skill_links-0-skill": str(skill.pk),
            "skill_links-0-level": "4",
            "_save": "Save",
        }
        for prefix in re.findall(r'name="([A-Za-z0-9_]+)-TOTAL_FORMS"', admin_page.content.decode()):
            if prefix == "skill_links":
                continue
            admin_data[f"{prefix}-TOTAL_FORMS"] = "0"
            admin_data[f"{prefix}-INITIAL_FORMS"] = "0"
            admin_data[f"{prefix}-MIN_NUM_FORMS"] = "0"
            admin_data[f"{prefix}-MAX_NUM_FORMS"] = "1000"
        admin_saved = self.client.post(
            reverse("admin:honaryaar_profile_change", args=[user.profile.pk]),
            admin_data,
        )
        if admin_saved.status_code != 302:
            content = admin_saved.content.decode()
            errors = re.findall(r'class="errorlist[^"]*">(.*?)</ul>', content, re.S)
            self.fail(f"status {admin_saved.status_code} errors {errors[:12]}")
        stored.refresh_from_db()
        self.assertEqual(stored.level, 4)

    def test_role_picker_searches_and_saves_a_primary_role(self):
        from honaryaar.models import ProfileRole, Role

        user = user_for_phone("09126667788")
        first = Role.objects.order_by("group", "title").first()
        second = Role.objects.exclude(group=first.group).order_by("group", "title").first()
        self.client.force_login(user)
        page = self.client.get(reverse("me-profile") + "?edit=roles")
        self.assertContains(page, "data-role-picker")
        self.assertContains(page, "data-search-typewriter")
        self.assertContains(page, "مثلاً: بازیگر")
        self.assertContains(page, "افزودن نقش")
        self.assertIn(
            {"id": first.pk, "title": first.title, "category": first.group},
            catalog_json(page, "role-catalog"),
        )
        self.assertNotContains(page, 'data-repeat-add="role"')
        self.assertNotContains(page, 'id="role-rows"')
        saved = self.client.post(
            reverse("me-profile"),
            {
                "first_name": "",
                "last_name": "",
                "name": "",
                "city": "",
                "about": "",
                "birth_date": "",
                "gender": "",
                "role_picker": "1",
                f"role-{first.pk}": "1",
                f"role-{second.pk}": "1",
                "role_primary": str(second.pk),
                "credit-TOTAL_FORMS": "0",
                "credit-INITIAL_FORMS": "0",
                "credit-MIN_NUM_FORMS": "0",
                "credit-MAX_NUM_FORMS": "1000",
                "media-TOTAL_FORMS": "0",
                "media-INITIAL_FORMS": "0",
                "media-MIN_NUM_FORMS": "0",
                "media-MAX_NUM_FORMS": "1000",
            },
        )
        self.assertEqual(saved.status_code, 302)
        stored = ProfileRole.objects.get(profile=user.profile, role=second)
        self.assertTrue(stored.is_primary)
        self.assertFalse(ProfileRole.objects.get(profile=user.profile, role=first).is_primary)

        staff = User.objects.create_superuser("staff5", "staff5@example.com", "secret")
        self.client.force_login(staff)
        admin_page = self.client.get(reverse("admin:honaryaar_profile_change", args=[user.profile.pk]))
        self.assertContains(admin_page, "data-inline-modal")
        self.assertContains(admin_page, "profile_roles-TOTAL_FORMS")
        self.assertContains(admin_page, second.title)
        self.assertNotContains(admin_page, "data-role-picker")
        links = list(ProfileRole.objects.filter(profile=user.profile).order_by("pk"))
        admin_data = {
            "user": user.pk,
            "name": "",
            "mobile": user.profile.mobile,
            "city": "",
            "about": "",
            "birth_date": "",
            "gender": "",
            "status": user.profile.status,
            "list_upload": "",
            "banner_upload": "",
            "profile_roles-TOTAL_FORMS": str(len(links)),
            "profile_roles-INITIAL_FORMS": str(len(links)),
            "profile_roles-MIN_NUM_FORMS": "0",
            "profile_roles-MAX_NUM_FORMS": "1000",
            "_save": "Save",
        }
        for index, link in enumerate(links):
            admin_data[f"profile_roles-{index}-id"] = str(link.pk)
            admin_data[f"profile_roles-{index}-role"] = str(link.role_id)
            if link.role_id == first.pk:
                admin_data[f"profile_roles-{index}-is_primary"] = "on"
            else:
                admin_data[f"profile_roles-{index}-DELETE"] = "on"
        for prefix in re.findall(r'name="([A-Za-z0-9_]+)-TOTAL_FORMS"', admin_page.content.decode()):
            if prefix == "profile_roles":
                continue
            admin_data[f"{prefix}-TOTAL_FORMS"] = "0"
            admin_data[f"{prefix}-INITIAL_FORMS"] = "0"
            admin_data[f"{prefix}-MIN_NUM_FORMS"] = "0"
            admin_data[f"{prefix}-MAX_NUM_FORMS"] = "1000"
        admin_saved = self.client.post(
            reverse("admin:honaryaar_profile_change", args=[user.profile.pk]),
            admin_data,
        )
        if admin_saved.status_code != 302:
            content = admin_saved.content.decode()
            errors = re.findall(r'class="errorlist[^"]*">(.*?)</ul>', content, re.S)
            self.fail(f"status {admin_saved.status_code} errors {errors[:12]}")
        self.assertFalse(ProfileRole.objects.filter(profile=user.profile, role=second).exists())
        self.assertTrue(ProfileRole.objects.get(profile=user.profile, role=first).is_primary)

    def test_profile_edit_offers_image_upload(self):
        user = user_for_phone("09125556677")
        user.first_name = "سارا"
        user.save(update_fields=["first_name"])
        self.client.force_login(user)
        response = self.client.get(reverse("me-profile"))
        self.assertContains(response, 'data-purpose="profile_list"')
        self.assertContains(response, 'data-purpose="profile_banner"')
        self.assertContains(response, 'aria-label="ویرایش بنر"')
        self.assertContains(response, 'aria-label="ویرایش تصویر اصلی"')
        self.assertContains(response, 'aria-label="ویرایش اطلاعات"')
        self.assertContains(response, "اطلاعات اصلی")
        opened = self.client.get(reverse("me-profile") + "?edit=1")
        self.assertContains(opened, "info: true")
        saved = self.client.post(
            reverse("me-profile"),
            {"section": "hero", "first_name": "آوا", "last_name": "راد", "name": "آوا", "arts": "theatre"},
        )
        self.assertEqual(saved.status_code, 302)
        user.refresh_from_db()
        user.profile.refresh_from_db()
        self.assertEqual(user.first_name, "آوا")
        self.assertEqual(user.last_name, "راد")
        self.assertEqual(user.profile.name, "آوا")
        self.assertEqual(user.profile.arts, ["theatre"])

    def test_profile_page_is_one_layout_with_section_edits(self):
        user = user_for_phone("09127770011")
        user.first_name = "نرگس"
        user.last_name = "کریمی"
        user.save(update_fields=["first_name", "last_name"])
        user.profile.name = "نام هنری"
        user.profile.about = "چند خط"
        user.profile.arts = ["film"]
        user.profile.save(update_fields=["name", "about", "arts"])
        self.client.force_login(user)
        page = self.client.get(reverse("me-profile"))
        self.assertContains(page, "me-hero")
        self.assertContains(page, "me-grid")
        self.assertContains(page, "نرگس")
        self.assertContains(page, "نام هنری")
        self.assertContains(page, "سینما")
        self.assertContains(page, "اطلاعات تماس")
        self.assertNotContains(page, "profile-tabs")
        self.assertContains(page, "sheet = 'about'")
        saved = self.client.post(
            reverse("me-profile"),
            {"section": "about", "city": "", "about": "متن تازه", "birth_date": "", "gender": "female"},
        )
        self.assertEqual(saved.status_code, 302)
        user.refresh_from_db()
        user.profile.refresh_from_db()
        self.assertEqual(user.first_name, "نرگس")
        self.assertEqual(user.profile.name, "نام هنری")
        self.assertEqual(user.profile.arts, ["film"])
        self.assertEqual(user.profile.about, "متن تازه")
        self.assertEqual(user.profile.gender, "female")

    def test_profile_files_use_edit_and_delete_icons(self):
        from honaryaar.models import ProfileMedia

        user = user_for_phone("09120002233")
        item = ProfileMedia.objects.create(profile=user.profile, kind="photo", label="نمونه", is_public=True)
        self.client.force_login(user)
        page = self.client.get(reverse("me-profile"))
        self.assertContains(page, 'aria-label="افزودن فایل"')
        self.assertContains(page, 'aria-label="ویرایش"')
        self.assertContains(page, 'aria-label="حذف"')
        self.assertNotContains(page, "انتخاب فایل")
        self.assertNotContains(page, ">حذف تصویر<")
        self.assertNotContains(page, 'type="checkbox" name="list_remove"')
        self.assertContains(page, "نمونه")
        self.assertContains(page, ">عنوان<")
        self.assertContains(page, ">عمومی<")
        self.assertContains(page, 'aria-label="عمومی"')
        self.assertContains(page, "data-media-editor")
        renamed = self.client.post(
            reverse("me-profile"),
            {"section": "media", "media_action": "replace", "media_id": item.pk, "label": "پشت صحنه"},
        )
        self.assertEqual(renamed.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.label, "پشت صحنه")
        hidden = self.client.post(
            reverse("me-profile"),
            {"section": "media", "media_action": "visibility", "media_id": item.pk, "is_public": "0"},
        )
        self.assertEqual(hidden.status_code, 302)
        item.refresh_from_db()
        self.assertFalse(item.is_public)
        removed = self.client.post(
            reverse("me-profile"),
            {"section": "media", "media_action": "delete", "media_id": item.pk},
        )
        self.assertEqual(removed.status_code, 302)
        self.assertFalse(ProfileMedia.objects.filter(pk=item.pk).exists())

    def test_account_pages_show_the_mobile_number(self):
        user = user_for_phone("09123334455")
        self.client.force_login(user)
        response = self.client.get(reverse("me-profile"))
        self.assertContains(response, "۰۹۱۲ ۳۳۳ ۴۴۵۵")
        self.assertNotContains(response, "09123334455")

    def test_admin_list_separates_username_and_mobile(self):
        user = user_for_phone("09124445566")
        staff = User.objects.create_superuser("staff", "staff@example.com", "secret")
        self.client.force_login(staff)
        response = self.client.get(reverse("admin:honaryaar_profile_changelist"))
        self.assertContains(response, user.username)
        self.assertContains(response, "09124445566")
        self.assertNotEqual(user.username, "09124445566")

    def test_profile_contacts_save_from_the_table_and_list_as_a_count(self):
        from honaryaar.models import ProfileContact

        user = user_for_phone("09120001122")
        self.client.force_login(user)
        page = self.client.get(reverse("me-profile") + "?edit=contacts")
        self.assertContains(page, "data-contact-picker")
        self.assertContains(page, "data-sheet-add=\"contact\"")
        self.assertContains(page, "هنوز راه تماسی ثبت نشده.")
        saved = self.client.post(
            reverse("me-profile"),
            {
                "section": "contacts",
                "contact_picker": "1",
                "contact-0-kind": "telegram",
                "contact-0-value": "https://t.me/honar_name",
                "contact-0-public": "1",
            },
        )
        self.assertRedirects(saved, reverse("me-profile") + "?edit=contacts")
        stored = ProfileContact.objects.get(profile=user.profile)
        self.assertEqual(stored.kind, "telegram")
        self.assertEqual(stored.value, "honar_name")
        self.assertTrue(stored.is_public)
        listed = self.client.get(reverse("me-profile"))
        self.assertContains(listed, "تلگرام")
        self.assertContains(listed, "@honar_name")
        self.assertNotContains(listed, "به‌زودی")
        rejected = self.client.post(
            reverse("me-profile"),
            {
                "section": "contacts",
                "contact_picker": "1",
                "contact-0-kind": "email",
                "contact-0-value": "not-an-email",
                "contact-0-public": "1",
            },
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertContains(rejected, "مقدار این راه تماس درست نیست.")
        self.assertTrue(ProfileContact.objects.filter(profile=user.profile, kind="telegram").exists())

        staff = User.objects.create_superuser("staff-contacts", "staff-contacts@example.com", "secret")
        self.client.force_login(staff)
        listing = self.client.get(reverse("admin:honaryaar_profile_changelist"))
        self.assertContains(listing, ">1</a>")
        self.assertNotContains(listing, "Contacts (")
        change = self.client.get(reverse("admin:honaryaar_profile_change", args=[user.profile.pk]))
        self.assertContains(change, "contacts-TOTAL_FORMS")
        self.assertContains(change, "data-inline-modal")
        self.assertContains(change, "profile_roles-TOTAL_FORMS")
        self.assertContains(change, "skill_links-TOTAL_FORMS")
        self.assertNotContains(change, "data-contact-picker")
        self.assertContains(change, "honar_name")


class AdminCsvExportTests(TestCase):
    def test_superuser_can_export_selected_or_all_rows(self):
        first = user_for_phone("09120001122")
        second = user_for_phone("09120001133")
        first.profile.name = "Export One"
        first.profile.save(update_fields=["name"])
        second.profile.name = "Export Two"
        second.profile.save(update_fields=["name"])
        staff = User.objects.create_superuser("export-staff", "export@example.com", "secret")
        self.client.force_login(staff)
        url = reverse("admin:honaryaar_profile_changelist")
        page = self.client.get(url)
        self.assertContains(page, "Export to CSV")
        self.assertContains(page, "Delete selected")

        selected = self.client.post(
            url,
            {"action": "export_csv", "_selected_action": [first.profile.pk]},
        )
        self.assertEqual(selected["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("profile.csv", selected["Content-Disposition"])
        rows = list(csv.reader(io.StringIO(selected.content.decode("utf-8-sig"))))
        self.assertIn("Art name", rows[0])
        self.assertNotIn("password", [cell.lower() for cell in rows[0]])
        body = "\n".join(",".join(row) for row in rows)
        self.assertIn("Export One", body)
        self.assertNotIn("Export Two", body)

        everything = self.client.post(
            url,
            {"action": "export_csv", "select_across": "1", "_selected_action": [first.profile.pk]},
        )
        all_rows = everything.content.decode("utf-8-sig")
        self.assertIn("Export One", all_rows)
        self.assertIn("Export Two", all_rows)

        users = self.client.post(
            reverse("admin:auth_user_changelist"),
            {"action": "export_csv", "_selected_action": [first.pk]},
        )
        user_rows = list(csv.reader(io.StringIO(users.content.decode("utf-8-sig"))))
        self.assertNotIn("password", [cell.lower() for cell in user_rows[0]])
        self.assertNotIn(first.password, users.content.decode())

    def test_export_is_hidden_from_staff_who_are_not_superusers(self):
        user_for_phone("09120001144")
        staff = User.objects.create_user("plain-staff", "plain@example.com", "secret")
        staff.is_staff = True
        staff.save()
        staff.user_permissions.add(
            Permission.objects.get(content_type__app_label="honaryaar", codename="view_profile")
        )
        self.client.force_login(staff)
        url = reverse("admin:honaryaar_profile_changelist")
        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, "Export to CSV")
        refused = self.client.post(url, {"action": "export_csv", "_selected_action": [Profile.objects.first().pk]})
        self.assertNotEqual(refused.get("Content-Type"), "text/csv; charset=utf-8")
        self.assertNotIn("attachment", refused.get("Content-Disposition", ""))
