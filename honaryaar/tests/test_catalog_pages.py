from django.test import TestCase

from honaryaar import catalog


class OpportunityPageTests(TestCase):
    def test_page_opportunities_respects_limit(self):
        items, total = catalog.page_opportunities(offset=0, limit=3)
        self.assertLessEqual(len(items), 3)
        self.assertGreaterEqual(total, len(items))
        if items:
            self.assertIn("card_project", items[0])
            self.assertIn("pay_label", items[0])

    def test_opportunity_facets_has_roles_in_use(self):
        facets = catalog.opportunity_facets()
        self.assertIn("roles", facets)
        self.assertIn("cities", facets)
        self.assertIn("productions", facets)

    def test_opportunity_list_partial(self):
        response = self.client.get(
            "/opportunities/",
            {"offset": "0", "limit": "2"},
            HTTP_X_REQUESTED_WITH="fetch",
            HTTP_HOST="localhost",
        )
        self.assertEqual(response.status_code, 200)


class ProjectPageTests(TestCase):
    def test_page_projects_respects_limit(self):
        items, total = catalog.page_projects(offset=0, limit=2)
        self.assertLessEqual(len(items), 2)
        self.assertGreaterEqual(total, len(items))
        if items:
            self.assertIn("open_calls", items[0])
            self.assertEqual(items[0]["testimonials"], [])

    def test_project_list_partial(self):
        response = self.client.get(
            "/projects/",
            {"offset": "0", "limit": "2"},
            HTTP_X_REQUESTED_WITH="fetch",
            HTTP_HOST="localhost",
        )
        self.assertEqual(response.status_code, 200)
