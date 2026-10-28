from pathlib import Path
from unittest.mock import patch

from django.test import TestCase

from honaryaar.models import ArtCategory, Opportunity, Project, ProjectContact, Role


class FakeCounters:
    def __init__(self):
        self.store = {}
        self.ttls = []
        self.deleted = []

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value
        self.ttls.append((key, ttl))

    def delete(self, *keys):
        self.deleted.extend(keys)
        for key in keys:
            self.store.pop(key, None)


class FreshPublicRowTests(TestCase):
    def test_project_created_after_the_first_request_is_visible(self):
        category = ArtCategory.objects.get(slug="stage-play")
        role = Role.objects.get(slug="actor")
        self.client.get("/projects/")
        project = Project.objects.create(
            slug="fresh-row",
            title="پروژه تازه",
            art_category=category,
            status="casting",
        )
        Opportunity.objects.create(
            slug="fresh-row-1",
            title="نقش تازه",
            project=project,
            role=role,
            art_category=category,
            paid=False,
            status="open",
        )
        listing = self.client.get("/projects/")
        detail = self.client.get("/projects/fresh-row/")
        call = self.client.get("/opportunities/fresh-row-1/")
        found = self.client.get("/search/", {"q": "پروژه تازه"})
        self.assertContains(listing, "/projects/fresh-row/")
        self.assertContains(listing, "پروژه تازه")
        self.assertContains(detail, "پروژه تازه")
        self.assertContains(call, "نقش تازه")
        self.assertContains(found, "/projects/fresh-row/")


class CounterCacheTests(TestCase):
    def test_save_refreshes_counters_with_a_ten_minute_ttl(self):
        import honaryaar.catalog as catalog

        fake = FakeCounters()
        category = ArtCategory.objects.get(slug="stage-play")
        with patch.object(catalog, "_upstash", return_value=fake):
            catalog.listing_stats()
            catalog.hire_stats()
            catalog.talent_stats()
            catalog.post_call_stats()
            self.assertEqual({ttl for _key, ttl in fake.ttls}, {catalog._STATS_TTL})
            self.assertEqual(catalog._STATS_TTL, 10 * 60)
            self.assertEqual(set(fake.store), set(catalog.STAT_KEYS.values()))
            project = Project.objects.create(
                slug="counter-row",
                title="شمارنده",
                art_category=category,
                status="casting",
            )
            self.assertEqual(fake.store, {})
            self.assertEqual(
                set(fake.deleted),
                set(catalog.STAT_KEYS.values()) | set(catalog.CHROME_KEYS.values()),
            )
            Opportunity.objects.create(
                slug="counter-row-1",
                title="نقش",
                project=project,
                role=Role.objects.get(slug="actor"),
                art_category=category,
                paid=False,
                status="open",
            )
            ProjectContact.objects.create(project=project, kind="phone", value="09120000000", is_public=False)
            project.delete()

            def refreshed():
                return {"refreshed": True}

            with patch.object(catalog, "_listing_counts", refreshed):
                self.assertEqual(catalog.listing_stats(), {"refreshed": True})
            self.assertEqual(fake.ttls[-1], ("honaryaar:stats:listing:v1", 600))

    def test_missing_redis_counts_directly(self):
        import honaryaar.catalog as catalog

        with patch.object(catalog, "_upstash", return_value=None):
            catalog.forget_stat_counters()
            stats = catalog.listing_stats()
        self.assertIn("projects", stats)

    def test_snapshot_key_is_gone(self):
        source = Path("honaryaar/catalog.py").read_text(encoding="utf-8")
        self.assertNotIn("honaryaar:home:v4", source)
        self.assertNotIn("_daily_snapshot", source)
        self.assertNotIn("_DAILY_LOADERS", source)
