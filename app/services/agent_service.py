import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.agent_keys import create_agent_credentials
from app.models.agent import Agent
from app.models.human import Human
from app.schemas.agent import AgentRegisterRequest, AgentRefineRequest
from app.services.signature_engine import extract_features, features_to_vector, merge_features


async def register_agent(
    db: AsyncSession, human: Human, request: AgentRegisterRequest
) -> tuple[Agent, str]:
    plain_key, key_hash, key_salt = create_agent_credentials()
    signature = extract_features(request.sample_trajectory)
    sig_vector = features_to_vector(signature)

    agent = Agent(
        human_id=human.id,
        name=request.name,
        description=request.description,
        key_hash=key_hash,
        key_salt=key_salt,
        signature=signature,
        signature_vector=sig_vector,
        status="active",
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent, plain_key


async def list_agents(db: AsyncSession, human_id: uuid.UUID) -> list[Agent]:
    result = await db.execute(
        select(Agent).where(Agent.human_id == human_id).order_by(Agent.created_at.desc())
    )
    return list(result.scalars().all())


async def get_agent(db: AsyncSession, agent_id: uuid.UUID, human_id: uuid.UUID) -> Agent | None:
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.human_id == human_id)
    )
    return result.scalar_one_or_none()


async def delete_agent(db: AsyncSession, agent_id: uuid.UUID, human_id: uuid.UUID) -> bool:
    agent = await get_agent(db, agent_id, human_id)
    if agent is None:
        return False
    agent.status = "revoked"
    await db.commit()
    return True


async def refine_agent(
    db: AsyncSession, agent_id: uuid.UUID, human_id: uuid.UUID, request: AgentRefineRequest
) -> Agent | None:
    agent = await get_agent(db, agent_id, human_id)
    if agent is None or agent.status == "revoked":
        return None

    new_features = extract_features(request.trajectory)
    existing = agent.signature or {}
    merged = merge_features(existing, new_features)
    agent.signature = merged
    agent.signature_vector = features_to_vector(merged)
    await db.commit()
    await db.refresh(agent)
    return agent


async def set_tool_allowlist(
    db: AsyncSession, agent_id: uuid.UUID, human_id: uuid.UUID, tools: list[str]
) -> list[str] | None:
    """Set the MCP tools this agent may call (RFC 0012)."""
    agent = await get_agent(db, agent_id, human_id)
    if agent is None or agent.status == "revoked":
        return None
    agent.tool_allowlist = sorted(set(tools))
    await db.commit()
    return agent.tool_allowlist


async def rotate_key(db: AsyncSession, agent_id: uuid.UUID, human_id: uuid.UUID) -> str | None:
    agent = await get_agent(db, agent_id, human_id)
    if agent is None or agent.status == "revoked":
        return None

    plain_key, key_hash, key_salt = create_agent_credentials()
    agent.key_hash = key_hash
    agent.key_salt = key_salt
    await db.commit()
    return plain_key
