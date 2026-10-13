import re

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from honaryaar.accounts import ensure_profile, user_for_phone
from honaryaar.models import Profile


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
