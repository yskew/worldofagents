"""RFC 0005 — /similar endpoint (pgvector ANN + ensemble re-rank)."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.clerk import get_current_human
from app.database import get_db
from app.main import app
from app.services.human_service import get_or_create_human

CODING = [
    {"type": "tool_call", "name": "search"},
    {"type": "tool_call", "name": "read_file"},
    {"type": "message", "name": "assistant", "content": "Found the file, editing now."},
    {"type": "tool_call", "name": "edit_file"},
    {"type": "tool_call", "name": "run_tests"},
]
DEVOPS = [
    {"type": "action", "name": "deploy"},
    {"type": "action", "name": "health_check"},
    {"type": "action", "name": "monitor"},
    {"type": "action", "name": "rollback"},
]
RESEARCH = [
    {"type": "tool_call", "name": "web_search"},
    {"type": "tool_call", "name": "web_search"},
    {"type": "tool_call", "name": "read_page"},
    {"type": "tool_call", "name": "write_file"},
]


@pytest.fixture
async def auth_client(db_session):
    clerk_id = f"clerk_{uuid.uuid4().hex[:12]}"

    async def override_get_current_human():
        return await get_or_create_human(db_session, clerk_id, "Owner", "o@example.com")

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


async def _register(client, name, trajectory):
    resp = await client.post("/agents/register", json={"name": name, "sample_trajectory": trajectory})
    assert resp.status_code == 201
    return resp.json()["agent_id"]


@pytest.mark.asyncio
async def test_similar_ranks_matching_agent_first(auth_client, open_client):
    coding_id = await _register(auth_client, "coder", CODING)
    await _register(auth_client, "devops", DEVOPS)
    await _register(auth_client, "research", RESEARCH)

    resp = await open_client.post("/similar", json={"trajectory": CODING, "limit": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["results"]) == 3
    # the coding agent must be the top match for a coding-like trajectory
    assert body["results"][0]["agent_id"] == coding_id
    # results are sorted by ensemble score descending
    scores = [r["score"] for r in body["results"]]
    assert scores == sorted(scores, reverse=True)
    # each match carries owner + both signals
    top = body["results"][0]
    assert top["owner_display_name"] == "Owner"
    assert 0.0 <= top["vector_similarity"] <= 1.0


@pytest.mark.asyncio
async def test_similar_respects_limit(auth_client, open_client):
    for i in range(4):
        await _register(auth_client, f"coder-{i}", CODING)
    resp = await open_client.post("/similar", json={"trajectory": CODING, "limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 2


@pytest.mark.asyncio
async def test_similar_empty_when_no_agents(open_client):
    resp = await open_client.post("/similar", json={"trajectory": CODING})
    assert resp.status_code == 200
    assert resp.json()["results"] == []


@pytest.mark.asyncio
async def test_similar_requires_trajectory(open_client):
    resp = await open_client.post("/similar", json={"trajectory": []})
    assert resp.status_code == 422
