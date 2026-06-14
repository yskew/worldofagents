"""Continuous mid-session attestation endpoints (RFC 0013)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.agent_keys import verify_agent_credentials
from app.config import settings
from app.database import get_db
from app.models.agent import Agent
from app.schemas.attestation import (
    AttestStartRequest,
    AttestStartResponse,
    AttestStepRequest,
    AttestStepResponse,
)
from app.services import attestation

router = APIRouter(tags=["attestation"])


@router.post("/attest/start")
async def attest_start(
    body: AttestStartRequest,
    db: AsyncSession = Depends(get_db),
) -> AttestStartResponse:
    if not settings.ATTEST_ENABLED:
        raise HTTPException(status_code=503, detail="Attestation disabled")
    agent = (await db.execute(select(Agent).where(Agent.id == body.agent_id))).scalar_one_or_none()
    if agent is None or agent.status == "revoked":
        raise HTTPException(status_code=404, detail="Agent not found or revoked")
    if not verify_agent_credentials(body.agent_key, agent.key_hash):
        raise HTTPException(status_code=401, detail="Invalid agent key")
    return AttestStartResponse(session_id=attestation.start(agent))


@router.post("/attest/step")
async def attest_step(body: AttestStepRequest) -> AttestStepResponse:
    if not settings.ATTEST_ENABLED:
        raise HTTPException(status_code=503, detail="Attestation disabled")
    result = attestation.ingest(body.session_id, body.trajectory)
    if result is None:
        raise HTTPException(status_code=404, detail="Unknown attestation session")
    return AttestStepResponse(**result)
