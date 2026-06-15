"""RFC 0007 — hardening: JWT key handling, dev-auth gating, CORS, rate limiting."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app import ratelimit
from app.auth import clerk
from app.auth.clerk import _decode_clerk_token, _is_dev_mode
from app.auth.jwt_issuer import JWTIssuer
from app.config import settings
from app.database import get_db
from app.main import app


# --- F: JWT key fail-loud ----------------------------------------------------

class TestJWTKeyHandling:
    def test_no_keys_in_production_raises(self, monkeypatch):
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        with pytest.raises(RuntimeError, match="required in production"):
            JWTIssuer(private_key_pem=None, public_key_pem=None)

    def test_no_keys_in_development_generates(self, monkeypatch):
        monkeypatch.setattr(settings, "ENVIRONMENT", "development")
        issuer = JWTIssuer(private_key_pem=None, public_key_pem=None)
        assert issuer.kid  # ephemeral keypair created

    def test_invalid_keys_raise_not_regenerate(self, monkeypatch):
        monkeypatch.setattr(settings, "ENVIRONMENT", "development")
        with pytest.raises(RuntimeError, match="Failed to load"):
            JWTIssuer(private_key_pem="not-a-key", public_key_pem="also-not")


# --- G: dev-auth bypass gating ----------------------------------------------

class TestDevAuthGating:
    def test_dev_mode_off_in_production(self, monkeypatch):
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "CLERK_SECRET_KEY", "")
        assert _is_dev_mode() is False

    def test_dev_mode_on_in_development(self, monkeypatch):
        monkeypatch.setattr(settings, "ENVIRONMENT", "development")
        monkeypatch.setattr(settings, "CLERK_SECRET_KEY", "sk_test_xxx")
        assert _is_dev_mode() is True

    def test_unsigned_decode_blocked_in_production(self, monkeypatch):
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "CLERK_JWKS_URL", "")
        monkeypatch.setattr(clerk, "_jwk_client", None)
        with pytest.raises(Exception) as ei:
            _decode_clerk_token("any.token.here")
        assert getattr(ei.value, "status_code", None) == 401

    @pytest.mark.asyncio
    async def test_no_demo_user_in_production(self, monkeypatch, db_session):
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "CLERK_SECRET_KEY", "")

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        try:
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                # no Authorization header -> must be rejected, not given a demo user
                resp = await c.get("/agents")
            assert resp.status_code == 401
        finally:
            app.dependency_overrides.clear()


# --- I: CORS ----------------------------------------------------------------

class TestCORS:
    def test_wildcard_disables_credentials(self, monkeypatch):
        monkeypatch.setattr(settings, "ALLOWED_ORIGINS", "*")
        assert settings.allowed_origins_list == ["*"]

    def test_explicit_origins_parsed(self, monkeypatch):
        monkeypatch.setattr(settings, "ALLOWED_ORIGINS", "https://a.com, https://b.com")
        assert settings.allowed_origins_list == ["https://a.com", "https://b.com"]


# --- H: rate limiting -------------------------------------------------------

class TestRateLimiting:
    @pytest.fixture
    def limited(self, monkeypatch):
        ratelimit.reset()
        monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
        monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 3)
        yield
        ratelimit.reset()

    @pytest.mark.asyncio
    async def test_compare_rate_limited(self, limited, db_session):
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        payload = {
            "trajectory_a": [{"type": "tool_call", "name": "x"}],
            "trajectory_b": [{"type": "tool_call", "name": "y"}],
        }
        transport = ASGITransport(app=app)
        try:
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                codes = [(await c.post("/compare", json=payload)).status_code for _ in range(5)]
            assert codes[:3] == [200, 200, 200]
            assert 429 in codes[3:]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_disabled_allows_unlimited(self, monkeypatch, db_session):
        ratelimit.reset()
        monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        payload = {
            "trajectory_a": [{"type": "tool_call", "name": "x"}],
            "trajectory_b": [{"type": "tool_call", "name": "y"}],
        }
        transport = ASGITransport(app=app)
        try:
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                codes = [(await c.post("/compare", json=payload)).status_code for _ in range(6)]
            assert all(code == 200 for code in codes)
        finally:
            app.dependency_overrides.clear()
