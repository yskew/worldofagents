"""RFC 0011 — Shared Signals / CAEP transmitter (SET signing, poll, hooks)."""
from __future__ import annotations

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.jwt_issuer import get_jwt_issuer
from app.config import settings
from app.database import get_db
from app.main import app
from app.services import ssf

CODING = [
    {"type": "tool_call", "name": "search"},
    {"type": "tool_call", "name": "read_file"},
    {"type": "message", "name": "assistant", "content": "found it, fixing now"},
    {"type": "tool_call", "name": "edit_file"},
]
DEVOPS = [
    {"type": "action", "name": "deploy"},
    {"type": "action", "name": "monitor"},
    {"type": "action", "name": "rollback"},
]


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    ssf.reset()
    monkeypatch.setattr(settings, "SSF_ENABLED", True)
    monkeypatch.setattr(settings, "SSF_RECEIVER_WEBHOOKS", "")  # no push in tests
    yield
    ssf.reset()


@pytest.fixture
async def open_client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


class _Human:
    email = "alice@example.com"
    clerk_id = "clerk_alice"


def _decode_set(token: str) -> dict:
    return jwt.decode(
        token, get_jwt_issuer().public_key, algorithms=["RS256"], audience=settings.SSF_AUDIENCE,
    )


class TestSetSigningAndQueue:
    def test_emit_builds_signed_caep_set(self):
        jti = ssf.emit_behavioral_anomaly(_Human(), "agent-1", "coder", 0.21, "verification_failed")
        assert jti
        token = ssf.poll()[jti]
        claims = _decode_set(token)
        assert claims["iss"] == settings.JWT_ISSUER
        assert ssf.BEHAVIORAL_ANOMALY in claims["events"]
        event = claims["events"][ssf.BEHAVIORAL_ANOMALY]
        assert event["subject"] == {"format": "email", "email": "alice@example.com"}
        assert event["actor"]["id"] == "agent-1"
        assert event["similarity_score"] == 0.21

    def test_session_revoked_event(self):
        jti = ssf.emit_session_revoked(_Human(), "agent-2", "devops")
        claims = _decode_set(ssf.poll()[jti])
        assert ssf.SESSION_REVOKED in claims["events"]

    def test_poll_ack_removes_delivered(self):
        jti = ssf.emit_session_revoked(_Human(), "a", "n")
        assert jti in ssf.poll()
        ssf.poll(acks=[jti])           # acknowledge
        assert ssf.queue_size() == 0   # removed

    def test_disabled_emits_nothing(self, monkeypatch):
        monkeypatch.setattr(settings, "SSF_ENABLED", False)
        assert ssf.emit_session_revoked(_Human(), "a", "n") is None


class TestEndpoints:
    @pytest.mark.asyncio
    async def test_ssf_configuration(self, open_client):
        resp = await open_client.get("/.well-known/ssf-configuration")
        assert resp.status_code == 200
        body = resp.json()
        assert body["issuer"] == settings.JWT_ISSUER
        assert ssf.BEHAVIORAL_ANOMALY in body["events_supported"]
        assert "urn:ietf:rfc:8936" in body["delivery_methods_supported"]

    @pytest.mark.asyncio
    async def test_poll_endpoint_delivers_and_acks(self, open_client):
        ssf.emit_session_revoked(_Human(), "a", "n")
        r1 = await open_client.post("/ssf/poll", json={"maxEvents": 10})
        sets = r1.json()["sets"]
        assert len(sets) == 1
        jti = next(iter(sets))
        await open_client.post("/ssf/poll", json={"ack": [jti]})
        r2 = await open_client.post("/ssf/poll", json={})
        assert r2.json()["sets"] == {}


class TestVerificationHooks:
    @pytest.mark.asyncio
    async def test_failed_verify_emits_anomaly(self, open_client):
        reg = (await open_client.post("/agents/register", json={
            "name": "hooked", "sample_trajectory": CODING})).json()
        # verify with divergent behavior -> fail -> CAEP event
        await open_client.post("/verify", json={
            "agent_id": reg["agent_id"], "agent_key": reg["agent_key"], "trajectory": DEVOPS})
        assert ssf.queue_size() == 1
        claims = _decode_set(next(iter(ssf.poll().values())))
        assert ssf.BEHAVIORAL_ANOMALY in claims["events"]

    @pytest.mark.asyncio
    async def test_passing_verify_emits_nothing(self, open_client):
        reg = (await open_client.post("/agents/register", json={
            "name": "ok", "sample_trajectory": CODING})).json()
        await open_client.post("/verify", json={
            "agent_id": reg["agent_id"], "agent_key": reg["agent_key"], "trajectory": CODING})
        assert ssf.queue_size() == 0

    @pytest.mark.asyncio
    async def test_revoke_emits_session_revoked(self, open_client):
        reg = (await open_client.post("/agents/register", json={
            "name": "torevoke", "sample_trajectory": CODING})).json()
        await open_client.delete(f"/agents/{reg['agent_id']}")
        assert ssf.queue_size() == 1
        claims = _decode_set(next(iter(ssf.poll().values())))
        assert ssf.SESSION_REVOKED in claims["events"]
