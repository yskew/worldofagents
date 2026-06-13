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


# --- Active challenge-response verification (RFC 0008) -----------------------

class ChallengeProfileRequest(BaseModel):
    # {probe_id: trajectory the agent produced for that probe}
    responses: dict[str, list[TrajectoryStep]] = Field(..., min_length=1)


class ChallengeProfileResponse(BaseModel):
    profiled_probes: list[str]


class ChallengeRequest(BaseModel):
    agent_id: uuid.UUID


class Probe(BaseModel):
    id: str
    stimulus: str


class ChallengeResponse(BaseModel):
    challenge_token: str
    probes: list[Probe]
    expires_in: int


class ActiveVerifyRequest(BaseModel):
    agent_id: uuid.UUID
    agent_key: str
    challenge_token: str
    responses: dict[str, list[TrajectoryStep]] = Field(..., min_length=1)


class ActiveVerifyResponse(BaseModel):
    verified: bool
    active_score: float
    verdict: Literal["pass", "fail", "warning"]
    token: str | None = None
    per_probe: dict[str, float]


# --- Telemetry ingestion (RFC 0010) -----------------------------------------

class TelemetryIngestRequest(BaseModel):
    agent_id: uuid.UUID
    agent_key: str
    source: Literal["otel", "langfuse", "braintrust"]
    spans: list[dict] = Field(..., min_length=1)
    # When False, map + summarize only (preview) without mutating the signature.
    apply: bool = True


class TelemetryIngestResponse(BaseModel):
    source: str
    ingested_spans: int
    mapped_steps: int
    summary: dict
    applied: bool
