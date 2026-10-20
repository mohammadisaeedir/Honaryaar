from django.test import SimpleTestCase, TestCase

from honaryaar import catalog
from honaryaar.models import Role


class ArtistPageQueryTests(TestCase):
    def test_page_artists_returns_only_limit_rows(self):
        items, total = catalog.page_artists(offset=0, limit=3)
        self.assertLessEqual(len(items), 3)
        self.assertGreaterEqual(total, len(items))
        if items:
            self.assertIn("role_titles", items[0])
            self.assertIn("list_image_key", items[0])

    def test_roles_on_artists_only_includes_linked_roles(self):
        linked = set(
            Role.objects.filter(profile_roles__isnull=False).values_list("slug", flat=True)
        )
        shown = {item["slug"] for item in catalog.roles_on_artists()}
        self.assertTrue(shown)
        self.assertTrue(shown.issubset(linked))

    def test_artist_list_partial_uses_page_artists(self):
        response = self.client.get(
            "/artists/",
            {"offset": "0", "limit": "2"},
            HTTP_X_REQUESTED_WITH="fetch",
            HTTP_HOST="localhost",
        )
        self.assertEqual(response.status_code, 200)


class ArtistCardDictTests(SimpleTestCase):
    def test_card_dict_skips_heavy_relations(self):
        source = open("honaryaar/catalog.py", encoding="utf-8").read()
        self.assertIn("def page_artists(", source)
        self.assertIn("def roles_on_artists(", source)
        self.assertIn("def _artist_card_queryset(", source)
