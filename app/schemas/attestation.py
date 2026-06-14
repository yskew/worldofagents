from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.agent import TrajectoryStep


class AttestStartRequest(BaseModel):
    agent_id: uuid.UUID
    agent_key: str


class AttestStartResponse(BaseModel):
    session_id: str


class AttestStepRequest(BaseModel):
    session_id: str
    trajectory: list[TrajectoryStep] = Field(..., min_length=1)


class AttestStepResponse(BaseModel):
    window_similarity: float
    cusum: float
    status: Literal["ok", "warning", "alarm"]
    windows: int
