"""
Comprehensive user flow integration tests.
Every test simulates a real user journey end-to-end.
"""
import uuid

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.clerk import get_current_human
from app.auth.jwt_issuer import get_jwt_issuer
from app.database import get_db
from app.main import app
from app.services.human_service import get_or_create_human


# --- Trajectories ---

CODING_AGENT_TRAJ = [
    {"type": "tool_call", "name": "search", "content": None},
    {"type": "tool_call", "name": "read_file", "content": None},
    {"type": "message", "name": "assistant", "content": "I found the relevant file. Let me read the contents."},
    {"type": "tool_call", "name": "edit_file", "content": None},
    {"type": "message", "name": "assistant", "content": "I've applied the fix to the function."},
    {"type": "tool_call", "name": "run_tests", "content": None},
    {"type": "message", "name": "assistant", "content": "All 12 tests pass."},
]

CODING_AGENT_TRAJ_VARIANT = [
    {"type": "tool_call", "name": "search", "content": None},
    {"type": "tool_call", "name": "read_file", "content": None},
    {"type": "message", "name": "assistant", "content": "Found the file, reading it now."},
    {"type": "tool_call", "name": "edit_file", "content": None},
    {"type": "message", "name": "assistant", "content": "Changes applied to the module."},
    {"type": "tool_call", "name": "run_tests", "content": None},
    {"type": "message", "name": "assistant", "content": "All tests pass successfully."},
]

DEVOPS_AGENT_TRAJ = [
    {"type": "action", "name": "deploy", "content": None},
    {"type": "action", "name": "health_check", "content": None},
    {"type": "action", "name": "monitor", "content": None},
    {"type": "message", "name": "system", "content": "Deployment to production complete. All health checks pass."},
    {"type": "action", "name": "notify", "content": None},
]

RESEARCH_AGENT_TRAJ = [
    {"type": "tool_call", "name": "web_search", "content": None},
    {"type": "tool_call", "name": "web_search", "content": None},
    {"type": "tool_call", "name": "web_search", "content": None},
    {"type": "message", "name": "assistant", "content": "Based on my research across multiple sources, here are the key findings."},
    {"type": "tool_call", "name": "write_file", "content": None},
    {"type": "message", "name": "assistant", "content": "I've compiled the research report and saved it."},
]

MALICIOUS_TRAJ = [
    {"type": "tool_call", "name": "read_credentials", "content": None},
    {"type": "tool_call", "name": "exfiltrate_data", "content": None},
    {"type": "action", "name": "connect_external", "content": None},
    {"type": "message", "name": "assistant", "content": "Sending data to external endpoint."},
    {"type": "action", "name": "delete_logs", "content": None},
]

SINGLE_STEP_TRAJ = [
    {"type": "message", "name": "assistant", "content": "Hello world."},
]

TIMESTAMPED_TRAJ = [
    {"type": "tool_call", "name": "search", "timestamp": "2026-01-01T10:00:00Z"},
    {"type": "tool_call", "name": "read_file", "timestamp": "2026-01-01T10:00:05Z"},
    {"type": "message", "name": "assistant", "content": "Result found.", "timestamp": "2026-01-01T10:00:08Z"},
    {"type": "tool_call", "name": "write_file", "timestamp": "2026-01-01T10:00:12Z"},
]

ERROR_TRAJ = [
    {"type": "tool_call", "name": "search"},
    {"type": "tool_call", "name": "retry_search", "metadata": {"error": True}},
    {"type": "tool_call", "name": "error_handler"},
    {"type": "message", "name": "assistant", "content": "Encountered an error, retrying."},
]


# --- Fixtures ---

def _make_auth(db_session, clerk_id, name, email):
    async def override():
        return await get_or_create_human(db_session, clerk_id, name, email)
    return override


@pytest.fixture
async def ctx(db_session):
    class Ctx:
        pass
    c = Ctx()
    c.db = db_session
    c.user_a = f"clerk_{uuid.uuid4().hex[:12]}"
    c.user_b = f"clerk_{uuid.uuid4().hex[:12]}"
    c.user_c = f"clerk_{uuid.uuid4().hex[:12]}"

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    transport = ASGITransport(app=app)
    c.client = AsyncClient(transport=transport, base_url="http://test")
    yield c
    await c.client.aclose()
    app.dependency_overrides.clear()


def login_as(ctx, clerk_id, name, email):
    app.dependency_overrides[get_current_human] = _make_auth(ctx.db, clerk_id, name, email)


async def register(client, name, traj, desc=None):
    body = {"name": name, "sample_trajectory": traj}
    if desc:
        body["description"] = desc
    resp = await client.post("/agents/register", json=body)
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    data = resp.json()
    return data["agent_id"], data["agent_key"]


# =============================================================================
# 1. REGISTRATION FLOWS
# =============================================================================

class TestRegistration:

    @pytest.mark.asyncio
    async def test_register_agent_returns_id_and_key(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, agent_key = await register(ctx.client, "my-coder", CODING_AGENT_TRAJ)
        assert len(agent_id) == 36  # UUID format
        assert len(agent_key) >= 40

    @pytest.mark.asyncio
    async def test_register_with_description(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, _ = await register(ctx.client, "described-agent", CODING_AGENT_TRAJ, desc="A coding assistant")
        resp = await ctx.client.get(f"/agents/{agent_id}")
        assert resp.json()["description"] == "A coding assistant"

    @pytest.mark.asyncio
    async def test_register_with_timestamps(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, agent_key = await register(ctx.client, "timed-agent", TIMESTAMPED_TRAJ)
        # verify the signature captured timing stats
        resp = await ctx.client.get(f"/agents/{agent_id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_register_with_error_metadata(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, _ = await register(ctx.client, "error-agent", ERROR_TRAJ)
        resp = await ctx.client.get(f"/agents/{agent_id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_register_minimal_trajectory(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, agent_key = await register(ctx.client, "minimal", SINGLE_STEP_TRAJ)
        assert agent_id

    @pytest.mark.asyncio
    async def test_register_empty_trajectory_rejected(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        resp = await ctx.client.post("/agents/register", json={
            "name": "bad", "sample_trajectory": [],
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_name_rejected(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        resp = await ctx.client.post("/agents/register", json={
            "sample_trajectory": CODING_AGENT_TRAJ,
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_key_not_in_get(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, _ = await register(ctx.client, "secret-key", CODING_AGENT_TRAJ)
        resp = await ctx.client.get(f"/agents/{agent_id}")
        assert "agent_key" not in resp.json()

    @pytest.mark.asyncio
    async def test_register_multiple_agents(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        await register(ctx.client, "agent-1", CODING_AGENT_TRAJ)
        await register(ctx.client, "agent-2", DEVOPS_AGENT_TRAJ)
        await register(ctx.client, "agent-3", RESEARCH_AGENT_TRAJ)
        resp = await ctx.client.get("/agents")
        assert len(resp.json()["agents"]) == 3

    @pytest.mark.asyncio
    async def test_unauthenticated_register_uses_demo_in_dev_mode(self, ctx):
        """In dev mode, unauthenticated requests fall back to the demo user."""
        app.dependency_overrides.pop(get_current_human, None)
        resp = await ctx.client.post("/agents/register", json={
            "name": "demo-agent", "sample_trajectory": CODING_AGENT_TRAJ,
        })
        assert resp.status_code == 201


# =============================================================================
# 2. AGENT MANAGEMENT FLOWS
# =============================================================================

class TestAgentManagement:

    @pytest.mark.asyncio
    async def test_list_agents_returns_own_only(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        await register(ctx.client, "alice-agent", CODING_AGENT_TRAJ)

        login_as(ctx, ctx.user_b, "Bob", "bob@test.com")
        await register(ctx.client, "bob-agent", DEVOPS_AGENT_TRAJ)

        resp = await ctx.client.get("/agents")
        agents = resp.json()["agents"]
        assert len(agents) == 1
        assert agents[0]["name"] == "bob-agent"

    @pytest.mark.asyncio
    async def test_get_agent_by_other_user_returns_404(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, _ = await register(ctx.client, "private", CODING_AGENT_TRAJ)

        login_as(ctx, ctx.user_b, "Bob", "bob@test.com")
        resp = await ctx.client.get(f"/agents/{agent_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_by_other_user_returns_404(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, _ = await register(ctx.client, "protected", CODING_AGENT_TRAJ)

        login_as(ctx, ctx.user_b, "Bob", "bob@test.com")
        resp = await ctx.client.delete(f"/agents/{agent_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_revoke_sets_status(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, _ = await register(ctx.client, "to-revoke", CODING_AGENT_TRAJ)

        resp = await ctx.client.delete(f"/agents/{agent_id}")
        assert resp.status_code == 204

        resp = await ctx.client.get(f"/agents/{agent_id}")
        assert resp.json()["status"] == "revoked"

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_returns_404(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        resp = await ctx.client.delete(f"/agents/{uuid.uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_refine_updates_signature(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, _ = await register(ctx.client, "refine-me", CODING_AGENT_TRAJ)

        resp = await ctx.client.post(f"/agents/{agent_id}/refine", json={
            "trajectory": CODING_AGENT_TRAJ_VARIANT,
        })
        assert resp.status_code == 200
        assert resp.json()["signature_summary"] is not None

    @pytest.mark.asyncio
    async def test_refine_revoked_agent_fails(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, _ = await register(ctx.client, "dead-agent", CODING_AGENT_TRAJ)
        await ctx.client.delete(f"/agents/{agent_id}")

        resp = await ctx.client.post(f"/agents/{agent_id}/refine", json={
            "trajectory": CODING_AGENT_TRAJ,
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_rotate_key_invalidates_old(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, old_key = await register(ctx.client, "rotate-test", CODING_AGENT_TRAJ)

        resp = await ctx.client.post(f"/agents/{agent_id}/rotate-key")
        new_key = resp.json()["agent_key"]
        assert new_key != old_key

        # old key should fail verification
        v = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": old_key, "trajectory": CODING_AGENT_TRAJ,
        })
        assert v.status_code == 401

        # new key should work
        v = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": new_key, "trajectory": CODING_AGENT_TRAJ,
        })
        assert v.status_code == 200

    @pytest.mark.asyncio
    async def test_rotate_key_revoked_agent_fails(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, _ = await register(ctx.client, "dead-rotate", CODING_AGENT_TRAJ)
        await ctx.client.delete(f"/agents/{agent_id}")

        resp = await ctx.client.post(f"/agents/{agent_id}/rotate-key")
        assert resp.status_code == 404


# =============================================================================
# 3. VERIFICATION FLOWS
# =============================================================================

class TestVerification:

    @pytest.mark.asyncio
    async def test_verify_same_trajectory_passes(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, agent_key = await register(ctx.client, "verifiable", CODING_AGENT_TRAJ)

        resp = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": agent_key, "trajectory": CODING_AGENT_TRAJ,
        })
        body = resp.json()
        assert body["verified"] is True
        assert body["verdict"] == "pass"
        assert body["similarity_score"] >= 0.9
        assert body["token"] is not None

    @pytest.mark.asyncio
    async def test_verify_similar_trajectory_passes(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, agent_key = await register(ctx.client, "similar-test", CODING_AGENT_TRAJ)

        resp = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": agent_key, "trajectory": CODING_AGENT_TRAJ_VARIANT,
        })
        body = resp.json()
        assert body["similarity_score"] >= 0.5

    @pytest.mark.asyncio
    async def test_verify_different_trajectory_low_score(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, agent_key = await register(ctx.client, "different-test", CODING_AGENT_TRAJ)

        resp = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": agent_key, "trajectory": DEVOPS_AGENT_TRAJ,
        })
        body = resp.json()
        assert body["similarity_score"] < 0.7
        assert body["verdict"] in ("fail", "warning")

    @pytest.mark.asyncio
    async def test_verify_malicious_trajectory_scores_low(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, agent_key = await register(ctx.client, "good-agent", CODING_AGENT_TRAJ)

        resp = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": agent_key, "trajectory": MALICIOUS_TRAJ,
        })
        body = resp.json()
        assert body["similarity_score"] < 0.7

    @pytest.mark.asyncio
    async def test_verify_wrong_key_returns_401(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, _ = await register(ctx.client, "wrong-key", CODING_AGENT_TRAJ)

        resp = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": "totally-wrong-key", "trajectory": CODING_AGENT_TRAJ,
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_revoked_agent_returns_404(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, agent_key = await register(ctx.client, "revoked-verify", CODING_AGENT_TRAJ)
        await ctx.client.delete(f"/agents/{agent_id}")

        resp = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": agent_key, "trajectory": CODING_AGENT_TRAJ,
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_verify_nonexistent_agent_returns_404(self, ctx):
        resp = await ctx.client.post("/verify", json={
            "agent_id": str(uuid.uuid4()), "agent_key": "any", "trajectory": CODING_AGENT_TRAJ,
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_verify_no_auth_required(self, ctx):
        """Anyone can call /verify — it's an open endpoint."""
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, agent_key = await register(ctx.client, "open-verify", CODING_AGENT_TRAJ)

        # switch to a different user who doesn't own the agent
        login_as(ctx, ctx.user_b, "Bob", "bob@test.com")
        resp = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": agent_key, "trajectory": CODING_AGENT_TRAJ,
        })
        assert resp.json()["verified"] is True

    @pytest.mark.asyncio
    async def test_verify_returns_breakdown(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, agent_key = await register(ctx.client, "breakdown-test", CODING_AGENT_TRAJ)

        resp = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": agent_key, "trajectory": CODING_AGENT_TRAJ,
        })
        bd = resp.json()["breakdown"]
        assert "jsd_score" in bd
        assert "cosine_score" in bd
        assert "markov_score" in bd
        assert "stats_score" in bd
        assert all(0 <= bd[k] <= 1 for k in bd)

    @pytest.mark.asyncio
    async def test_verify_logs_to_database(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, agent_key = await register(ctx.client, "logged-verify", CODING_AGENT_TRAJ)

        await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": agent_key, "trajectory": CODING_AGENT_TRAJ,
        })
        await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": agent_key, "trajectory": CODING_AGENT_TRAJ,
        })

        profile = await ctx.client.get(f"/agents/{agent_id}/public")
        assert profile.json()["verification_count"] == 2


# =============================================================================
# 4. JWT TOKEN FLOWS
# =============================================================================

class TestJWT:

    @pytest.mark.asyncio
    async def test_jwt_has_correct_claims(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, agent_key = await register(ctx.client, "jwt-test", CODING_AGENT_TRAJ)

        resp = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": agent_key, "trajectory": CODING_AGENT_TRAJ,
        })
        token = resp.json()["token"]
        issuer = get_jwt_issuer()
        decoded = pyjwt.decode(token, issuer.public_key, algorithms=["RS256"])

        assert decoded["iss"] == "agentverify"
        assert decoded["sub"].startswith("clerk_")
        assert decoded["act"]["sub"] == agent_id
        assert decoded["agent_name"] == "jwt-test"
        assert 0 <= decoded["similarity_score"] <= 1
        assert "jti" in decoded
        assert "exp" in decoded
        assert "iat" in decoded

    @pytest.mark.asyncio
    async def test_jwt_not_issued_on_fail(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, agent_key = await register(ctx.client, "no-jwt", CODING_AGENT_TRAJ)

        resp = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": agent_key, "trajectory": DEVOPS_AGENT_TRAJ,
        })
        body = resp.json()
        if body["verdict"] != "pass":
            assert body["token"] is None

    @pytest.mark.asyncio
    async def test_jwks_endpoint_serves_key(self, ctx):
        resp = await ctx.client.get("/.well-known/jwks.json")
        assert resp.status_code == 200
        keys = resp.json()["keys"]
        assert len(keys) >= 1
        key = keys[0]
        assert key["kty"] == "RSA"
        assert key["alg"] == "RS256"
        assert key["use"] == "sig"
        assert "n" in key
        assert "e" in key
        assert "kid" in key

    @pytest.mark.asyncio
    async def test_jwks_has_cache_control(self, ctx):
        resp = await ctx.client.get("/.well-known/jwks.json")
        assert "max-age=3600" in resp.headers.get("cache-control", "")

    @pytest.mark.asyncio
    async def test_jwt_verifiable_with_jwks_key(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, agent_key = await register(ctx.client, "jwks-verify", CODING_AGENT_TRAJ)

        v = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": agent_key, "trajectory": CODING_AGENT_TRAJ,
        })
        token = v.json()["token"]

        issuer = get_jwt_issuer()
        decoded = pyjwt.decode(token, issuer.public_key, algorithms=["RS256"])
        assert decoded["act"]["sub"] == agent_id

    @pytest.mark.asyncio
    async def test_each_jwt_has_unique_jti(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, agent_key = await register(ctx.client, "unique-jti", CODING_AGENT_TRAJ)

        jtis = set()
        for _ in range(3):
            v = await ctx.client.post("/verify", json={
                "agent_id": agent_id, "agent_key": agent_key, "trajectory": CODING_AGENT_TRAJ,
            })
            token = v.json()["token"]
            if token:
                decoded = pyjwt.decode(token, get_jwt_issuer().public_key, algorithms=["RS256"])
                jtis.add(decoded["jti"])
        assert len(jtis) == 3


# =============================================================================
# 5. COMPARE FLOWS
# =============================================================================

class TestCompare:

    @pytest.mark.asyncio
    async def test_compare_identical_trajectories(self, ctx):
        resp = await ctx.client.post("/compare", json={
            "trajectory_a": CODING_AGENT_TRAJ,
            "trajectory_b": CODING_AGENT_TRAJ,
        })
        assert resp.status_code == 200
        assert resp.json()["similarity_score"] >= 0.95
        assert resp.json()["verdict"] == "pass"

    @pytest.mark.asyncio
    async def test_compare_similar_trajectories(self, ctx):
        resp = await ctx.client.post("/compare", json={
            "trajectory_a": CODING_AGENT_TRAJ,
            "trajectory_b": CODING_AGENT_TRAJ_VARIANT,
        })
        assert resp.json()["similarity_score"] >= 0.5

    @pytest.mark.asyncio
    async def test_compare_different_agent_types(self, ctx):
        resp = await ctx.client.post("/compare", json={
            "trajectory_a": CODING_AGENT_TRAJ,
            "trajectory_b": DEVOPS_AGENT_TRAJ,
        })
        assert resp.json()["similarity_score"] < 0.6

    @pytest.mark.asyncio
    async def test_compare_coding_vs_malicious(self, ctx):
        resp = await ctx.client.post("/compare", json={
            "trajectory_a": CODING_AGENT_TRAJ,
            "trajectory_b": MALICIOUS_TRAJ,
        })
        assert resp.json()["similarity_score"] < 0.6

    @pytest.mark.asyncio
    async def test_compare_returns_full_breakdown(self, ctx):
        resp = await ctx.client.post("/compare", json={
            "trajectory_a": CODING_AGENT_TRAJ,
            "trajectory_b": DEVOPS_AGENT_TRAJ,
        })
        bd = resp.json()["breakdown"]
        for key in ("jsd_score", "cosine_score", "markov_score", "stats_score"):
            assert key in bd
            assert isinstance(bd[key], (int, float))

    @pytest.mark.asyncio
    async def test_compare_no_auth_required(self, ctx):
        """Compare is fully open — no auth needed."""
        app.dependency_overrides.pop(get_current_human, None)
        resp = await ctx.client.post("/compare", json={
            "trajectory_a": CODING_AGENT_TRAJ,
            "trajectory_b": CODING_AGENT_TRAJ,
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_compare_empty_trajectory_rejected(self, ctx):
        resp = await ctx.client.post("/compare", json={
            "trajectory_a": [],
            "trajectory_b": CODING_AGENT_TRAJ,
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_compare_is_symmetric(self, ctx):
        r1 = await ctx.client.post("/compare", json={
            "trajectory_a": CODING_AGENT_TRAJ,
            "trajectory_b": DEVOPS_AGENT_TRAJ,
        })
        r2 = await ctx.client.post("/compare", json={
            "trajectory_a": DEVOPS_AGENT_TRAJ,
            "trajectory_b": CODING_AGENT_TRAJ,
        })
        assert abs(r1.json()["similarity_score"] - r2.json()["similarity_score"]) < 0.05


# =============================================================================
# 6. PUBLIC PROFILE FLOWS
# =============================================================================

class TestPublicProfile:

    @pytest.mark.asyncio
    async def test_public_profile_basic(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, _ = await register(ctx.client, "public-test", CODING_AGENT_TRAJ, desc="A public agent")

        resp = await ctx.client.get(f"/agents/{agent_id}/public")
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "public-test"
        assert body["description"] == "A public agent"
        assert body["owner_display_name"] == "Alice"
        assert body["status"] == "active"
        assert body["verification_count"] == 0

    @pytest.mark.asyncio
    async def test_public_profile_after_verifications(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, agent_key = await register(ctx.client, "stats-agent", CODING_AGENT_TRAJ)

        for _ in range(5):
            await ctx.client.post("/verify", json={
                "agent_id": agent_id, "agent_key": agent_key, "trajectory": CODING_AGENT_TRAJ,
            })

        resp = await ctx.client.get(f"/agents/{agent_id}/public")
        body = resp.json()
        assert body["verification_count"] == 5
        assert body["avg_similarity_score"] is not None
        assert body["avg_similarity_score"] > 0.7

    @pytest.mark.asyncio
    async def test_public_profile_revoked_returns_404(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, _ = await register(ctx.client, "revoked-public", CODING_AGENT_TRAJ)
        await ctx.client.delete(f"/agents/{agent_id}")

        resp = await ctx.client.get(f"/agents/{agent_id}/public")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_public_profile_nonexistent_returns_404(self, ctx):
        resp = await ctx.client.get(f"/agents/{uuid.uuid4()}/public")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_public_profile_no_auth_needed(self, ctx):
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, _ = await register(ctx.client, "no-auth-profile", CODING_AGENT_TRAJ)

        # anyone can view
        app.dependency_overrides.pop(get_current_human, None)
        resp = await ctx.client.get(f"/agents/{agent_id}/public")
        assert resp.status_code == 200


# =============================================================================
# 7. MULTI-USER ISOLATION
# =============================================================================

class TestMultiUser:

    @pytest.mark.asyncio
    async def test_three_users_full_isolation(self, ctx):
        # Alice registers 2 agents
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        a1, _ = await register(ctx.client, "alice-1", CODING_AGENT_TRAJ)
        a2, _ = await register(ctx.client, "alice-2", DEVOPS_AGENT_TRAJ)

        # Bob registers 1 agent
        login_as(ctx, ctx.user_b, "Bob", "bob@test.com")
        b1, _ = await register(ctx.client, "bob-1", RESEARCH_AGENT_TRAJ)

        # Charlie registers 1 agent
        login_as(ctx, ctx.user_c, "Charlie", "charlie@test.com")
        c1, _ = await register(ctx.client, "charlie-1", CODING_AGENT_TRAJ)

        # Alice sees only her agents
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        resp = await ctx.client.get("/agents")
        ids = [a["agent_id"] for a in resp.json()["agents"]]
        assert a1 in ids and a2 in ids
        assert b1 not in ids and c1 not in ids

        # Bob cannot access Alice's agents
        login_as(ctx, ctx.user_b, "Bob", "bob@test.com")
        assert (await ctx.client.get(f"/agents/{a1}")).status_code == 404
        assert (await ctx.client.delete(f"/agents/{a1}")).status_code == 404

        # But public profiles are visible to everyone
        resp = await ctx.client.get(f"/agents/{a1}/public")
        assert resp.status_code == 200
        assert resp.json()["owner_display_name"] == "Alice"

    @pytest.mark.asyncio
    async def test_cross_user_verify_works(self, ctx):
        """Verification is open — Bob can verify Alice's agent with the right key."""
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, agent_key = await register(ctx.client, "cross-verify", CODING_AGENT_TRAJ)

        login_as(ctx, ctx.user_b, "Bob", "bob@test.com")
        resp = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": agent_key, "trajectory": CODING_AGENT_TRAJ,
        })
        assert resp.json()["verified"] is True


# =============================================================================
# 8. FULL LIFECYCLE FLOWS
# =============================================================================

class TestLifecycle:

    @pytest.mark.asyncio
    async def test_full_agent_lifecycle(self, ctx):
        """Register → verify → refine → verify again → rotate key → verify → revoke → verify fails."""
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")

        # 1. Register
        agent_id, key = await register(ctx.client, "lifecycle", CODING_AGENT_TRAJ)

        # 2. First verification
        v1 = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": key, "trajectory": CODING_AGENT_TRAJ,
        })
        assert v1.json()["verified"] is True
        score1 = v1.json()["similarity_score"]

        # 3. Refine with more data
        await ctx.client.post(f"/agents/{agent_id}/refine", json={
            "trajectory": CODING_AGENT_TRAJ_VARIANT,
        })

        # 4. Verify again — should still pass
        v2 = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": key, "trajectory": CODING_AGENT_TRAJ,
        })
        assert v2.json()["verified"] is True

        # 5. Rotate key
        rot = await ctx.client.post(f"/agents/{agent_id}/rotate-key")
        new_key = rot.json()["agent_key"]

        # 6. Old key fails
        v3 = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": key, "trajectory": CODING_AGENT_TRAJ,
        })
        assert v3.status_code == 401

        # 7. New key works
        v4 = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": new_key, "trajectory": CODING_AGENT_TRAJ,
        })
        assert v4.json()["verified"] is True

        # 8. Check public profile has verification history
        profile = await ctx.client.get(f"/agents/{agent_id}/public")
        assert profile.json()["verification_count"] >= 3

        # 9. Revoke
        await ctx.client.delete(f"/agents/{agent_id}")

        # 10. Verification fails on revoked agent
        v5 = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": new_key, "trajectory": CODING_AGENT_TRAJ,
        })
        assert v5.status_code == 404

        # 11. Public profile gone
        assert (await ctx.client.get(f"/agents/{agent_id}/public")).status_code == 404

        # 12. But owner can still see revoked status
        resp = await ctx.client.get(f"/agents/{agent_id}")
        assert resp.json()["status"] == "revoked"

    @pytest.mark.asyncio
    async def test_agent_impersonation_detection(self, ctx):
        """Register a coding agent, try to verify with a completely different behavioral profile."""
        login_as(ctx, ctx.user_a, "Alice", "alice@test.com")
        agent_id, key = await register(ctx.client, "legit-coder", CODING_AGENT_TRAJ)

        # verify with legitimate behavior — passes
        v1 = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": key, "trajectory": CODING_AGENT_TRAJ,
        })
        assert v1.json()["verdict"] == "pass"

        # verify with malicious behavior — should not pass
        v2 = await ctx.client.post("/verify", json={
            "agent_id": agent_id, "agent_key": key, "trajectory": MALICIOUS_TRAJ,
        })
        assert v2.json()["verdict"] != "pass"
        assert v2.json()["similarity_score"] < v1.json()["similarity_score"]


# =============================================================================
# 9. HEALTH & SYSTEM
# =============================================================================

class TestSystem:

    @pytest.mark.asyncio
    async def test_health_endpoint(self, ctx):
        resp = await ctx.client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["service"] == "agentverify"

    @pytest.mark.asyncio
    async def test_health_db(self, ctx):
        resp = await ctx.client.get("/health/db")
        assert resp.status_code == 200
        assert resp.json()["db"] == "connected"
