from django.test import TestCase
from django.urls import reverse


class AboutPageTests(TestCase):
    def test_about_page_uses_the_shared_layout_and_figma_hero_assets(self):
        response = self.client.get(reverse("about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="site-header site-header--redesigned ')
        self.assertContains(response, "site-header--dark")
        self.assertContains(response, 'class="site-footer"')
        self.assertContains(response, 'class="about-hero"')
        self.assertContains(response, "صحنه‌ی بعدی، با یک آشنایی شروع می‌شود.")
        self.assertContains(response, "/static/about/artwork-1.png")
        self.assertContains(response, "/static/about/artwork-2-overlay.png")
        self.assertContains(response, "/static/about/artwork-4.png")
        self.assertContains(response, 'class="about-story"')
        self.assertContains(response, "قصه‌ی هنریار، از دل جامعه‌ی هنر")
        self.assertContains(response, "/static/about/brand-mark.png")
        self.assertContains(response, 'class="about-features"')
        self.assertContains(response, "از معرفی تو تا شروع یک همکاری")
        self.assertContains(response, "/static/about/feature-casting.png")
        self.assertContains(response, "/static/about/feature-profile-mobile.png")
        self.assertContains(response, 'aria-label="ویژگی قبلی"')
        self.assertContains(response, 'aria-label="ویژگی بعدی"')
        self.assertContains(response, 'class="about-quote"')
        self.assertContains(response, "/static/about/quote-illustration.png")
        self.assertNotContains(response, "هر مورد مرتبط با هنر، همین‌جا.")
        self.assertNotContains(response, "figma.com/api/mcp/asset")
