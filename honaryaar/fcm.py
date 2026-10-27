"""Firebase Cloud Messaging (HTTP v1) helpers."""

from __future__ import annotations

import base64
import json
import logging
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from django.conf import settings

logger = logging.getLogger(__name__)

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
UNREGISTERED_CODES = {"UNREGISTERED", "INVALID_ARGUMENT", "NOT_FOUND"}

_cached_token: str | None = None
_cached_expiry: float = 0


def fcm_configured() -> bool:
    return bool(_credentials_info() and getattr(settings, "FIREBASE_PROJECT_ID", ""))


def web_config() -> dict[str, str] | None:
    project_id = getattr(settings, "FIREBASE_PROJECT_ID", "") or ""
    api_key = getattr(settings, "FIREBASE_API_KEY", "") or ""
    sender = getattr(settings, "FIREBASE_MESSAGING_SENDER_ID", "") or ""
    app_id = getattr(settings, "FIREBASE_APP_ID", "") or ""
    vapid = getattr(settings, "FIREBASE_VAPID_KEY", "") or ""
    if not all([project_id, api_key, sender, app_id, vapid]):
        return None
    return {
        "apiKey": api_key,
        "authDomain": getattr(settings, "FIREBASE_AUTH_DOMAIN", "") or f"{project_id}.firebaseapp.com",
        "projectId": project_id,
        "messagingSenderId": sender,
        "appId": app_id,
        "vapidKey": vapid,
    }


def _credentials_info() -> dict[str, Any] | None:
    raw = (getattr(settings, "FCM_CREDENTIALS_JSON", "") or "").strip()
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.exception("FCM_CREDENTIALS_JSON is not valid JSON")
            return None
    path = (getattr(settings, "FCM_CREDENTIALS_FILE", "") or "").strip()
    if path:
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.exception("failed to read FCM_CREDENTIALS_FILE=%s", path)
            return None
    return None


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _sign_jwt_openssl(private_key_pem: str, signing_input: bytes) -> bytes:
    with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as key_file:
        key_file.write(private_key_pem)
        key_path = key_file.name
    try:
        result = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", key_path],
            input=signing_input,
            capture_output=True,
            check=True,
        )
        return result.stdout
    finally:
        Path(key_path).unlink(missing_ok=True)


def _access_token_via_google_auth(info: dict[str, Any]) -> str:
    from google.auth.transport.urllib3 import Request
    from google.oauth2 import service_account
    import urllib3

    credentials = service_account.Credentials.from_service_account_info(
        info,
        scopes=[FCM_SCOPE],
    )
    credentials.refresh(Request(urllib3.PoolManager()))
    if not credentials.token:
        raise RuntimeError("fcm_token_empty")
    return credentials.token


def _access_token_via_openssl(info: dict[str, Any]) -> str:
    now = int(time.time())
    header = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
    claim = _b64url(
        json.dumps(
            {
                "iss": info["client_email"],
                "scope": FCM_SCOPE,
                "aud": info.get("token_uri") or "https://oauth2.googleapis.com/token",
                "iat": now,
                "exp": now + 3600,
            },
            separators=(",", ":"),
        ).encode()
    )
    signing_input = f"{header}.{claim}".encode("ascii")
    signature = _b64url(_sign_jwt_openssl(info["private_key"], signing_input))
    assertion = f"{header}.{claim}.{signature}"
    body = parse.urlencode(
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }
    ).encode()
    req = request.Request(
        info.get("token_uri") or "https://oauth2.googleapis.com/token",
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("fcm_token_empty")
    return token


def _access_token() -> str:
    global _cached_token, _cached_expiry
    if _cached_token and time.time() < _cached_expiry - 60:
        return _cached_token
    info = _credentials_info()
    if not info:
        raise RuntimeError("fcm_credentials_missing")
    try:
        token = _access_token_via_google_auth(info)
    except ImportError:
        token = _access_token_via_openssl(info)
    _cached_token = token
    _cached_expiry = time.time() + 3000
    return token


def clear_token_cache() -> None:
    global _cached_token, _cached_expiry
    _cached_token = None
    _cached_expiry = 0


def send_to_token(token: str, *, title: str, body: str, deep_link: str = "") -> tuple[bool, str, bool]:
    """
    Send one FCM data+notification message.

    Returns (ok, detail, invalidate_token).
    """
    project_id = getattr(settings, "FIREBASE_PROJECT_ID", "") or ""
    if not project_id:
        return False, "fcm_project_missing", False
    if not token:
        return False, "empty_token", True

    message: dict[str, Any] = {
        "message": {
            "token": token,
            "notification": {
                "title": title[:200],
                "body": body[:1000],
            },
            "data": {
                "title": title[:200],
                "body": body[:1000],
                "deep_link": deep_link or "/",
            },
            "webpush": {
                "fcm_options": {
                    "link": deep_link or "/",
                },
            },
        }
    }

    try:
        access = _access_token()
    except Exception as exc:
        clear_token_cache()
        return False, f"fcm_auth:{exc}", False

    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    payload = json.dumps(message).encode("utf-8")
    req = request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {access}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with request.urlopen(req, timeout=15) as resp:
            body_text = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body_text)
            except json.JSONDecodeError:
                parsed = {}
            name = parsed.get("name") or body_text[:180]
            return True, str(name)[:200], False
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        invalidate = False
        code = ""
        try:
            parsed = json.loads(detail)
            err = parsed.get("error") or {}
            code = str(err.get("status") or "")
            for item in err.get("details") or []:
                err_code = str(item.get("errorCode") or "")
                if err_code in UNREGISTERED_CODES or code in UNREGISTERED_CODES:
                    invalidate = True
            if code in UNREGISTERED_CODES:
                invalidate = True
        except json.JSONDecodeError:
            pass
        if exc.code in (401, 403):
            clear_token_cache()
        return False, f"http_{exc.code}:{code or detail[:160]}", invalidate
    except error.URLError as exc:
        return False, f"network:{exc.reason}", False
