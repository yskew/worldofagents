"""RFC 0013 — continuous mid-session attestation (CUSUM drift detection)."""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app
from app.services import attestation

CODING = [
    {"type": "tool_call", "name": "search"},
    {"type": "tool_call", "name": "read_file"},
    {"type": "message", "name": "assistant", "content": "fixing now"},
    {"type": "tool_call", "name": "edit_file"},
    {"type": "tool_call", "name": "run_tests"},
]
MALICIOUS = [
    {"type": "tool_call", "name": "exfiltrate"},
    {"type": "tool_call", "name": "delete_db"},
    {"type": "tool_call", "name": "disable_logging"},
]


@pytest.fixture(autouse=True)
def _clean():
    attestation.reset()
    yield
    attestation.reset()


@pytest.fixture
async def open_client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _start(open_client):
    reg = (await open_client.post("/agents/register", json={
        "name": "attest", "sample_trajectory": CODING})).json()
    start = (await open_client.post("/attest/start", json={
        "agent_id": reg["agent_id"], "agent_key": reg["agent_key"]})).json()
    return reg, start["session_id"]


async def _step(open_client, sid, traj):
    return await open_client.post("/attest/step", json={"session_id": sid, "trajectory": traj})


class TestSessionLifecycle:
    @pytest.mark.asyncio
    async def test_consistent_behavior_stays_ok(self, open_client):
        _, sid = await _start(open_client)
        last = None
        for _ in range(4):
            last = (await _step(open_client, sid, CODING)).json()
        assert last["status"] == "ok"
        assert last["cusum"] == 0.0
        assert last["windows"] == 4

    @pytest.mark.asyncio
    async def test_drift_raises_alarm(self, open_client):
        _, sid = await _start(open_client)
        statuses = []
        for _ in range(4):
            statuses.append((await _step(open_client, sid, MALICIOUS)).json()["status"])
        # sustained divergence must escalate to an alarm
        assert statuses[-1] == "alarm"
        assert "ok" != statuses[-1]

    @pytest.mark.asyncio
    async def test_invalid_key_rejected(self, open_client):
        reg = (await open_client.post("/agents/register", json={
            "name": "a", "sample_trajectory": CODING})).json()
        resp = await open_client.post("/attest/start", json={
            "agent_id": reg["agent_id"], "agent_key": "wrong"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unknown_session_404(self, open_client):
        resp = await _step(open_client, "nope", CODING)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_start_unknown_agent_404(self, open_client):
        resp = await open_client.post("/attest/start", json={
            "agent_id": str(uuid.uuid4()), "agent_key": "x"})
        assert resp.status_code == 404


class TestCusumUnit:
    def test_recovery_lowers_cusum(self):
        class _A:
            id = uuid.uuid4()
            signature = None
        # build a real baseline via the service using a registered-like agent
        from app.services.signature_engine import extract_features, features_to_vector
        from app.schemas.agent import TrajectoryStep
        base = extract_features([TrajectoryStep(**s) for s in CODING])
        sid = "s1"
        attestation._sessions[sid] = attestation.Session(
            agent_id="a", baseline=base, baseline_vec=features_to_vector(base))
        mal = [TrajectoryStep(**s) for s in MALICIOUS]
        good = [TrajectoryStep(**s) for s in CODING]
        for _ in range(3):
            attestation.ingest(sid, mal)
        high = attestation.get(sid).cusum
        for _ in range(3):
            attestation.ingest(sid, good)
        assert attestation.get(sid).cusum < high  # self-heals when behavior returns
