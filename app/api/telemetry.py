"""Telemetry ingestion endpoint (RFC 0010).

Accepts agent execution traces (OTel / Langfuse / Braintrust), maps them to a
trajectory, and enriches the agent's behavioral signature from real runtime
behavior. Authenticated with the agent key (so the agent's own runtime can push
telemetry without a human session); Clerk is untouched. Raw spans are not
persisted, only derived signature features.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.agent_keys import verify_agent_credentials
from app.config import settings
from app.database import get_db
from app.models.agent import Agent
from app.ratelimit import rate_limit
from app.schemas.verify import TelemetryIngestRequest, TelemetryIngestResponse
from app.services import agent_service, telemetry

router = APIRouter(tags=["telemetry"])


@router.post("/telemetry/ingest", dependencies=[Depends(rate_limit)])
async def ingest_telemetry(
    body: TelemetryIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> TelemetryIngestResponse:
    if not settings.TELEMETRY_ENABLED:
        raise HTTPException(status_code=503, detail="Telemetry ingestion disabled")

    agent = (await db.execute(select(Agent).where(Agent.id == body.agent_id))).scalar_one_or_none()
    if agent is None or agent.status == "revoked":
        raise HTTPException(status_code=404, detail="Agent not found or revoked")
    if not verify_agent_credentials(body.agent_key, agent.key_hash):
        raise HTTPException(status_code=401, detail="Invalid agent key")

    trajectory = telemetry.map_spans(body.source, body.spans)
    if not trajectory:
        raise HTTPException(status_code=422, detail="No mappable spans in payload")

    summary = telemetry.summarize(trajectory)

    applied = False
    if body.apply:
        await agent_service.enrich_signature_from_trajectory(db, agent, trajectory)
        applied = True

    return TelemetryIngestResponse(
        source=body.source,
        ingested_spans=len(body.spans),
        mapped_steps=len(trajectory),
        summary=summary,
        applied=applied,
    )
