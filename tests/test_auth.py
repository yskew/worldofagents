import uuid

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.clerk import get_current_human
from app.database import get_db
from app.main import app
from app.models.human import Human

FAKE_SECRET = "test-secret"


def _make_token(sub: str = "clerk_user_1", name: str = "Test User", email: str = "test@example.com"):
    return jwt.encode({"sub": sub, "name": name, "email": email}, FAKE_SECRET, algorithm="HS256")


@pytest.fixture
async def auth_client(db_session):
    token = _make_token()

    async def override_get_current_human(
    ):
        from app.services.human_service import get_or_create_human
        return await get_or_create_human(db_session, "clerk_user_1", "Test User", "test@example.com")

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_human] = override_get_current_human
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected_in_prod_mode(client):
    """With a real Clerk key configured, unauthenticated requests are rejected."""
    from app.config import settings
    if settings.CLERK_SECRET_KEY and not settings.CLERK_SECRET_KEY.startswith("sk_test_xxx"):
        resp = await client.get("/agents")
        assert resp.status_code == 401
    else:
        resp = await client.get("/agents")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_human_created_from_clerk_claims(db_session):
    from app.services.human_service import get_or_create_human

    human = await get_or_create_human(db_session, f"clerk_{uuid.uuid4().hex[:12]}", "Alice", "alice@example.com")
    assert isinstance(human.id, uuid.UUID)
    assert human.display_name == "Alice"


@pytest.mark.asyncio
async def test_idempotent_human_creation(db_session):
    from app.services.human_service import get_or_create_human

    clerk_id = f"clerk_{uuid.uuid4().hex[:12]}"
    h1 = await get_or_create_human(db_session, clerk_id, "Bob", "bob@example.com")
    h2 = await get_or_create_human(db_session, clerk_id, "Bob", "bob@example.com")
    assert h1.id == h2.id


@pytest.mark.asyncio
async def test_human_updated_on_name_change(db_session):
    from app.services.human_service import get_or_create_human

    clerk_id = f"clerk_{uuid.uuid4().hex[:12]}"
    h1 = await get_or_create_human(db_session, clerk_id, "Old Name", None)
    h2 = await get_or_create_human(db_session, clerk_id, "New Name", "new@example.com")
    assert h2.id == h1.id
    assert h2.display_name == "New Name"
    assert h2.email == "new@example.com"
