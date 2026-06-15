"""RFC 0009 — token-exchange broker + provider registry.

Covers the provider registry (Clerk reuse + generic OIDC validation) and the
RFC 8693 /oauth/token flow with scope enforcement and the ownership/grant checks.
Clerk's own auth path is exercised unchanged by the existing suites.
"""
from __future__ import annotations

import uuid

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient

import app.auth.clerk as clerk_mod
from app.auth.clerk import get_current_human
from app.auth.jwt_issuer import get_jwt_issuer
from app.auth.providers import OIDCProvider, get_provider, reset_registry
from app.config import settings
from app.database import get_db
from app.main import app
from app.services.human_service import get_or_create_human

CODING = [
    {"type": "tool_call", "name": "search"},
    {"type": "tool_call", "name": "read_file"},
    {"type": "message", "name": "assistant", "content": "found it, fixing now"},
    {"type": "tool_call", "name": "edit_file"},
    {"type": "tool_call", "name": "run_tests"},
]


@pytest.fixture
async def ctx(db_session, monkeypatch):
    """Return (auth_client, open_client, clerk_id) sharing one db session.

    Run Clerk in dev-decode mode (no JWKS configured) so the broker's
    ClerkProvider accepts a stand-in subject token, mirroring a local dev setup.
    """
    monkeypatch.setattr(settings, "CLERK_JWKS_URL", "")
    monkeypatch.setattr(clerk_mod, "_jwk_client", None)
    clerk_id = f"clerk_{uuid.uuid4().hex[:12]}"

    async def override_get_current_human():
        return await get_or_create_human(db_session, clerk_id, "Owner", "o@example.com")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_current_human] = override_get_current_human
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    auth = AsyncClient(transport=transport, base_url="http://test")
    openc = AsyncClient(transport=transport, base_url="http://test")
    yield auth, openc, clerk_id
    await auth.aclose()
    await openc.aclose()
    app.dependency_overrides.clear()


def _subject_token(sub: str) -> str:
    # Clerk dev-mode decode does not verify the signature, so any signed JWT with
    # a sub works as a stand-in for a real Clerk session token in tests.
    return pyjwt.encode({"sub": sub, "name": "Owner"}, "test-secret-" + "0" * 32, algorithm="HS256")


async def _setup(auth, openc, clerk_id, scopes):
    reg = (await auth.post("/agents/register", json={"name": "broker-agent", "sample_trajectory": CODING})).json()
    agent_id, agent_key = reg["agent_id"], reg["agent_key"]
    await auth.post(f"/agents/{agent_id}/scopes", json={"scopes": scopes})
    verify = (await openc.post("/verify", json={
        "agent_id": agent_id, "agent_key": agent_key, "trajectory": CODING,
    })).json()
    assert verify["verified"] is True
    return agent_id, verify["token"]


async def _exchange(openc, subject_sub, actor_token, scope, audience="https://api.downstream"):
    return await openc.post("/oauth/token", data={
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": _subject_token(subject_sub),
        "subject_token_type": "urn:ietf:params:oauth:token-type:id_token",
        "subject_token_provider": "clerk",
        "actor_token": actor_token,
        "audience": audience,
        "scope": scope,
    })


# --- provider registry ------------------------------------------------------

class TestProviderRegistry:
    def test_clerk_always_registered(self):
        reset_registry()
        assert get_provider("clerk").id == "clerk"

    def test_unknown_provider_rejected(self):
        reset_registry()
        with pytest.raises(Exception) as ei:
            get_provider("nope")
        assert getattr(ei.value, "status_code", None) == 400

    def test_oidc_provider_validates_token(self, monkeypatch):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = pyjwt.encode(
            {"sub": "okta|123", "iss": "https://acme.okta.com", "aud": "woa", "email": "u@acme.com"},
            key, algorithm="RS256",
        )
        prov = OIDCProvider("okta", issuer="https://acme.okta.com", jwks_url="http://x", audience="woa")

        class _Key:
            def __init__(self, k):
                self.key = k

        monkeypatch.setattr(prov._jwk_client, "get_signing_key_from_jwt", lambda t: _Key(key.public_key()))
        ident = prov.verify(token)
        assert ident.subject == "okta|123"
        assert ident.provider == "okta"


# --- broker flow ------------------------------------------------------------

class TestTokenExchange:
    @pytest.mark.asyncio
    async def test_happy_path_mints_scoped_token(self, ctx):
        auth, openc, clerk_id = ctx
        agent_id, actor = await _setup(auth, openc, clerk_id, ["repo:read", "repo:write"])
        resp = await _exchange(openc, clerk_id, actor, "repo:read")
        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "Bearer"
        claims = get_jwt_issuer().verify_own_token(body["access_token"])
        assert claims["sub"] == clerk_id
        assert claims["act"]["sub"] == agent_id
        assert claims["aud"] == "https://api.downstream"
        assert claims["scope"] == "repo:read"

    @pytest.mark.asyncio
    async def test_scope_not_allowed_rejected(self, ctx):
        auth, openc, clerk_id = ctx
        _, actor = await _setup(auth, openc, clerk_id, ["repo:read"])
        resp = await _exchange(openc, clerk_id, actor, "repo:admin")
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "invalid_scope"

    @pytest.mark.asyncio
    async def test_unsupported_grant_type(self, ctx):
        auth, openc, clerk_id = ctx
        _, actor = await _setup(auth, openc, clerk_id, ["repo:read"])
        resp = await openc.post("/oauth/token", data={
            "grant_type": "authorization_code",
            "subject_token": _subject_token(clerk_id),
            "actor_token": actor,
            "audience": "x",
            "scope": "repo:read",
        })
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "unsupported_grant_type"

    @pytest.mark.asyncio
    async def test_subject_must_own_agent(self, ctx):
        auth, openc, clerk_id = ctx
        _, actor = await _setup(auth, openc, clerk_id, ["repo:read"])
        # a different human presents the agent's actor_token
        resp = await _exchange(openc, "clerk_someone_else", actor, "repo:read")
        assert resp.status_code == 403
        assert resp.json()["detail"]["error"] == "invalid_grant"

    @pytest.mark.asyncio
    async def test_invalid_actor_token(self, ctx):
        auth, openc, clerk_id = ctx
        await _setup(auth, openc, clerk_id, ["repo:read"])
        resp = await _exchange(openc, clerk_id, "not.a.jwt", "repo:read")
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "invalid_grant"
