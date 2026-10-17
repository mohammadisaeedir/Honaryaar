from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from honaryaar.admin import OpportunityAdminForm
from honaryaar.management.commands.import_crawled_calls import _parse_pay
from honaryaar.models import ArtCategory, City, Opportunity, PayType, Project, ProjectContact, Role
from honaryaar.pay import classify_legacy_pay, format_tomans, pay_label


def _flush_catalog():
    import honaryaar.catalog as catalog

    catalog._daily_mem["value"] = None
    catalog._daily_mem["at"] = 0
    for fn in (catalog._opportunities, catalog._projects, catalog._artists):
        for cell in fn.__closure__ or ():
            try:
                box = cell.cell_contents
            except ValueError:
                continue
            if isinstance(box, dict) and "at" in box and "value" in box:
                box["value"] = None
                box["at"] = 0


class PayRuleTests(TestCase):
    def test_legacy_notes_and_labels(self):
        self.assertEqual(classify_legacy_pay("دستمزد توافقی، پرداخت بعد از شروع اجرا.")[:2], ("negotiable", None))
        self.assertEqual(classify_legacy_pay("در حد هدیه")[0], "gift")
        self.assertEqual(classify_legacy_pay("درصدی از گیشه")[0], "box_office")
        self.assertEqual(classify_legacy_pay("۵ میلیون تومان")[:2], ("fixed", 5_000_000))
        kind, amount, fell_back = classify_legacy_pay("مبلغ بعد از انتخاب نهایی اعلام می‌شود.")
        self.assertEqual((kind, amount, fell_back), ("gift", None, True))
        self.assertEqual(format_tomans(5_000_000), "۵ میلیون تومان")
        self.assertEqual(format_tomans(12_000), "۱۲٬۰۰۰ تومان")
        self.assertEqual(pay_label(False, "", None), "بدون دستمزد")

    def test_model_rejects_invalid_combinations(self):
        category = ArtCategory.objects.get(slug="stage-play")
        role = Role.objects.get(slug="actor")
        project = Project.objects.create(slug="pay-rules", title="قواعد", art_category=category, status="draft")
        opening = Opportunity(
            slug="pay-rules-1",
            title="نقش",
            project=project,
            role=role,
            art_category=category,
            paid=True,
            pay_type="",
        )
        with self.assertRaises(ValidationError):
            opening.save()
        opening.pay_type = PayType.FIXED
        opening.pay_amount = None
        with self.assertRaises(ValidationError):
            opening.save()
        opening.pay_amount = 2_000_000
        opening.save()
        self.assertEqual(opening.pay_amount, 2_000_000)
        opening.paid = False
        opening.pay_type = PayType.GIFT
        with self.assertRaises(ValidationError):
            opening.save()

    def test_admin_form_accepts_valid_and_rejects_invalid(self):
        category = ArtCategory.objects.get(slug="stage-play")
        role = Role.objects.get(slug="actor")
        project = Project.objects.create(slug="pay-admin", title="ادمین", art_category=category, status="draft")
        base = {
            "title": "بازیگر",
            "project": project.pk,
            "role": role.pk,
            "art_category": category.pk,
            "slug": "pay-admin-1",
            "gender": "any",
            "count": 1,
            "status": "open",
            "views": "0",
            "featured": "",
            "description": "",
            "requirements": "[]",
            "special_conditions": [],
        }
        valid = OpportunityAdminForm(data={**base, "paid": "on", "pay_type": "negotiable", "pay_amount": ""})
        self.assertTrue(valid.is_valid(), valid.errors)
        missing = OpportunityAdminForm(data={**base, "paid": "on", "pay_type": "", "pay_amount": ""})
        self.assertFalse(missing.is_valid())
        self.assertIn("pay_type", missing.errors)
        unpaid = OpportunityAdminForm(data={**base, "paid": "", "pay_type": "gift", "pay_amount": ""})
        self.assertFalse(unpaid.is_valid())
        fixed = OpportunityAdminForm(data={**base, "slug": "pay-admin-2", "paid": "on", "pay_type": "fixed", "pay_amount": ""})
        self.assertFalse(fixed.is_valid())
        self.assertIn("pay_amount", fixed.errors)

    def test_list_filters_combine(self):
        _flush_catalog()
        paid = self.client.get("/opportunities/?paid=paid")
        unpaid = self.client.get("/opportunities/?paid=unpaid")
        both = self.client.get("/opportunities/?paid=paid&pay_type=negotiable&city=تهران")
        none = self.client.get("/opportunities/?paid=unpaid&pay_type=fixed")
        self.assertEqual(paid.status_code, 200)
        self.assertContains(paid, "پرستار")
        self.assertNotContains(paid, "راوی")
        self.assertContains(unpaid, "راوی")
        self.assertContains(both, "پرستار")
        self.assertNotContains(both, "مادر")
        self.assertNotContains(none, "پرستار")
        self.assertNotContains(none, "راوی")
        self.assertContains(paid, "دستمزد")
        self.assertContains(paid, "توافقی")

    def test_public_pages_hide_project_contacts_and_show_pay(self):
        category = ArtCategory.objects.get(slug="stage-play")
        city = City.objects.get(slug="tehran")
        role = Role.objects.get(slug="actor")
        project = Project.objects.create(
            slug="pay-public",
            title="پروژه عمومی",
            art_category=category,
            city=city,
            status="casting",
            summary="خلاصه‌ای بدون راه تماس.",
        )
        ProjectContact.objects.create(
            project=project,
            kind="phone",
            value="09120000000",
            is_public=True,
            source="telegram",
        )
        Opportunity.objects.create(
            slug="pay-public-1",
            title="نقش ثابت",
            project=project,
            role=role,
            art_category=category,
            city=city,
            paid=True,
            pay_type=PayType.FIXED,
            pay_amount=5_000_000,
            status="open",
        )
        Opportunity.objects.create(
            slug="pay-public-2",
            title="نقش رایگان",
            project=project,
            role=role,
            art_category=category,
            city=city,
            paid=False,
            status="open",
        )
        _flush_catalog()
        project_page = self.client.get("/projects/pay-public/")
        paid_page = self.client.get("/opportunities/pay-public-1/")
        free_page = self.client.get("/opportunities/pay-public-2/")
        listing = self.client.get("/opportunities/?pay_type=fixed")
        self.assertEqual(project_page.status_code, 200)
        self.assertEqual(paid_page.status_code, 200)
        self.assertNotContains(project_page, "09120000000")
        self.assertNotContains(project_page, "برای همکاری")
        self.assertNotContains(paid_page, "09120000000")
        self.assertNotContains(paid_page, "برای همکاری")
        self.assertContains(paid_page, "۵ میلیون تومان")
        self.assertContains(free_page, "بدون دستمزد")
        self.assertContains(listing, "نقش ثابت")
        self.assertNotContains(listing, "نقش رایگان")

    def test_studio_create_and_edit(self):
        user = User.objects.create_user("pay-owner", password="secret")
        from honaryaar.models import Profile

        Profile.objects.create(user=user, slug="pay-owner", name="مالک", status="claimed")
        category = ArtCategory.objects.get(slug="stage-play")
        role = Role.objects.get(slug="actor")
        project = Project.objects.create(slug="pay-studio", title="استودیو", art_category=category, status="draft", owner=Profile.objects.get(slug="pay-owner"))
        self.client.force_login(user)
        rejected = self.client.post(
            reverse("me-project", args=[project.slug]),
            {"action": "opportunity", "title": "بد", "role": role.pk, "description": "", "paid": "on", "pay_type": "", "pay_amount": ""},
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertFalse(project.opportunities.exists())
        created = self.client.post(
            reverse("me-project", args=[project.slug]),
            {"action": "opportunity", "title": "خوب", "role": role.pk, "description": "متن", "paid": "on", "pay_type": "fixed", "pay_amount": "250000"},
        )
        self.assertEqual(created.status_code, 302)
        opening = project.opportunities.get()
        self.assertEqual(opening.pay_type, "fixed")
        self.assertEqual(opening.pay_amount, 250000)
        edited = self.client.post(
            reverse("me-project", args=[project.slug]),
            {
                "action": "opportunity",
                "opportunity": opening.pk,
                "title": "خوب",
                "role": role.pk,
                "description": "متن",
                "pay_type": "",
                "pay_amount": "",
            },
        )
        self.assertEqual(edited.status_code, 302)
        opening.refresh_from_db()
        self.assertFalse(opening.paid)
        self.assertEqual(opening.pay_type, "")
        self.assertIsNone(opening.pay_amount)

    def test_import_pay_rules(self):
        unpaid = _parse_pay({"paid": False, "pay_type": None, "pay_amount": None})
        self.assertEqual(unpaid[0], {"paid": False, "pay_type": "", "pay_amount": None})
        gift = _parse_pay({"paid": True, "pay_type": "gift", "pay_amount": None})
        self.assertEqual(gift[0]["pay_type"], "gift")
        invalid = _parse_pay({"paid": True, "pay_type": "fixed", "pay_amount": None})
        self.assertIsNone(invalid[0])
        self.assertEqual(invalid[1], "invalid pay")
