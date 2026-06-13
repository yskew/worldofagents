"""RFC 0010 — telemetry ingestion (mappers + endpoint)."""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app
from app.services import telemetry

# --- format fixtures --------------------------------------------------------

OTEL = [
    {"name": "chat gpt", "attributes": {"gen_ai.operation.name": "chat", "gen_ai.completion": "hello there"},
     "startTimeUnixNano": 1_000_000_000_000, "status": {"code": "OK"}},
    {"name": "execute_tool search", "attributes": {"gen_ai.tool.name": "search"},
     "startTimeUnixNano": 2_000_000_000_000, "status": {"code": "OK"}},
    {"name": "execute_tool read_file", "attributes": {"gen_ai.tool.name": "read_file"},
     "startTimeUnixNano": 3_000_000_000_000, "status": {"code": "ERROR"}},
]

LANGFUSE = [
    {"type": "GENERATION", "name": "llm", "startTime": "2026-01-01T00:00:01Z", "output": "done"},
    {"type": "SPAN", "name": "search", "startTime": "2026-01-01T00:00:02Z", "level": "DEFAULT"},
    {"type": "SPAN", "name": "deploy", "startTime": "2026-01-01T00:00:03Z", "level": "ERROR"},
]

BRAINTRUST = [
    {"span_attributes": {"type": "llm", "name": "gen"}, "output": "ok", "metrics": {"start": 1.0}},
    {"span_attributes": {"type": "tool", "name": "query_db"}, "metrics": {"start": 2.0}},
    {"span_attributes": {"type": "function", "name": "transform"}, "metrics": {"start": 3.0}, "error": "boom"},
]


class TestMappers:
    def test_otel_maps_tools_messages_errors(self):
        steps = telemetry.map_otel(OTEL)
        assert [s.type for s in steps] == ["message", "tool_call", "tool_call"]
        assert steps[1].name == "search"
        assert steps[2].metadata == {"error": True}
        assert steps[0].timestamp is not None  # timing preserved

    def test_langfuse_maps(self):
        steps = telemetry.map_langfuse(LANGFUSE)
        assert steps[0].type == "message"
        assert steps[1].type == "tool_call" and steps[1].name == "search"
        assert steps[2].metadata == {"error": True}

    def test_braintrust_maps(self):
        steps = telemetry.map_braintrust(BRAINTRUST)
        assert steps[0].type == "message"
        assert steps[1].name == "query_db"
        assert steps[2].metadata == {"error": True}

    def test_summary_reports_patterns(self):
        steps = telemetry.map_otel(OTEL)
        summary = telemetry.summarize(steps)
        assert summary["sequence_length"] == 3
        assert summary["error_rate"] > 0  # one ERROR span
        assert "search" in summary["tool_histogram"]
        assert summary["mean_interval_s"] is not None  # timing computed

    def test_unknown_source_raises(self):
        with pytest.raises(ValueError):
            telemetry.map_spans("nope", [{}])


# --- endpoint ---------------------------------------------------------------

@pytest.fixture
async def open_client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _register(open_client):
    # dev-mode demo user owns the agent (no auth header needed)
    reg = await open_client.post("/agents/register", json={
        "name": "telemetry-agent",
        "sample_trajectory": [{"type": "tool_call", "name": "search"}],
    })
    body = reg.json()
    return body["agent_id"], body["agent_key"]


class TestIngestEndpoint:
    @pytest.mark.asyncio
    async def test_ingest_applies_and_summarizes(self, open_client):
        agent_id, agent_key = await _register(open_client)
        resp = await open_client.post("/telemetry/ingest", json={
            "agent_id": agent_id, "agent_key": agent_key, "source": "otel", "spans": OTEL,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["ingested_spans"] == 3
        assert body["mapped_steps"] == 3
        assert body["applied"] is True
        assert body["summary"]["error_rate"] > 0

    @pytest.mark.asyncio
    async def test_preview_does_not_apply(self, open_client):
        agent_id, agent_key = await _register(open_client)
        resp = await open_client.post("/telemetry/ingest", json={
            "agent_id": agent_id, "agent_key": agent_key, "source": "langfuse",
            "spans": LANGFUSE, "apply": False,
        })
        assert resp.status_code == 200
        assert resp.json()["applied"] is False

    @pytest.mark.asyncio
    async def test_invalid_key_rejected(self, open_client):
        agent_id, _ = await _register(open_client)
        resp = await open_client.post("/telemetry/ingest", json={
            "agent_id": agent_id, "agent_key": "wrong", "source": "otel", "spans": OTEL,
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unknown_agent_404(self, open_client):
        resp = await open_client.post("/telemetry/ingest", json={
            "agent_id": str(uuid.uuid4()), "agent_key": "x", "source": "otel", "spans": OTEL,
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_spans_rejected(self, open_client):
        agent_id, agent_key = await _register(open_client)
        resp = await open_client.post("/telemetry/ingest", json={
            "agent_id": agent_id, "agent_key": agent_key, "source": "otel", "spans": [],
        })
        assert resp.status_code == 422
