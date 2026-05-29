import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

TRAJ_A = [
    {"type": "tool_call", "name": "search"},
    {"type": "tool_call", "name": "read_file"},
    {"type": "message", "name": "assistant", "content": "Here is the result."},
    {"type": "tool_call", "name": "write_file"},
]

TRAJ_B = [
    {"type": "action", "name": "deploy"},
    {"type": "action", "name": "monitor"},
    {"type": "message", "name": "system", "content": "Deployment complete."},
    {"type": "action", "name": "rollback"},
]


@pytest.fixture
async def open_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_compare_identical_trajectories(open_client):
    resp = await open_client.post("/compare", json={
        "trajectory_a": TRAJ_A,
        "trajectory_b": TRAJ_A,
    })
    assert resp.status_code == 200
    assert resp.json()["similarity_score"] >= 0.9


@pytest.mark.asyncio
async def test_compare_different_trajectories(open_client):
    resp = await open_client.post("/compare", json={
        "trajectory_a": TRAJ_A,
        "trajectory_b": TRAJ_B,
    })
    assert resp.status_code == 200
    assert resp.json()["similarity_score"] < 0.6


@pytest.mark.asyncio
async def test_compare_returns_breakdown(open_client):
    resp = await open_client.post("/compare", json={
        "trajectory_a": TRAJ_A,
        "trajectory_b": TRAJ_A,
    })
    breakdown = resp.json()["breakdown"]
    assert "jsd_score" in breakdown
    assert "cosine_score" in breakdown
    assert "markov_score" in breakdown
    assert "stats_score" in breakdown


@pytest.mark.asyncio
async def test_compare_no_auth_required(open_client):
    resp = await open_client.post("/compare", json={
        "trajectory_a": TRAJ_A,
        "trajectory_b": TRAJ_B,
    })
    assert resp.status_code == 200
