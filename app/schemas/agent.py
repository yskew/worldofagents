from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TrajectoryStep(BaseModel):
    type: Literal["tool_call", "message", "action"]
    name: str | None = None
    content: str | None = None
    timestamp: datetime | None = None
    metadata: dict | None = None


class AgentScopesRequest(BaseModel):
    scopes: list[str] = Field(default_factory=list)


class AgentScopesResponse(BaseModel):
    allowed_scopes: list[str]


class AgentRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    sample_trajectory: list[TrajectoryStep] = Field(..., min_length=1)


class AgentRegisterResponse(BaseModel):
    agent_id: uuid.UUID
    agent_key: str
    name: str
    status: str


class AgentDetailResponse(BaseModel):
    agent_id: uuid.UUID
    name: str
    description: str | None
    status: str
    signature_summary: dict | None = None
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    agents: list[AgentDetailResponse]


class AgentRefineRequest(BaseModel):
    trajectory: list[TrajectoryStep] = Field(..., min_length=1)


class AgentPublicProfile(BaseModel):
    agent_id: uuid.UUID
    name: str
    description: str | None
    status: str
    owner_display_name: str
    created_at: datetime
    verification_count: int
    avg_similarity_score: float | None
