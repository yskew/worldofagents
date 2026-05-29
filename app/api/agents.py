import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk import get_current_human
from app.database import get_db
from app.models.human import Human
from app.schemas.agent import (
    AgentDetailResponse,
    AgentListResponse,
    AgentRefineRequest,
    AgentRegisterRequest,
    AgentRegisterResponse,
)
from app.services import agent_service

router = APIRouter(prefix="/agents", tags=["agents"])


def _agent_detail(agent) -> AgentDetailResponse:
    sig_summary = None
    if agent.signature:
        sig_summary = {
            "tool_count": len(agent.signature.get("tool_call_histogram", {})),
            "sequence_length": agent.signature.get("structural_features", {}).get("sequence_length"),
        }
    return AgentDetailResponse(
        agent_id=agent.id,
        name=agent.name,
        description=agent.description,
        status=agent.status,
        signature_summary=sig_summary,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.post("/register", status_code=201)
async def register_agent(
    request: AgentRegisterRequest,
    human: Human = Depends(get_current_human),
    db: AsyncSession = Depends(get_db),
) -> AgentRegisterResponse:
    agent, plain_key = await agent_service.register_agent(db, human, request)
    return AgentRegisterResponse(
        agent_id=agent.id,
        agent_key=plain_key,
        name=agent.name,
        status=agent.status,
    )


@router.get("")
async def list_agents(
    human: Human = Depends(get_current_human),
    db: AsyncSession = Depends(get_db),
) -> AgentListResponse:
    agents = await agent_service.list_agents(db, human.id)
    return AgentListResponse(agents=[_agent_detail(a) for a in agents])


@router.get("/{agent_id}")
async def get_agent(
    agent_id: uuid.UUID,
    human: Human = Depends(get_current_human),
    db: AsyncSession = Depends(get_db),
) -> AgentDetailResponse:
    agent = await agent_service.get_agent(db, agent_id, human.id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _agent_detail(agent)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: uuid.UUID,
    human: Human = Depends(get_current_human),
    db: AsyncSession = Depends(get_db),
):
    success = await agent_service.delete_agent(db, agent_id, human.id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.post("/{agent_id}/refine")
async def refine_agent(
    agent_id: uuid.UUID,
    request: AgentRefineRequest,
    human: Human = Depends(get_current_human),
    db: AsyncSession = Depends(get_db),
) -> AgentDetailResponse:
    agent = await agent_service.refine_agent(db, agent_id, human.id, request)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _agent_detail(agent)


@router.post("/{agent_id}/rotate-key")
async def rotate_key(
    agent_id: uuid.UUID,
    human: Human = Depends(get_current_human),
    db: AsyncSession = Depends(get_db),
):
    new_key = await agent_service.rotate_key(db, agent_id, human.id)
    if new_key is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent_key": new_key}
