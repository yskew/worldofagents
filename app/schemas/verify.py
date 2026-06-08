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
    confidence: float | None = None  # calibrated probability (RFC 0006), when enabled


class CompareRequest(BaseModel):
    trajectory_a: list[TrajectoryStep] = Field(..., min_length=1)
    trajectory_b: list[TrajectoryStep] = Field(..., min_length=1)


class CompareResponse(BaseModel):
    similarity_score: float
    verdict: Literal["pass", "fail", "warning"]
    breakdown: dict
    confidence: float | None = None  # calibrated probability (RFC 0006), when enabled


class SimilarRequest(BaseModel):
    trajectory: list[TrajectoryStep] = Field(..., min_length=1)
    limit: int = Field(5, ge=1, le=50)


class SimilarMatch(BaseModel):
    agent_id: uuid.UUID
    name: str
    owner_display_name: str
    score: float            # full ensemble overall_score after re-rank
    vector_similarity: float  # raw pgvector cosine similarity (ANN signal)


class SimilarResponse(BaseModel):
    results: list[SimilarMatch]
    # agents excluded because their stored vector predates the active encoding
    # (run scripts/reembed.py to include them)
    stale_excluded: int = 0
