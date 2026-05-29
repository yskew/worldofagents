from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.agent import TrajectoryStep


class VerifyRequest(BaseModel):
    agent_id: uuid.UUID
    agent_key: str
    trajectory: list[TrajectoryStep] = Field(..., min_length=1)


class VerifyResponse(BaseModel):
    verified: bool
    similarity_score: float
    verdict: Literal["pass", "fail", "warning"]
    token: str | None = None
    breakdown: dict | None = None


class CompareRequest(BaseModel):
    trajectory_a: list[TrajectoryStep] = Field(..., min_length=1)
    trajectory_b: list[TrajectoryStep] = Field(..., min_length=1)


class CompareResponse(BaseModel):
    similarity_score: float
    verdict: Literal["pass", "fail", "warning"]
    breakdown: dict
