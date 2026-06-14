"""MCP / A2A reference authorization server (RFC 0012).

Exposes a tool catalog and a guarded tool-call endpoint. A real MCP server/proxy
would call the same `mcp.authorize()` before executing any tool.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas.mcp import McpCallRequest, McpCallResponse, McpToolsResponse
from app.services import mcp

router = APIRouter(tags=["mcp"])


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return authorization.split(" ", 1)[1]


@router.get("/mcp/tools")
async def list_tools() -> McpToolsResponse:
    return McpToolsResponse(tools=mcp.TOOLS)


@router.post("/mcp/call")
async def call_tool(
    body: McpCallRequest,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> McpCallResponse:
    if not settings.MCP_ENABLED:
        raise HTTPException(status_code=503, detail="MCP server disabled")
    if body.tool not in mcp.TOOL_NAMES:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {body.tool}")

    token = _bearer(authorization)
    decision = await mcp.authorize(token, body.tool, db)
    if not decision.allowed:
        raise HTTPException(status_code=decision.status, detail={"error": decision.reason})

    # Reference execution: a real server would dispatch to the tool here.
    return McpCallResponse(
        tool=body.tool,
        status="executed",
        result={"echo": body.arguments},
        agent_id=decision.agent_id,
        principal=decision.human,
    )
