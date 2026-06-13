"""Shared Signals Framework / CAEP transmitter (RFC 0011).

Emits behavioral-risk and revocation events as signed Security Event Tokens
(SETs) so that IdPs / relying parties (Okta, Entra, Google) can react in their
Continuous Access Evaluation flows. Delivery is poll-based (RFC 8936) with
optional push to configured webhook receivers.

The whole point: instead of replacing the IdP, we become the *agent-behavior
signal source* the IdP ecosystem subscribes to.
"""
from __future__ import annotations

import time

import httpx

from app.auth.jwt_issuer import get_jwt_issuer
from app.config import settings

# CAEP standard event + a namespaced behavioral event (no CAEP type fits agent
# behavioral drift, so we define our own under our domain, alongside the standard
# session-revoked for revocations).
SESSION_REVOKED = "https://schemas.openid.net/secevent/caep/event-type/session-revoked"
BEHAVIORAL_ANOMALY = "https://worldofagents.dev/caep/event-type/behavioral-anomaly"

# In-memory delivery queue (per-process). A multi-instance deployment should back
# this with a shared store; documented as a follow-up.
_queue: list[dict] = []


def reset() -> None:
    _queue.clear()


def queue_size() -> int:
    return len(_queue)


def _subject(human) -> dict:
    """RFC 9493 subject identifier for the responsible human."""
    if getattr(human, "email", None):
        return {"format": "email", "email": human.email}
    return {"format": "opaque", "id": getattr(human, "clerk_id", "unknown")}


def emit(event_type: str, subject: dict, payload: dict) -> str | None:
    """Build, enqueue, and (best-effort) push a SET. Returns its jti, or None if
    SSF is disabled."""
    if not settings.SSF_ENABLED:
        return None
    now = int(time.time())
    event = {event_type: {"subject": subject, "event_timestamp": now, **payload}}
    issuer = get_jwt_issuer()
    token = issuer.issue_set(event, audience=settings.SSF_AUDIENCE)
    # jti is inside the signed token; decode-free tracking via a wrapper id is
    # unnecessary — we key the queue by the token's jti.
    jti = _jti_of(token)
    _queue.append({"jti": jti, "set": token, "event_type": event_type, "ts": now,
                   "subject": subject, "payload": payload})
    _push(token)
    return jti


def emit_behavioral_anomaly(human, agent_id: str, agent_name: str, score: float, reason: str) -> str | None:
    return emit(BEHAVIORAL_ANOMALY, _subject(human), {
        "actor": {"format": "opaque", "id": agent_id},
        "agent_name": agent_name,
        "similarity_score": score,
        "reason": reason,
    })


def emit_session_revoked(human, agent_id: str, agent_name: str) -> str | None:
    return emit(SESSION_REVOKED, _subject(human), {
        "actor": {"format": "opaque", "id": agent_id},
        "agent_name": agent_name,
        "reason": "admin_revocation",
    })


def poll(max_events: int = 100, acks: list[str] | None = None) -> dict:
    """RFC 8936 poll delivery: ack removes delivered SETs, then return up to
    max_events queued SETs as {jti: set_jwt}."""
    if acks:
        ackset = set(acks)
        _queue[:] = [e for e in _queue if e["jti"] not in ackset]
    batch = _queue[:max_events]
    return {e["jti"]: e["set"] for e in batch}


def _jti_of(token: str) -> str:
    import base64
    import json

    payload_b64 = token.split(".")[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_b64))["jti"]


def _push(token: str) -> None:
    """Best-effort push to configured webhook receivers. Failures are swallowed
    so a bad receiver never breaks the triggering request."""
    for url in settings.ssf_receiver_webhooks_list:
        try:
            httpx.post(url, content=token,
                       headers={"Content-Type": "application/secevent+jwt"}, timeout=2.0)
        except Exception:
            pass
