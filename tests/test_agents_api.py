import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.clerk import get_current_human
from app.database import get_db
from app.main import app
from app.models.human import Human
from app.services.human_service import get_or_create_human

SAMPLE_TRAJECTORY = [
    {"type": "tool_call", "name": "search"},
    {"type": "tool_call", "name": "read_file"},
    {"type": "message", "name": "assistant", "content": "Here is the result."},
    {"type": "tool_call", "name": "write_file"},
]


@pytest.fixture
async def auth_client(db_session):
    clerk_id = f"clerk_{uuid.uuid4().hex[:12]}"

    async def override_get_current_human():
        return await get_or_create_human(db_session, clerk_id, "Test User", "test@example.com")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_current_human] = override_get_current_human
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_client_b(db_session):
    clerk_id = f"clerk_{uuid.uuid4().hex[:12]}"

    async def override_get_current_human():
        return await get_or_create_human(db_session, clerk_id, "Other User", "other@example.com")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_current_human] = override_get_current_human
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_agent(auth_client):
    resp = await auth_client.post("/agents/register", json={
        "name": "my-agent",
        "description": "A test agent",
        "sample_trajectory": SAMPLE_TRAJECTORY,
    })
    assert resp.status_code == 201
    body = resp.json()
    assert "agent_id" in body
    assert "agent_key" in body
    assert body["name"] == "my-agent"
    assert body["status"] == "active"


@pytest.mark.asyncio
async def test_register_returns_key_once(auth_client):
    resp = await auth_client.post("/agents/register", json={
        "name": "key-once",
        "sample_trajectory": SAMPLE_TRAJECTORY,
    })
    agent_id = resp.json()["agent_id"]

    get_resp = await auth_client.get(f"/agents/{agent_id}")
    assert get_resp.status_code == 200
    assert "agent_key" not in get_resp.json()


@pytest.mark.asyncio
async def test_list_agents(auth_client):
    await auth_client.post("/agents/register", json={"name": "a1", "sample_trajectory": SAMPLE_TRAJECTORY})
    await auth_client.post("/agents/register", json={"name": "a2", "sample_trajectory": SAMPLE_TRAJECTORY})

    resp = await auth_client.get("/agents")
    assert resp.status_code == 200
    assert len(resp.json()["agents"]) == 2


@pytest.mark.asyncio
async def test_get_agent(auth_client):
    reg = await auth_client.post("/agents/register", json={"name": "detail", "sample_trajectory": SAMPLE_TRAJECTORY})
    agent_id = reg.json()["agent_id"]

    resp = await auth_client.get(f"/agents/{agent_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "detail"


@pytest.mark.asyncio
async def test_delete_agent(auth_client):
    reg = await auth_client.post("/agents/register", json={"name": "to-delete", "sample_trajectory": SAMPLE_TRAJECTORY})
    agent_id = reg.json()["agent_id"]

    del_resp = await auth_client.delete(f"/agents/{agent_id}")
    assert del_resp.status_code == 204

    get_resp = await auth_client.get(f"/agents/{agent_id}")
    assert get_resp.json()["status"] == "revoked"


@pytest.mark.asyncio
async def test_refine_agent(auth_client):
    reg = await auth_client.post("/agents/register", json={"name": "refine-me", "sample_trajectory": SAMPLE_TRAJECTORY})
    agent_id = reg.json()["agent_id"]

    resp = await auth_client.post(f"/agents/{agent_id}/refine", json={
        "trajectory": [
            {"type": "tool_call", "name": "search"},
            {"type": "tool_call", "name": "read_file"},
            {"type": "message", "name": "assistant", "content": "Additional data point."},
        ],
    })
    assert resp.status_code == 200
    assert resp.json()["signature_summary"] is not None


@pytest.mark.asyncio
async def test_rotate_key(auth_client):
    reg = await auth_client.post("/agents/register", json={"name": "rotate-me", "sample_trajectory": SAMPLE_TRAJECTORY})
    agent_id = reg.json()["agent_id"]

    resp = await auth_client.post(f"/agents/{agent_id}/rotate-key")
    assert resp.status_code == 200
    new_key = resp.json()["agent_key"]
    assert len(new_key) >= 40


@pytest.mark.asyncio
async def test_register_invalid_trajectory(auth_client):
    resp = await auth_client.post("/agents/register", json={
        "name": "bad-agent",
        "sample_trajectory": [],
    })
    assert resp.status_code == 422
