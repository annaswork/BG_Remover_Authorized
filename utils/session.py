"""
Lightweight signed-session helpers.

Token format (URL-safe base64-encoded JSON + HMAC-SHA256 signature):
  <base64(payload_json)>.<hex_signature>

payload = {"sub": "admin", "iat": <unix_timestamp>}

No external dependencies required — uses only stdlib.
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Optional

from config.index import SECRET_KEY, SESSION_TTL

_SIGNING_KEY = SECRET_KEY.encode("utf-8")
COOKIE_NAME = "admin_session"


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(s: str) -> bytes:
    # Restore padding
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_session_token(username: str) -> str:
    """Create a signed session token for *username*."""
    payload = {"sub": username, "iat": int(time.time())}
    payload_b64 = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(_SIGNING_KEY, payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_session_token(token: str) -> Optional[str]:
    """
    Verify the token signature and TTL.
    Returns the username string on success, None on any failure.
    """
    if not token or "." not in token:
        return None
    try:
        payload_b64, sig = token.rsplit(".", 1)
        expected_sig = hmac.new(
            _SIGNING_KEY, payload_b64.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None

        payload = json.loads(_b64decode(payload_b64).decode("utf-8"))
        issued_at = payload.get("iat", 0)
        if time.time() - issued_at > SESSION_TTL:
            return None

        return payload.get("sub")
    except Exception:
        return None
