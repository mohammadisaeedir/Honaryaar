from datetime import timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from honaryaar.accounts import user_for_phone
from honaryaar.models import (
    ArtCategory,
    InAppNotification,
    Invite,
    NotificationChannel,
    NotificationLog,
    NotificationLogStatus,
    NotificationTemplate,
    Opportunity,
    Project,
    PushDevice,
    Role,
)
from honaryaar.notifications import (
    CODE_INVITE_SENT,
    notify_invite_sent,
    notify_user,
    purge_old_logs,
    register_push_device,
    render_string,
)


class NotificationRenderTests(TestCase):
    def test_render_string_fills_placeholders(self):
        text = render_string("سلام {{ name }}", {"name": "سارا"})
        self.assertEqual(text, "سلام سارا")

    def test_render_string_missing_var_is_blank(self):
        self.assertEqual(render_string("x={{ missing }}", {}), "x=")


class NotificationDispatchTests(TestCase):
    def setUp(self):
        self.category = ArtCategory.objects.create(
            art="theatre",
            slug="notif-art",
            title="تئاتر اعلان",
        )
        self.role = Role.objects.create(
            slug="notif-role",
            title="بازیگر",
            group="اجرا",
            art_category=self.category,
        )
        self.owner = user_for_phone("09121110001")
        self.owner.first_name = "مالک"
        self.owner.last_name = "پروژه"
        self.owner.save()
        self.artist = user_for_phone("09121110002")
        self.artist.first_name = "هنرمند"
        self.artist.last_name = "نمونه"
        self.artist.save()
        self.project = Project.objects.create(
            slug="notif-project",
            title="پروژه اعلان",
            art_category=self.category,
            status="draft",
            owner=self.owner.profile,
        )
        self.opportunity = Opportunity.objects.create(
            slug="notif-opp",
            title="فراخوان اعلان",
            project=self.project,
            role=self.role,
            art_category=self.category,
            status="open",
        )
        NotificationTemplate.objects.update_or_create(
            code=CODE_INVITE_SENT,
            channel=NotificationChannel.PUSH,
            defaults={
                "name": "دعوت",
                "title": "دعوت جدید",
                "body": "{{ owner_name }} شما را به «{{ opportunity_title }}» دعوت کرد.",
                "deep_link": "/me/invites/{{ invite_id }}/",
                "is_active": True,
            },
        )

    def test_invite_sent_logs_skipped_without_device(self):
        invite = Invite.objects.create(profile=self.artist.profile, opportunity=self.opportunity)
        logs = notify_invite_sent(invite)
        self.assertEqual(len(logs), 1)
        log = logs[0]
        self.assertEqual(log.user_id, self.artist.pk)
        self.assertEqual(log.code, CODE_INVITE_SENT)
        self.assertEqual(log.channel, NotificationChannel.PUSH)
        self.assertEqual(log.status, NotificationLogStatus.SKIPPED)
        self.assertEqual(log.error, "no_device")
        self.assertIn("مالک", log.body)
        self.assertIn("فراخوان اعلان", log.body)
        self.assertEqual(log.deep_link, f"/me/invites/{invite.pk}/")
        inbox = InAppNotification.objects.get(user=self.artist, code=CODE_INVITE_SENT)
        self.assertFalse(inbox.is_read)
        self.assertEqual(inbox.title, "دعوت جدید")
        self.assertEqual(inbox.deep_link, f"/me/invites/{invite.pk}/")

    def test_invite_sent_marks_sent_with_device_and_log_provider(self):
        register_push_device(self.artist, "device-token-abc", platform="web")
        invite = Invite.objects.create(profile=self.artist.profile, opportunity=self.opportunity)
        with override_settings(PUSH_PROVIDER="log"):
            logs = notify_invite_sent(invite)
        log = logs[0]
        self.assertEqual(log.status, NotificationLogStatus.SENT)
        self.assertEqual(log.provider, "log")
        self.assertTrue(log.provider_ref.startswith("devices="))
        self.assertIsNotNone(log.sent_at)
        self.assertEqual(InAppNotification.objects.filter(user=self.artist).count(), 1)

    def test_fcm_provider_sends_and_invalidates_bad_token(self):
        register_push_device(self.artist, "good-token", platform="web")
        register_push_device(self.artist, "bad-token", platform="web")
        invite = Invite.objects.create(profile=self.artist.profile, opportunity=self.opportunity)

        def fake_send(token, **kwargs):
            if token == "bad-token":
                return False, "http_404:UNREGISTERED", True
            return True, "projects/x/messages/1", False

        with override_settings(PUSH_PROVIDER="fcm", FIREBASE_PROJECT_ID="demo"):
            with mock.patch("honaryaar.fcm.fcm_configured", return_value=True):
                with mock.patch("honaryaar.fcm.send_to_token", side_effect=fake_send):
                    logs = notify_invite_sent(invite)
        self.assertEqual(logs[0].status, NotificationLogStatus.SENT)
        self.assertEqual(logs[0].provider, "fcm")
        self.assertTrue(PushDevice.objects.get(token="good-token").is_active)
        self.assertFalse(PushDevice.objects.get(token="bad-token").is_active)

    def test_inactive_template_is_skipped(self):
        NotificationTemplate.objects.filter(code=CODE_INVITE_SENT).update(is_active=False)
        invite = Invite.objects.create(profile=self.artist.profile, opportunity=self.opportunity)
        logs = notify_invite_sent(invite)
        self.assertEqual(logs[0].status, NotificationLogStatus.SKIPPED)
        self.assertEqual(logs[0].error, "no_active_template")

    def test_sms_channel_skipped_until_configured(self):
        NotificationTemplate.objects.create(
            code="invite.sent",
            channel=NotificationChannel.SMS,
            name="SMS دعوت",
            title="",
            body="پیامک تست {{ opportunity_title }}",
            is_active=True,
        )
        invite = Invite.objects.create(profile=self.artist.profile, opportunity=self.opportunity)
        logs = notify_user(
            self.artist,
            CODE_INVITE_SENT,
            {"opportunity_title": "فراخوان"},
            related=invite,
            channels=(NotificationChannel.SMS,),
        )
        self.assertEqual(logs[0].status, NotificationLogStatus.SKIPPED)
        self.assertEqual(logs[0].error, "sms_not_configured")


class NotificationRetentionTests(TestCase):
    def test_purge_old_logs(self):
        user = user_for_phone("09121110003")
        old = NotificationLog.objects.create(
            code="invite.sent",
            channel=NotificationChannel.PUSH,
            user=user,
            title="قدیمی",
            body="قدیمی",
            status=NotificationLogStatus.SENT,
        )
        NotificationLog.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=100)
        )
        recent = NotificationLog.objects.create(
            code="invite.sent",
            channel=NotificationChannel.PUSH,
            user=user,
            title="جدید",
            body="جدید",
            status=NotificationLogStatus.SENT,
        )
        deleted = purge_old_logs(days=90)
        self.assertEqual(deleted, 1)
        self.assertFalse(NotificationLog.objects.filter(pk=old.pk).exists())
        self.assertTrue(NotificationLog.objects.filter(pk=recent.pk).exists())


class PushDeviceTests(TestCase):
    def test_register_updates_same_token(self):
        first = user_for_phone("09121110004")
        second = user_for_phone("09121110005")
        device = register_push_device(first, "shared-token")
        self.assertEqual(PushDevice.objects.filter(token="shared-token").count(), 1)
        moved = register_push_device(second, "shared-token", platform="ios")
        self.assertEqual(device.pk, moved.pk)
        moved.refresh_from_db()
        self.assertEqual(moved.user_id, second.pk)
        self.assertEqual(moved.platform, "ios")
        self.assertTrue(moved.is_active)


class InboxViewTests(TestCase):
    def setUp(self):
        self.user = user_for_phone("09121110006")
        self.item = InAppNotification.objects.create(
            user=self.user,
            code="invite.sent",
            title="دعوت جدید",
            body="متن اعلان",
            deep_link="/me/invites/1/",
        )

    def test_inbox_page_lists_items(self):
        self.client.force_login(self.user)
        page = self.client.get(reverse("me-notifications"))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "دعوت جدید")
        self.assertContains(page, "متن اعلان")

    def test_open_marks_read_and_redirects(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("me-notification-open", args=[self.item.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/me/invites/1/")
        self.item.refresh_from_db()
        self.assertTrue(self.item.is_read)

    def test_register_device_endpoint(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("push-devices"),
            data='{"token":"web-token-1","platform":"web"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertTrue(PushDevice.objects.filter(user=self.user, token="web-token-1", is_active=True).exists())
