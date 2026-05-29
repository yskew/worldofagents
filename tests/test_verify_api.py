import uuid

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.clerk import get_current_human
from app.auth.jwt_issuer import get_jwt_issuer
from app.database import get_db
from app.main import app
from app.services.human_service import get_or_create_human

SAMPLE_TRAJECTORY = [
    {"type": "tool_call", "name": "search"},
    {"type": "tool_call", "name": "read_file"},
    {"type": "message", "name": "assistant", "content": "Here is the result."},
    {"type": "tool_call", "name": "write_file"},
]

DIFFERENT_TRAJECTORY = [
    {"type": "action", "name": "deploy"},
    {"type": "action", "name": "monitor"},
    {"type": "message", "name": "system", "content": "Deployment complete."},
    {"type": "action", "name": "rollback"},
    {"type": "action", "name": "cleanup"},
]


async def _register_agent(auth_client, trajectory=None):
    resp = await auth_client.post("/agents/register", json={
        "name": "verify-test",
        "sample_trajectory": trajectory or SAMPLE_TRAJECTORY,
    })
    body = resp.json()
    return body["agent_id"], body["agent_key"]


@pytest.fixture
async def auth_client(db_session):
    clerk_id = f"clerk_{uuid.uuid4().hex[:12]}"

    async def override_get_current_human():
        return await get_or_create_human(db_session, clerk_id, "Verifier", "v@example.com")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_current_human] = override_get_current_human
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def open_client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_verify_valid_agent_passes(auth_client, open_client):
    agent_id, agent_key = await _register_agent(auth_client)

    resp = await open_client.post("/verify", json={
        "agent_id": agent_id,
        "agent_key": agent_key,
        "trajectory": SAMPLE_TRAJECTORY,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True
    assert body["verdict"] == "pass"
    assert body["token"] is not None
    assert body["similarity_score"] >= 0.7


@pytest.mark.asyncio
async def test_verify_invalid_key_rejected(auth_client, open_client):
    agent_id, _ = await _register_agent(auth_client)

    resp = await open_client.post("/verify", json={
        "agent_id": agent_id,
        "agent_key": "wrong-key-entirely",
        "trajectory": SAMPLE_TRAJECTORY,
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_verify_revoked_agent_rejected(auth_client, open_client):
    agent_id, agent_key = await _register_agent(auth_client)
    await auth_client.delete(f"/agents/{agent_id}")

    resp = await open_client.post("/verify", json={
        "agent_id": agent_id,
        "agent_key": agent_key,
        "trajectory": SAMPLE_TRAJECTORY,
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_verify_jwt_has_correct_claims(auth_client, open_client):
    agent_id, agent_key = await _register_agent(auth_client)

    resp = await open_client.post("/verify", json={
        "agent_id": agent_id,
        "agent_key": agent_key,
        "trajectory": SAMPLE_TRAJECTORY,
    })
    token = resp.json()["token"]
    issuer = get_jwt_issuer()
    decoded = pyjwt.decode(token, issuer.public_key, algorithms=["RS256"])

    assert decoded["iss"] == "agentverify"
    assert "sub" in decoded
    assert decoded["act"]["sub"] == agent_id
    assert "similarity_score" in decoded
    assert "jti" in decoded


@pytest.mark.asyncio
async def test_verify_different_trajectory(auth_client, open_client):
    agent_id, agent_key = await _register_agent(auth_client)

    resp = await open_client.post("/verify", json={
        "agent_id": agent_id,
        "agent_key": agent_key,
        "trajectory": DIFFERENT_TRAJECTORY,
    })
    body = resp.json()
    assert body["verdict"] in ("fail", "warning")
    assert body["similarity_score"] < 0.7
