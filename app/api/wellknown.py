import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_issuer import get_jwt_issuer
from app.database import get_db
from app.models.agent import Agent
from app.models.human import Human
from app.models.verification_log import VerificationLog
from app.schemas.agent import AgentPublicProfile

router = APIRouter(tags=["well-known"])


@router.get("/.well-known/jwks.json")
async def jwks():
    issuer = get_jwt_issuer()
    return JSONResponse(
        content=issuer.jwks(),
        headers={"Cache-Control": "max-age=3600"},
    )


@router.get("/agents/{agent_id}/public")
async def public_profile(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AgentPublicProfile:
    result = await db.execute(
        select(Agent, Human.display_name)
        .join(Human, Agent.human_id == Human.id)
        .where(Agent.id == agent_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent, owner_name = row
    if agent.status == "revoked":
        raise HTTPException(status_code=404, detail="Agent not found")

    stats = await db.execute(
        select(
            func.count(VerificationLog.id),
            func.avg(VerificationLog.similarity_score),
        ).where(VerificationLog.agent_id == agent_id)
    )
    count, avg_score = stats.one()

    return AgentPublicProfile(
        agent_id=agent.id,
        name=agent.name,
        description=agent.description,
        status=agent.status,
        owner_display_name=owner_name,
        created_at=agent.created_at,
        verification_count=count or 0,
        avg_similarity_score=round(float(avg_score), 4) if avg_score else None,
    )
