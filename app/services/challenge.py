"""Stateless, signed, single-use challenge tokens (RFC 0008).

A challenge token is an HMAC-signed payload binding {agent_id, probe_ids, nonce,
expiry}. Stateless issuance (no DB row) keeps it scalable; integrity comes from
the HMAC, freshness from the expiry, and single-use from the nonce store. The
nonce is what defeats trajectory replay: a recorded response cannot satisfy a
challenge whose fresh nonce it never saw.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from app.config import settings


class ChallengeError(Exception):
    """Raised when a challenge token is invalid, expired, tampered, or replayed."""


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign_bytes(raw: bytes) -> bytes:
    return hmac.new(settings.CHALLENGE_SECRET.encode(), raw, hashlib.sha256).digest()


def new_nonce() -> str:
    return secrets.token_urlsafe(16)


def issue(agent_id: str, probe_ids: list[str], nonce: str | None = None) -> tuple[str, dict]:
    now = int(time.time())
    payload = {
        "agent_id": str(agent_id),
        "probe_ids": probe_ids,
        "nonce": nonce or new_nonce(),
        "iat": now,
        "exp": now + settings.CHALLENGE_TTL_SECONDS,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    token = f"{_b64(raw)}.{_b64(_sign_bytes(raw))}"
    return token, payload


def decode(token: str) -> dict:
    """Verify signature + expiry and return the payload. Raises ChallengeError."""
    try:
        body_b64, sig_b64 = token.split(".", 1)
        raw = _unb64(body_b64)
        sig = _unb64(sig_b64)
    except Exception as e:
        raise ChallengeError("malformed challenge token") from e

    if not hmac.compare_digest(sig, _sign_bytes(raw)):
        raise ChallengeError("challenge token signature invalid")

    payload = json.loads(raw)
    if int(time.time()) >= payload.get("exp", 0):
        raise ChallengeError("challenge token expired")
    return payload


# --- single-use nonce store (in-memory; use a shared store for multi-instance) --
_used: dict[str, int] = {}  # nonce -> expiry epoch


def consume_nonce(nonce: str, exp: int) -> bool:
    """Mark a nonce used. Returns False if it was already used (replay)."""
    now = int(time.time())
    # opportunistic purge of expired nonces
    for n in [n for n, e in _used.items() if e <= now]:
        _used.pop(n, None)
    if nonce in _used:
        return False
    _used[nonce] = exp
    return True


def reset() -> None:
    """Clear the nonce store (tests)."""
    _used.clear()
