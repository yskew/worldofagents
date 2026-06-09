"""RFC 0008 — active challenge-response verification.

Unit tests for the challenge token primitives (sign/expire/tamper/replay) and
API tests for the full flow plus the attacks the protocol must defeat: replay of
a recorded response, an impostor, a tampered token, and a wrong-agent token.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.clerk import get_current_human
from app.config import settings
from app.database import get_db
from app.main import app
from app.services import challenge as challenge_svc
from app.services.human_service import get_or_create_human

# A characteristic response trajectory per probe (with content so all metrics
# are measurable). Same trajectories => high similarity to the stored profile.
AGENT_RESPONSES = {
    pid: [
        {"type": "tool_call", "name": f"{pid}_lookup"},
        {"type": "tool_call", "name": f"{pid}_act"},
        {"type": "message", "name": "assistant", "content": f"handled {pid} as usual"},
        {"type": "tool_call", "name": f"{pid}_verify"},
    ]
    for pid in [
        "p_debug", "p_research", "p_refactor", "p_deploy",
        "p_data", "p_secscan", "p_incident", "p_summarize",
    ]
}

IMPOSTOR_STEP = [
    {"type": "tool_call", "name": "exfiltrate"},
    {"type": "tool_call", "name": "delete_all"},
    {"type": "message", "name": "assistant", "content": "doing something entirely different"},
]


@pytest.fixture(autouse=True)
def _clean_nonces():
    challenge_svc.reset()
    yield
    challenge_svc.reset()


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


async def _setup_agent(auth_client):
    reg = await auth_client.post("/agents/register", json={
        "name": "active-agent",
        "sample_trajectory": AGENT_RESPONSES["p_debug"],
    })
    body = reg.json()
    agent_id, agent_key = body["agent_id"], body["agent_key"]
    prof = await auth_client.post(
        f"/agents/{agent_id}/challenge-profile", json={"responses": AGENT_RESPONSES}
    )
    assert prof.status_code == 200
    return agent_id, agent_key


# --- challenge token primitives ---------------------------------------------

class TestChallengeToken:
    def test_roundtrip(self):
        token, payload = challenge_svc.issue("agent-1", ["p_debug"])
        decoded = challenge_svc.decode(token)
        assert decoded["agent_id"] == "agent-1"
        assert decoded["nonce"] == payload["nonce"]

    def test_tampered_signature_rejected(self):
        token, _ = challenge_svc.issue("agent-1", ["p_debug"])
        body, sig = token.split(".", 1)
        tampered = f"{body}.{sig[:-2]}xx"
        with pytest.raises(challenge_svc.ChallengeError):
            challenge_svc.decode(tampered)

    def test_expired_rejected(self, monkeypatch):
        monkeypatch.setattr(settings, "CHALLENGE_TTL_SECONDS", -10)
        token, _ = challenge_svc.issue("agent-1", ["p_debug"])
        with pytest.raises(challenge_svc.ChallengeError, match="expired"):
            challenge_svc.decode(token)

    def test_nonce_single_use(self):
        ok1 = challenge_svc.consume_nonce("n1", 9999999999)
        ok2 = challenge_svc.consume_nonce("n1", 9999999999)
        assert ok1 is True and ok2 is False


# --- full API flow + attacks ------------------------------------------------

class TestActiveVerificationFlow:
    @pytest.mark.asyncio
    async def test_happy_path_passes(self, auth_client, open_client):
        agent_id, agent_key = await _setup_agent(auth_client)
        ch = (await open_client.post("/challenge", json={"agent_id": agent_id})).json()
        responses = {p["id"]: AGENT_RESPONSES[p["id"]] for p in ch["probes"]}
        resp = await open_client.post("/verify/active", json={
            "agent_id": agent_id, "agent_key": agent_key,
            "challenge_token": ch["challenge_token"], "responses": responses,
        })
        body = resp.json()
        assert body["verified"] is True
        assert body["active_score"] >= settings.ACTIVE_VERIFICATION_PASS_THRESHOLD
        assert body["token"]  # delegated JWT issued

    @pytest.mark.asyncio
    async def test_replay_rejected(self, auth_client, open_client):
        """The core SOTA property: a recorded valid response cannot be replayed."""
        agent_id, agent_key = await _setup_agent(auth_client)
        ch = (await open_client.post("/challenge", json={"agent_id": agent_id})).json()
        responses = {p["id"]: AGENT_RESPONSES[p["id"]] for p in ch["probes"]}
        payload = {"agent_id": agent_id, "agent_key": agent_key,
                   "challenge_token": ch["challenge_token"], "responses": responses}
        first = await open_client.post("/verify/active", json=payload)
        assert first.json()["verified"] is True
        replay = await open_client.post("/verify/active", json=payload)
        assert replay.status_code == 409  # nonce already consumed

    @pytest.mark.asyncio
    async def test_impostor_fails(self, auth_client, open_client):
        agent_id, agent_key = await _setup_agent(auth_client)
        ch = (await open_client.post("/challenge", json={"agent_id": agent_id})).json()
        # correct key, but responses come from a different (impostor) behavior
        responses = {p["id"]: IMPOSTOR_STEP for p in ch["probes"]}
        resp = await open_client.post("/verify/active", json={
            "agent_id": agent_id, "agent_key": agent_key,
            "challenge_token": ch["challenge_token"], "responses": responses,
        })
        body = resp.json()
        assert body["verified"] is False
        assert body["token"] is None

    @pytest.mark.asyncio
    async def test_tampered_token_rejected(self, auth_client, open_client):
        agent_id, agent_key = await _setup_agent(auth_client)
        ch = (await open_client.post("/challenge", json={"agent_id": agent_id})).json()
        b, s = ch["challenge_token"].split(".", 1)
        responses = {p["id"]: AGENT_RESPONSES[p["id"]] for p in ch["probes"]}
        resp = await open_client.post("/verify/active", json={
            "agent_id": agent_id, "agent_key": agent_key,
            "challenge_token": f"{b}.{s[:-2]}xx", "responses": responses,
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_challenge_requires_profile(self, auth_client, open_client):
        reg = (await auth_client.post("/agents/register", json={
            "name": "no-profile", "sample_trajectory": AGENT_RESPONSES["p_debug"],
        })).json()
        resp = await open_client.post("/challenge", json={"agent_id": reg["agent_id"]})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_token_bound_to_agent(self, auth_client, open_client):
        agent_a, key_a = await _setup_agent(auth_client)
        ch = (await open_client.post("/challenge", json={"agent_id": agent_a})).json()
        other = uuid.uuid4()
        responses = {p["id"]: AGENT_RESPONSES[p["id"]] for p in ch["probes"]}
        resp = await open_client.post("/verify/active", json={
            "agent_id": str(other), "agent_key": key_a,
            "challenge_token": ch["challenge_token"], "responses": responses,
        })
        assert resp.status_code == 400  # challenge not issued for this agent
