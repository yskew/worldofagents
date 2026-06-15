import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.agent_keys import create_agent_credentials
from app.config import settings
from app.models.agent import Agent
from app.models.human import Human
from app.schemas.agent import AgentRegisterRequest, AgentRefineRequest
from app.services.signature_engine import extract_features, features_to_vector, merge_features


def _current_vector_version() -> int:
    return 2 if settings.VECTOR_ENCODING_V2 else 1


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
        signature_version=_current_vector_version(),
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
    agent.signature_version = _current_vector_version()
    await db.commit()
    await db.refresh(agent)
    return agent


async def set_challenge_profile(
    db: AsyncSession, agent_id: uuid.UUID, human_id: uuid.UUID, responses: dict
) -> list[str] | None:
    """Store per-probe response signatures (RFC 0008). Returns the profiled probe
    ids, or None if the agent is not found / revoked."""
    agent = await get_agent(db, agent_id, human_id)
    if agent is None or agent.status == "revoked":
        return None
    profile = {
        probe_id: extract_features(trajectory)
        for probe_id, trajectory in responses.items()
    }
    agent.challenge_profile = profile
    await db.commit()
    return sorted(profile.keys())


async def set_allowed_scopes(
    db: AsyncSession, agent_id: uuid.UUID, human_id: uuid.UUID, scopes: list[str]
) -> list[str] | None:
    """Set the scopes this agent may request via the token-exchange broker (RFC
    0009). Returns the stored scopes, or None if not found / revoked."""
    agent = await get_agent(db, agent_id, human_id)
    if agent is None or agent.status == "revoked":
        return None
    agent.allowed_scopes = sorted(set(scopes))
    await db.commit()
    return agent.allowed_scopes


async def rotate_key(db: AsyncSession, agent_id: uuid.UUID, human_id: uuid.UUID) -> str | None:
    agent = await get_agent(db, agent_id, human_id)
    if agent is None or agent.status == "revoked":
        return None

    plain_key, key_hash, key_salt = create_agent_credentials()
    agent.key_hash = key_hash
    agent.key_salt = key_salt
    await db.commit()
    return plain_key
