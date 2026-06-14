"""Continuous mid-session attestation (RFC 0013).

Verification today is point-in-time: an agent proves itself once, then acts
freely. This adds *continuous* attestation — a CUSUM change-point detector over a
live stream of behavioral windows, comparing each window to the agent's baseline
signature. Sustained downward drift (a model swap, prompt injection, or hijack
mid-session) accumulates and raises an alarm, while normal variation does not.

Session state is in-memory (per-process); a multi-instance deployment should use
a shared store. The emitted status is the natural signal source for the CAEP
emitter (RFC 0011).
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass

from app.config import settings
from app.schemas.agent import TrajectoryStep
from app.services.signature_engine import compare_signatures, extract_features, features_to_vector


@dataclass
class Session:
    agent_id: str
    baseline: dict
    baseline_vec: list
    cusum: float = 0.0
    windows: int = 0
    status: str = "ok"


_sessions: dict[str, Session] = {}


def reset() -> None:
    _sessions.clear()


def get(session_id: str) -> Session | None:
    return _sessions.get(session_id)


def start(agent) -> str:
    """Open a session anchored to the agent's stored baseline signature."""
    session_id = secrets.token_urlsafe(16)
    base = agent.signature or {}
    _sessions[session_id] = Session(
        agent_id=str(agent.id), baseline=base, baseline_vec=features_to_vector(base),
    )
    return session_id


def _classify(cusum: float) -> str:
    if cusum >= settings.ATTEST_ALARM_THRESHOLD:
        return "alarm"
    if cusum >= settings.ATTEST_WARN_THRESHOLD:
        return "warning"
    return "ok"


def ingest(session_id: str, steps: list[TrajectoryStep]) -> dict | None:
    """Score one behavioral window against the baseline and update the CUSUM.

    Returns None if the session is unknown."""
    session = _sessions.get(session_id)
    if session is None:
        return None
    features = extract_features(steps)
    vec = features_to_vector(features)
    similarity = compare_signatures(session.baseline, session.baseline_vec, features, vec)["overall_score"]

    # one-sided CUSUM for a downward shift in similarity
    session.cusum = max(0.0, session.cusum + (settings.ATTEST_REF_SIMILARITY - similarity))
    session.windows += 1
    session.status = _classify(session.cusum)
    return {
        "window_similarity": round(similarity, 4),
        "cusum": round(session.cusum, 4),
        "status": session.status,
        "windows": session.windows,
    }
