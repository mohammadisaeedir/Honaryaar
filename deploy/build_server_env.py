#!/usr/bin/env python3
"""Build a production .env for the VPS from the local .env (never committed)."""

from __future__ import annotations

import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / ".env"
OUT = ROOT / "deploy" / ".env.production"


def load_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.is_file():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            data[key] = value
    return data


def main() -> int:
    src = load_env(SRC)
    prod_db = (src.get("PROD_DATABASE_URL") or src.get("DATABASE_URL") or "").strip()
    if not prod_db:
        print("PROD_DATABASE_URL or DATABASE_URL must be set in .env", file=sys.stderr)
        return 1

    secret = (src.get("DJANGO_SECRET_KEY") or "").strip()
    if not secret or secret.startswith("django-insecure"):
        secret = secrets.token_urlsafe(50)

    out = {
        "DJANGO_SECRET_KEY": secret,
        "DJANGO_DEBUG": "false",
        "DJANGO_ALLOWED_HOSTS": "honaryaar.ir,www.honaryaar.ir",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "https://honaryaar.ir,https://www.honaryaar.ir",
        "DATABASE_URL": prod_db,
        "REDIS_URL": "redis://127.0.0.1:6379/0",
        # Must match live object keys (production/...), not local "dev".
        "MEDIA_STORAGE_PREFIX": "production",
        "PARSPACK_ACCESS_KEY_ID": src.get("PARSPACK_ACCESS_KEY_ID", ""),
        "PARSPACK_SECRET_ACCESS_KEY": src.get("PARSPACK_SECRET_ACCESS_KEY", ""),
        "PARSPACK_ENDPOINT_URL": src.get("PARSPACK_ENDPOINT_URL", ""),
        "PARSPACK_BUCKET_NAME": src.get("PARSPACK_BUCKET_NAME", ""),
        "PARSPACK_REGION_NAME": src.get("PARSPACK_REGION_NAME", ""),
        "PARSPACK_PUBLIC_MEDIA_BASE_URL": src.get(
            "PARSPACK_PUBLIC_MEDIA_BASE_URL", "https://media.honaryaar.ir"
        ),
        "MEDIA_UPLOAD_ORIGINS": "https://honaryaar.ir,https://www.honaryaar.ir",
        "MEDIA_PROFILE_MAX_ITEMS": src.get("MEDIA_PROFILE_MAX_ITEMS", "12"),
        "MEDIA_MAX_IMAGE_BYTES": src.get("MEDIA_MAX_IMAGE_BYTES", "5242880"),
        "MEDIA_MAX_VIDEO_BYTES": src.get("MEDIA_MAX_VIDEO_BYTES", "52428800"),
        "MEDIA_MAX_AUDIO_BYTES": src.get("MEDIA_MAX_AUDIO_BYTES", "15728640"),
        "MEDIA_PRESIGN_SECONDS": src.get("MEDIA_PRESIGN_SECONDS", "600"),
        "MEDIA_ABANDON_HOURS": src.get("MEDIA_ABANDON_HOURS", "24"),
        "PUSH_PROVIDER": src.get("PUSH_PROVIDER", "log"),
        "NOTIFICATION_LOG_RETENTION_DAYS": src.get(
            "NOTIFICATION_LOG_RETENTION_DAYS", "90"
        ),
    }
    for key in (
        "FCM_CREDENTIALS_JSON",
        "FCM_CREDENTIALS_FILE",
        "FIREBASE_API_KEY",
        "FIREBASE_AUTH_DOMAIN",
        "FIREBASE_PROJECT_ID",
        "FIREBASE_MESSAGING_SENDER_ID",
        "FIREBASE_APP_ID",
        "FIREBASE_VAPID_KEY",
        "UPSTASH_REDIS_URL",
        "KV_URL",
    ):
        if src.get(key):
            out[key] = src[key]

    missing = [k for k, v in out.items() if not v and k.startswith("PARSPACK_")]
    if missing:
        print(f"Missing ParsPack values in .env: {', '.join(missing)}", file=sys.stderr)
        return 1

    lines = [f"{k}={v}" for k, v in out.items()]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT.chmod(0o600)
    print(f"Wrote {OUT} (mode 600). Do not commit this file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
