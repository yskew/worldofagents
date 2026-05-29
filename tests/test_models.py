import uuid

import pytest

from app.models.agent import Agent
from app.models.human import Human
from app.models.verification_log import VerificationLog


def _uid():
    return f"clerk_{uuid.uuid4().hex[:12]}"


@pytest.mark.asyncio
async def test_create_human(db_session):
    human = Human(clerk_id=_uid(), display_name="Alice", email="alice@example.com")
    db_session.add(human)
    await db_session.commit()
    await db_session.refresh(human)

    assert isinstance(human.id, uuid.UUID)
    assert human.display_name == "Alice"
    assert human.created_at is not None


@pytest.mark.asyncio
async def test_create_agent(db_session):
    human = Human(clerk_id=_uid(), display_name="Bob")
    db_session.add(human)
    await db_session.commit()
    await db_session.refresh(human)

    agent = Agent(
        human_id=human.id,
        name="test-agent",
        description="A test agent",
        key_hash="fakehash",
        key_salt="fakesalt",
        status="active",
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    assert isinstance(agent.id, uuid.UUID)
    assert agent.human_id == human.id
    assert agent.name == "test-agent"
    assert agent.status == "active"


@pytest.mark.asyncio
async def test_create_verification_log(db_session):
    human = Human(clerk_id=_uid(), display_name="Charlie")
    db_session.add(human)
    await db_session.commit()
    await db_session.refresh(human)

    agent = Agent(
        human_id=human.id, name="log-agent", key_hash="h", key_salt="s", status="active"
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    log = VerificationLog(
        agent_id=agent.id, similarity_score=0.85, passed=True, ip_address="127.0.0.1"
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    assert isinstance(log.id, uuid.UUID)
    assert log.similarity_score == 0.85
    assert log.passed is True
    assert log.requested_at is not None


@pytest.mark.asyncio
async def test_agent_status_default(db_session):
    human = Human(clerk_id=_uid(), display_name="Default")
    db_session.add(human)
    await db_session.commit()
    await db_session.refresh(human)

    agent = Agent(human_id=human.id, name="default-agent", key_hash="h", key_salt="s")
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    assert agent.status == "active"


@pytest.mark.asyncio
async def test_signature_vector_dimension(db_session):
    human = Human(clerk_id=_uid(), display_name="Vector")
    db_session.add(human)
    await db_session.commit()
    await db_session.refresh(human)

    vec = [float(i) / 256 for i in range(256)]
    agent = Agent(
        human_id=human.id,
        name="vec-agent",
        key_hash="h",
        key_salt="s",
        signature_vector=vec,
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    assert agent.signature_vector is not None
    assert len(agent.signature_vector) == 256
