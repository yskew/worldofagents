"""Shared Signals Framework transmitter endpoints (RFC 0011)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.schemas.ssf import PollRequest, PollResponse
from app.services import ssf

router = APIRouter(tags=["shared-signals"])


@router.get("/.well-known/ssf-configuration")
async def ssf_configuration() -> dict:
    """Transmitter metadata so receivers can discover delivery + supported events."""
    return {
        "issuer": settings.JWT_ISSUER,
        "jwks_uri": "/.well-known/jwks.json",
        "configuration_endpoint": "/.well-known/ssf-configuration",
        "delivery_methods_supported": [
            "urn:ietf:rfc:8936",  # poll-based
            "urn:ietf:rfc:8935",  # push-based
        ],
        "events_supported": [ssf.BEHAVIORAL_ANOMALY, ssf.SESSION_REVOKED],
    }


@router.post("/ssf/poll")
async def ssf_poll(body: PollRequest) -> PollResponse:
    """RFC 8936 poll delivery: acknowledge prior SETs, receive queued ones."""
    if not settings.SSF_ENABLED:
        raise HTTPException(status_code=503, detail="Shared Signals disabled")
    sets = ssf.poll(max_events=body.maxEvents, acks=body.ack)
    return PollResponse(sets=sets)
