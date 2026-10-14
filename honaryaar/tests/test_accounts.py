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
        self.assertContains(admin_page, "data-skill-picker")
        self.assertContains(admin_page, "js/skill-picker.js")
        self.assertContains(admin_page, skill.title)
        self.assertNotContains(admin_page, "profileskill-TOTAL_FORMS")
        admin_data = {
            "user": user.pk,
            "name": "",
            "mobile": user.profile.mobile,
            "city": "",
            "about": "",
            "birth_date": "",
            "gender": "",
            "status": user.profile.status,
            "skill_picker": "1",
            f"skill-{skill.pk}": "4",
            "list_upload": "",
            "banner_upload": "",
            "_save": "Save",
        }
        for prefix in re.findall(r'name="([A-Za-z0-9_]+)-TOTAL_FORMS"', admin_page.content.decode()):
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
        self.assertContains(admin_page, "data-role-picker")
        self.assertContains(admin_page, "js/role-picker.js")
        self.assertContains(admin_page, second.title)
        self.assertNotContains(admin_page, "profilerole-TOTAL_FORMS")
        admin_data = {
            "user": user.pk,
            "name": "",
            "mobile": user.profile.mobile,
            "city": "",
            "about": "",
            "birth_date": "",
            "gender": "",
            "status": user.profile.status,
            "role_picker": "1",
            f"role-{first.pk}": "1",
            "role_primary": str(first.pk),
            "list_upload": "",
            "banner_upload": "",
            "_save": "Save",
        }
        for prefix in re.findall(r'name="([A-Za-z0-9_]+)-TOTAL_FORMS"', admin_page.content.decode()):
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
