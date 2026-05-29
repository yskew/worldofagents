import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.jwt_issuer import get_jwt_issuer
from app.main import app


@pytest.fixture
async def open_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_jwks_returns_valid_format(open_client):
    resp = await open_client.get("/.well-known/jwks.json")
    assert resp.status_code == 200
    body = resp.json()
    assert "keys" in body
    assert len(body["keys"]) >= 1


@pytest.mark.asyncio
async def test_jwks_key_has_required_fields(open_client):
    resp = await open_client.get("/.well-known/jwks.json")
    key = resp.json()["keys"][0]
    assert key["kty"] == "RSA"
    assert key["use"] == "sig"
    assert key["alg"] == "RS256"
    assert "kid" in key
    assert "n" in key
    assert "e" in key


@pytest.mark.asyncio
async def test_jwks_key_can_verify_issued_jwt(open_client):
    issuer = get_jwt_issuer()
    token = issuer.issue_token(
        human_clerk_id="test_clerk",
        agent_id="test_agent",
        agent_name="test",
        similarity_score=0.95,
    )
    decoded = pyjwt.decode(token, issuer.public_key, algorithms=["RS256"])
    assert decoded["sub"] == "test_clerk"
    assert decoded["act"]["sub"] == "test_agent"


@pytest.mark.asyncio
async def test_jwks_cache_control(open_client):
    resp = await open_client.get("/.well-known/jwks.json")
    assert "max-age=3600" in resp.headers.get("cache-control", "")
