import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "agentverify"
    assert body["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_db_connected(client):
    resp = await client.get("/health/db")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["db"] == "connected"
