"""RFC 0012 — MCP/A2A reference authorization server."""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.jwt_issuer import get_jwt_issuer
from app.database import get_db
from app.main import app

CODING = [
    {"type": "tool_call", "name": "search"},
    {"type": "tool_call", "name": "read_file"},
    {"type": "message", "name": "assistant", "content": "fixing now"},
    {"type": "tool_call", "name": "edit_file"},
]


@pytest.fixture
async def open_client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _setup(open_client, tools):
    """Register an agent (dev demo user), allowlist tools, return (id, attestation token)."""
    reg = (await open_client.post("/agents/register", json={
        "name": "mcp-agent", "sample_trajectory": CODING})).json()
    aid, akey = reg["agent_id"], reg["agent_key"]
    await open_client.post(f"/agents/{aid}/tools", json={"tools": tools})
    token = (await open_client.post("/verify", json={
        "agent_id": aid, "agent_key": akey, "trajectory": CODING})).json()["token"]
    assert token
    return aid, token


async def _call(open_client, token, tool, args=None):
    return await open_client.post("/mcp/call", json={"tool": tool, "arguments": args or {}},
                                  headers={"Authorization": f"Bearer {token}"})


class TestToolCatalog:
    @pytest.mark.asyncio
    async def test_lists_tools(self, open_client):
        resp = await open_client.get("/mcp/tools")
        assert resp.status_code == 200
        names = {t["name"] for t in resp.json()["tools"]}
        assert {"search", "edit_file", "deploy"} <= names


class TestAuthorization:
    @pytest.mark.asyncio
    async def test_allowed_tool_executes(self, open_client):
        aid, token = await _setup(open_client, ["search", "edit_file"])
        resp = await _call(open_client, token, "edit_file", {"path": "x.py"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "executed"
        assert body["agent_id"] == aid
        assert body["result"]["echo"] == {"path": "x.py"}

    @pytest.mark.asyncio
    async def test_tool_not_in_allowlist_forbidden(self, open_client):
        _, token = await _setup(open_client, ["search"])
        resp = await _call(open_client, token, "deploy")
        assert resp.status_code == 403
        assert "tool_not_authorized" in resp.json()["detail"]["error"]

    @pytest.mark.asyncio
    async def test_unknown_tool_404(self, open_client):
        _, token = await _setup(open_client, ["search"])
        resp = await _call(open_client, token, "rm_rf")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_missing_token_401(self, open_client):
        await _setup(open_client, ["search"])
        resp = await open_client.post("/mcp/call", json={"tool": "search", "arguments": {}})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_401(self, open_client):
        await _setup(open_client, ["search"])
        resp = await _call(open_client, "not.a.jwt", "search")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_revoked_agent_forbidden(self, open_client):
        aid, token = await _setup(open_client, ["search"])
        await open_client.delete(f"/agents/{aid}")  # revoke
        resp = await _call(open_client, token, "search")
        assert resp.status_code == 403
        assert resp.json()["detail"]["error"] == "agent_revoked"

    @pytest.mark.asyncio
    async def test_foreign_token_for_unknown_agent_forbidden(self, open_client):
        # a well-signed token whose agent does not exist
        token = get_jwt_issuer().issue_token(
            human_clerk_id="demo_user_001", agent_id=str(uuid.uuid4()),
            agent_name="ghost", similarity_score=0.99)
        resp = await _call(open_client, token, "search")
        assert resp.status_code == 403
