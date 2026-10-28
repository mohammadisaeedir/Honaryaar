# Production push (FCM)

## Already on production DB

Migration `0073_seed_notification_templates` seeded **6** push templates. No new migration is required.

| code | title |
|------|--------|
| `invite.sent` | دعوت جدید |
| `invite.replied` | پاسخ دعوت |
| `application.submitted` | درخواست جدید |
| `application.status_changed` | وضعیت درخواست |
| `collaboration.started` | همکاری جدید |
| `project.member_invited` | عضویت در تیم |

Re-seed anytime:

```bash
sudo -u honaryaar /var/www/honaryaar/.venv/bin/python /var/www/honaryaar/manage.py seed_notification_templates
```

## Why push does not fire yet

On the VPS today:

- `PUSH_PROVIDER=log` (stub, not FCM)
- Firebase web + service-account env vars are empty
- Browser never registers a device (`PushDevice` count = 0) because `push_enabled` is false without Firebase web config

## What to put in `/var/www/honaryaar/.env`

```bash
PUSH_PROVIDER=fcm
FIREBASE_API_KEY=...
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_PROJECT_ID=your-project
FIREBASE_MESSAGING_SENDER_ID=...
FIREBASE_APP_ID=...
FIREBASE_VAPID_KEY=...          # Cloud Messaging → Web Push certificates
FCM_CREDENTIALS_JSON={...}      # Firebase service-account JSON (one line)
# or: FCM_CREDENTIALS_FILE=/var/www/honaryaar/secrets/firebase-adminsdk.json
```

Then:

```bash
sudo systemctl restart honaryaar
```

## After env is set

1. Open the site while logged in → allow notifications → a `PushDevice` row should appear.
2. Trigger an invite / application / etc.
3. Check `NotificationLog` in admin (status should be `sent`, provider `fcm`).
