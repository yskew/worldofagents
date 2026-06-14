from __future__ import annotations

from pydantic import BaseModel, Field


class McpCallRequest(BaseModel):
    tool: str
    arguments: dict = Field(default_factory=dict)


class McpCallResponse(BaseModel):
    tool: str
    status: str
    result: dict
    agent_id: str | None = None
    principal: str | None = None


class McpToolsResponse(BaseModel):
    tools: list[dict]
