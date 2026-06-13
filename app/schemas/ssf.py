from __future__ import annotations

from pydantic import BaseModel, Field


class PollRequest(BaseModel):
    # RFC 8936 poll delivery request (subset).
    maxEvents: int = Field(100, ge=1, le=1000)
    ack: list[str] = Field(default_factory=list)


class PollResponse(BaseModel):
    sets: dict[str, str]
