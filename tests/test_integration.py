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
    {"type": "message", "name": "assistant", "content": "Here is the result from the file."},
    {"type": "tool_call", "name": "write_file"},
    {"type": "message", "name": "assistant", "content": "File updated successfully."},
]

DIFFERENT_TRAJECTORY = [
    {"type": "action", "name": "deploy"},
    {"type": "action", "name": "monitor"},
    {"type": "action", "name": "rollback"},
    {"type": "message", "name": "system", "content": "Deployment failed, rolling back."},
    {"type": "action", "name": "cleanup"},
]


def _make_auth_override(db_session, clerk_id, name, email):
    async def override():
        return await get_or_create_human(db_session, clerk_id, name, email)
    return override


@pytest.fixture
async def setup(db_session):
    clerk_a = f"clerk_{uuid.uuid4().hex[:12]}"
    clerk_b = f"clerk_{uuid.uuid4().hex[:12]}"

    class Ctx:
        pass

    ctx = Ctx()
    ctx.db = db_session
    ctx.clerk_a = clerk_a
    ctx.clerk_b = clerk_b

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db

    transport = ASGITransport(app=app)
    ctx.open_client = AsyncClient(transport=transport, base_url="http://test")

    yield ctx

    await ctx.open_client.aclose()
    app.dependency_overrides.clear()


def _set_human(setup, clerk_id, name, email):
    app.dependency_overrides[get_current_human] = _make_auth_override(
        setup.db, clerk_id, name, email
    )


@pytest.mark.asyncio
async def test_full_registration_verification_flow(setup):
    _set_human(setup, setup.clerk_a, "Alice", "alice@test.com")
    client = setup.open_client

    reg = await client.post("/agents/register", json={
        "name": "alice-agent",
        "sample_trajectory": SAMPLE_TRAJECTORY,
    })
    assert reg.status_code == 201
    agent_id = reg.json()["agent_id"]
    agent_key = reg.json()["agent_key"]

    verify_resp = await client.post("/verify", json={
        "agent_id": agent_id,
        "agent_key": agent_key,
        "trajectory": SAMPLE_TRAJECTORY,
    })
    assert verify_resp.status_code == 200
    body = verify_resp.json()
    assert body["verified"] is True
    assert body["verdict"] == "pass"

    token = body["token"]
    issuer = get_jwt_issuer()
    decoded = pyjwt.decode(token, issuer.public_key, algorithms=["RS256"])
    assert decoded["iss"] == "agentverify"
    assert decoded["act"]["sub"] == agent_id

    jwks_resp = await client.get("/.well-known/jwks.json")
    assert jwks_resp.status_code == 200
    assert len(jwks_resp.json()["keys"]) >= 1

    profile = await client.get(f"/agents/{agent_id}/public")
    assert profile.status_code == 200
    assert profile.json()["verification_count"] == 1


@pytest.mark.asyncio
async def test_refine_maintains_verification(setup):
    _set_human(setup, setup.clerk_a, "Alice", "alice@test.com")
    client = setup.open_client

    reg = await client.post("/agents/register", json={
        "name": "refine-agent",
        "sample_trajectory": SAMPLE_TRAJECTORY,
    })
    agent_id = reg.json()["agent_id"]
    agent_key = reg.json()["agent_key"]

    v1 = await client.post("/verify", json={
        "agent_id": agent_id, "agent_key": agent_key, "trajectory": SAMPLE_TRAJECTORY,
    })
    score_before = v1.json()["similarity_score"]

    await client.post(f"/agents/{agent_id}/refine", json={
        "trajectory": SAMPLE_TRAJECTORY,
    })

    v2 = await client.post("/verify", json={
        "agent_id": agent_id, "agent_key": agent_key, "trajectory": SAMPLE_TRAJECTORY,
    })
    score_after = v2.json()["similarity_score"]
    assert score_after >= score_before - 0.1


@pytest.mark.asyncio
async def test_key_rotation_invalidates_old_key(setup):
    _set_human(setup, setup.clerk_a, "Alice", "alice@test.com")
    client = setup.open_client

    reg = await client.post("/agents/register", json={
        "name": "rotate-agent",
        "sample_trajectory": SAMPLE_TRAJECTORY,
    })
    agent_id = reg.json()["agent_id"]
    old_key = reg.json()["agent_key"]

    v1 = await client.post("/verify", json={
        "agent_id": agent_id, "agent_key": old_key, "trajectory": SAMPLE_TRAJECTORY,
    })
    assert v1.json()["verified"] is True

    rotate = await client.post(f"/agents/{agent_id}/rotate-key")
    new_key = rotate.json()["agent_key"]

    v_old = await client.post("/verify", json={
        "agent_id": agent_id, "agent_key": old_key, "trajectory": SAMPLE_TRAJECTORY,
    })
    assert v_old.status_code == 401

    v_new = await client.post("/verify", json={
        "agent_id": agent_id, "agent_key": new_key, "trajectory": SAMPLE_TRAJECTORY,
    })
    assert v_new.json()["verified"] is True


@pytest.mark.asyncio
async def test_revocation_blocks_verification(setup):
    _set_human(setup, setup.clerk_a, "Alice", "alice@test.com")
    client = setup.open_client

    reg = await client.post("/agents/register", json={
        "name": "revoke-agent",
        "sample_trajectory": SAMPLE_TRAJECTORY,
    })
    agent_id = reg.json()["agent_id"]
    agent_key = reg.json()["agent_key"]

    await client.delete(f"/agents/{agent_id}")

    v = await client.post("/verify", json={
        "agent_id": agent_id, "agent_key": agent_key, "trajectory": SAMPLE_TRAJECTORY,
    })
    assert v.status_code == 404

    p = await client.get(f"/agents/{agent_id}/public")
    assert p.status_code == 404

    get_resp = await client.get(f"/agents/{agent_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "revoked"


@pytest.mark.asyncio
async def test_compare_standalone(setup):
    client = setup.open_client

    r1 = await client.post("/compare", json={
        "trajectory_a": SAMPLE_TRAJECTORY,
        "trajectory_b": SAMPLE_TRAJECTORY,
    })
    assert r1.json()["similarity_score"] >= 0.9

    r2 = await client.post("/compare", json={
        "trajectory_a": SAMPLE_TRAJECTORY,
        "trajectory_b": DIFFERENT_TRAJECTORY,
    })
    assert r2.json()["similarity_score"] < 0.6


@pytest.mark.asyncio
async def test_multi_human_isolation(setup):
    client = setup.open_client

    _set_human(setup, setup.clerk_a, "Alice", "alice@test.com")
    reg_a = await client.post("/agents/register", json={
        "name": "alice-agent",
        "sample_trajectory": SAMPLE_TRAJECTORY,
    })
    agent_a_id = reg_a.json()["agent_id"]
    agent_a_key = reg_a.json()["agent_key"]

    _set_human(setup, setup.clerk_b, "Bob", "bob@test.com")
    reg_b = await client.post("/agents/register", json={
        "name": "bob-agent",
        "sample_trajectory": SAMPLE_TRAJECTORY,
    })
    agent_b_id = reg_b.json()["agent_id"]

    list_b = await client.get("/agents")
    agent_ids = [a["agent_id"] for a in list_b.json()["agents"]]
    assert agent_b_id in agent_ids
    assert agent_a_id not in agent_ids

    get_a = await client.get(f"/agents/{agent_a_id}")
    assert get_a.status_code == 404

    del_a = await client.delete(f"/agents/{agent_a_id}")
    assert del_a.status_code == 404

    v = await client.post("/verify", json={
        "agent_id": agent_a_id, "agent_key": agent_a_key, "trajectory": SAMPLE_TRAJECTORY,
    })
    assert v.status_code == 200
    assert v.json()["verified"] is True


@pytest.mark.asyncio
async def test_verification_logging_stats(setup):
    _set_human(setup, setup.clerk_a, "Alice", "alice@test.com")
    client = setup.open_client

    reg = await client.post("/agents/register", json={
        "name": "stats-agent",
        "sample_trajectory": SAMPLE_TRAJECTORY,
    })
    agent_id = reg.json()["agent_id"]
    agent_key = reg.json()["agent_key"]

    for _ in range(3):
        await client.post("/verify", json={
            "agent_id": agent_id, "agent_key": agent_key, "trajectory": SAMPLE_TRAJECTORY,
        })

    profile = await client.get(f"/agents/{agent_id}/public")
    assert profile.status_code == 200
    body = profile.json()
    assert body["verification_count"] == 3
    assert body["avg_similarity_score"] is not None
    assert body["avg_similarity_score"] > 0.7
