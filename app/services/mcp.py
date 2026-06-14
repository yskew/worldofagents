"""MCP / A2A reference authorization (RFC 0012).

The greenfield: MCP servers expose tools with (today) no auth. This is a
reference authorization layer that gates a tool call on (a) a valid behavioral-
attestation token issued by us (verified against our JWKS) and (b) a per-agent
tool allowlist. An MCP server / proxy calls `authorize()` before executing a tool.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_issuer import get_jwt_issuer
from app.config import settings
from app.models.agent import Agent

# Reference tool catalog exposed by this MCP server.
TOOLS = [
    {"name": "search", "description": "Search the codebase or web"},
    {"name": "read_file", "description": "Read a file"},
    {"name": "edit_file", "description": "Edit a file"},
    {"name": "run_tests", "description": "Run the test suite"},
    {"name": "deploy", "description": "Deploy to an environment"},
]
TOOL_NAMES = {t["name"] for t in TOOLS}


@dataclass
class Decision:
    allowed: bool
    status: int = 200
    reason: str = "ok"
    human: str | None = None
    agent_id: str | None = None
    agent_name: str | None = None


async def authorize(token: str, tool: str, db: AsyncSession) -> Decision:
    """Authorize an MCP tool call from a bearer attestation token."""
    try:
        claims = jwt.decode(
            token, get_jwt_issuer().public_key, algorithms=["RS256"],
            issuer=settings.JWT_ISSUER, options={"verify_aud": False},
        )
    except jwt.PyJWTError as e:
        return Decision(False, 401, f"invalid_token: {e}")

    agent_id = (claims.get("act") or {}).get("sub")
    human = claims.get("sub")
    if not agent_id:
        return Decision(False, 401, "token missing act.sub")
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        return Decision(False, 401, "malformed agent id in token")

    agent = (await db.execute(select(Agent).where(Agent.id == agent_uuid))).scalar_one_or_none()
    if agent is None or agent.status == "revoked":
        return Decision(False, 403, "agent_revoked", human, agent_id)

    if tool not in (agent.tool_allowlist or []):
        return Decision(False, 403, f"tool_not_authorized: {tool}", human, agent_id, agent.name)

    return Decision(True, 200, "ok", human, agent_id, agent.name)
