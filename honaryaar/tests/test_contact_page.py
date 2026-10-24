from django.test import TestCase
from django.urls import reverse

from honaryaar.models import KindReason, SupportTicket, TicketKind


class ContactPageTests(TestCase):
    def test_contact_page_renders_the_redesigned_form_and_local_assets(self):
        response = self.client.get(reverse("contact"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="site-header site-header--redesigned ')
        self.assertContains(response, "site-header--light")
        self.assertContains(response, "با هنریار در تماس باشید")
        self.assertContains(response, 'class="contact-page__grid"')
        self.assertContains(response, 'name="kind_reason"')
        self.assertContains(response, 'name="body"')
        self.assertContains(response, 'mailto:info@honaryaar.ir')
        self.assertContains(response, 'tel:+989356706868')
        self.assertContains(response, "/static/contact/social-media-illustration.png")
        self.assertContains(response, "/static/footer-promo/stage-performer.png")
        self.assertContains(response, "برای نقش بعدی‌ات آماده‌ای؟")
        self.assertContains(response, "/static/footer/figma-raw-4.png")
        self.assertContains(response, "/static/footer/badge-samandehi.png")
        self.assertContains(response, 'class="site-footer__mobile"')
        self.assertContains(response, 'class="site-footer__accordion"')
        self.assertContains(response, "/static/footer/chevron-down.svg")
        self.assertContains(response, "هنریار را در شبکه‌های اجتماعی دنبال کنید")
        self.assertContains(response, '<h3 class="site-footer__title">فرصت‌های هنری</h3>', html=True)
        self.assertContains(response, '<h3 class="site-footer__title">حوزه‌های هنری</h3>', html=True)
        self.assertNotContains(response, "figma.com/api/mcp/asset")

    def test_contact_page_creates_a_contact_ticket(self):
        response = self.client.post(
            reverse("contact"),
            {"kind_reason": KindReason.GENERAL, "body": "لطفاً پیگیری کنید."},
        )

        self.assertRedirects(response, f"{reverse('contact')}?sent=1", fetch_redirect_response=False)
        ticket = SupportTicket.objects.get()
        self.assertEqual(ticket.kind, TicketKind.CONTACT)
        self.assertEqual(ticket.kind_reason, KindReason.GENERAL)
        self.assertEqual(ticket.body, "لطفاً پیگیری کنید.")
        self.assertEqual(ticket.messages.count(), 1)

    def test_contact_page_shows_validation_errors_without_losing_the_message(self):
        response = self.client.post(
            reverse("contact"),
            {"kind_reason": "", "body": "پیام آزمایشی"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "موضوع را انتخاب کنید.")
        self.assertContains(response, "پیام آزمایشی")
        self.assertEqual(SupportTicket.objects.count(), 0)
