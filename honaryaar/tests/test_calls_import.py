import json
import os
import tempfile
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connections
from django.test import TestCase

from honaryaar.management.commands.import_crawled_calls import _prepare, _require_leaf
from honaryaar.models import ArtCategory, City, Project, Role

_URL = "postgresql://import-user:fixture-password@db.example:5432/honaryaar"


def _write(payload):
    handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(payload, handle, ensure_ascii=False)
    handle.close()
    return handle.name


def _call(slug, opportunities, **project):
    body = {
        "slug": slug,
        "title": "فراخوان آزمایشی",
        "category": "stage-play",
        "summary": "",
    }
    body.update(project)
    return {
        "source_channel": "telegram:fixture",
        "source_post_id": 9100,
        "project": body,
        "opportunities": opportunities,
    }


def _opp(slug, **extra):
    row = {
        "slug": slug,
        "title": "بازیگر",
        "production": "نمایش",
        "role_slug": "actor",
        "gender": "any",
        "paid": False,
        "pay_type": None,
        "pay_amount": None,
    }
    row.update(extra)
    return row


class ImportGuardTests(TestCase):
    def setUp(self):
        self._saved = {key: os.environ.get(key) for key in ("PROD_DATABASE_URL", "ALLOW_PROD_IMPORT", "VERCEL")}
        os.environ.pop("PROD_DATABASE_URL", None)
        os.environ.pop("ALLOW_PROD_IMPORT", None)
        os.environ.pop("VERCEL", None)

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _abort(self, *args, env=None):
        if env:
            os.environ.update(env)
        out = StringIO()
        with patch(
            "honaryaar.management.commands.import_crawled_calls._repoint",
            side_effect=AssertionError("repointed"),
        ):
            with self.assertRaises(CommandError) as caught:
                call_command("import_crawled_calls", *args, stdout=out)
        message = str(caught.exception)
        self.assertNotIn("fixture-password", message)
        self.assertNotIn("postgresql://", message)
        return message, out.getvalue()

    def test_production_guards_abort_before_connection(self):
        message, _output = self._abort("--file", "missing.json", "--production")
        self.assertEqual(message, "PROD_DATABASE_URL is not set")

        message, _output = self._abort(
            "--file",
            "missing.json",
            "--production",
            "--expect-host",
            "db.example",
            env={"PROD_DATABASE_URL": "not-a-database-url"},
        )
        self.assertEqual(message, "PROD_DATABASE_URL could not be parsed")

        message, _output = self._abort(
            "--file",
            "missing.json",
            "--production",
            env={"PROD_DATABASE_URL": _URL},
        )
        self.assertEqual(message, "--expect-host is required with --production")

        message, _output = self._abort(
            "--file",
            "missing.json",
            "--production",
            "--expect-host",
            "other.example",
            env={"PROD_DATABASE_URL": _URL},
        )
        self.assertEqual(message, "--expect-host does not match the database host")

        message, _output = self._abort(
            "--file",
            "missing.json",
            "--production",
            "--expect-host",
            "db.example",
            env={"PROD_DATABASE_URL": _URL, "ALLOW_PROD_IMPORT": "no"},
        )
        self.assertEqual(message, "ALLOW_PROD_IMPORT must be yes")

    def test_local_guards(self):
        wrapper = connections["default"]
        original = wrapper.settings_dict.get("HOST")
        wrapper.settings_dict["HOST"] = "db.example"
        try:
            message, _output = self._abort("--file", "missing.json")
        finally:
            wrapper.settings_dict["HOST"] = original
        self.assertEqual(message, "database host must be localhost or 127.0.0.1")

        message, _output = self._abort("--file", "missing.json", env={"VERCEL": "1"})
        self.assertEqual(message, "refusing to run when VERCEL=1")

    def test_leaf_must_be_pay_constraint_or_later(self):
        _require_leaf("0060_opportunity_pay_constraint")
        _require_leaf("0061_later")
        with self.assertRaises(CommandError) as caught:
            _require_leaf("0059_backfill_opportunity_pay")
        self.assertEqual(
            str(caught.exception),
            "migration leaf must be 0060_opportunity_pay_constraint or later",
        )

    def test_missing_catalog_rows_stop_the_import(self):
        before = (
            Role.objects.count(),
            City.objects.count(),
            ArtCategory.objects.count(),
            Project.objects.count(),
        )
        path = _write(
            [
                _call(
                    "missing-catalog",
                    [_opp("missing-catalog-1", role_slug="no-such-role", production="ژانر ناشناخته")],
                    category="no-such-art",
                    city="NoSuchCity",
                )
            ]
        )
        out = StringIO()
        with self.assertRaises(CommandError) as caught:
            call_command("import_crawled_calls", "--file", path, stdout=out)
        self.assertEqual(str(caught.exception), "catalog is missing rows the file needs")
        text = out.getvalue()
        self.assertIn("missing role\tno-such-role", text)
        self.assertIn("missing city\tNoSuchCity", text)
        self.assertIn("missing art category\tno-such-art", text)
        self.assertIn("missing art category\tژانر ناشناخته", text)
        self.assertEqual(
            before,
            (
                Role.objects.count(),
                City.objects.count(),
                ArtCategory.objects.count(),
                Project.objects.count(),
            ),
        )
        os.remove(path)

    def test_empty_role_and_invalid_pay_are_skipped(self):
        payload = [
            _call(
                "skip-parts",
                [
                    _opp("skip-parts-1"),
                    _opp("skip-parts-2", role_slug=""),
                    _opp("skip-parts-3", paid=True, pay_type="fixed", pay_amount=None, inferred_pay=True),
                ],
                lead_role="group",
                category="reading",
            )
        ]
        payload[0]["opportunities"][0]["production"] = "نمایشنامه\u200cخوانی"
        payload[0]["opportunities"][0]["inferred_pay"] = True
        payload[0]["opportunities"][0]["defaulted_pay"] = True
        calls, blocked, skipped = _prepare(payload)
        self.assertEqual(blocked, [])
        self.assertEqual(calls[0]["art_category"], "reading")
        self.assertEqual(calls[0]["lead_role"], None)
        self.assertEqual(calls[0]["lead_note"], "group")
        self.assertEqual(len(calls[0]["opportunities"]), 1)
        self.assertEqual(calls[0]["opportunities"][0]["paid"], False)
        self.assertEqual(calls[0]["opportunities"][0]["art_category"], "reading")
        self.assertIn(("skip-parts", "role_slug empty"), skipped)
        self.assertTrue(any(reason.startswith("invalid pay") for _slug, reason in skipped))
