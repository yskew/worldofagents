"""Challenge bank for active verification (RFC 0008).

A probe is a stimulus the agent must respond to *live*. Because the verifier
chooses which probes to issue (per challenge, seeded by a fresh nonce), an
attacker cannot pre-record a passing trajectory: they must respond to these
probes, now. An impostor with a different model / system prompt / tool set
responds measurably differently from the registered agent.

The stimuli here are abstract scenarios; the discriminating signal is *how* the
agent responds (tool-call pattern, sequence, verbosity), captured by the existing
signature engine over the response trajectory.
"""
from __future__ import annotations

import hashlib
import random

# id -> human-facing stimulus the agent is asked to act on.
PROBES: list[dict] = [
    {"id": "p_debug", "stimulus": "A unit test is failing intermittently. Investigate and fix it."},
    {"id": "p_research", "stimulus": "Find the current best practice for X and summarize with sources."},
    {"id": "p_refactor", "stimulus": "Refactor this module for readability without changing behavior."},
    {"id": "p_deploy", "stimulus": "Roll out the new build to staging and confirm it is healthy."},
    {"id": "p_data", "stimulus": "Load yesterday's events into the warehouse and validate row counts."},
    {"id": "p_secscan", "stimulus": "Scan this repository for leaked secrets and risky dependencies."},
    {"id": "p_incident", "stimulus": "Latency just spiked in production. Diagnose the cause."},
    {"id": "p_summarize", "stimulus": "Summarize this 40-page document into five bullet points."},
]

PROBE_IDS = [p["id"] for p in PROBES]
_BY_ID = {p["id"]: p for p in PROBES}


def get_probe(probe_id: str) -> dict | None:
    return _BY_ID.get(probe_id)


def select_probes(agent_id: str, nonce: str, available_ids: list[str], k: int) -> list[str]:
    """Deterministically pick k probes for this challenge, seeded by the fresh
    nonce so the selection is unpredictable to the caller but reproducible by the
    server. Only probes the agent has a stored profile for are eligible.

    NOTE: this is the spike's selection. The SOTA target (RFC 0008 §6) ranks
    probes by discriminativeness (where the agent's stored response diverges most
    from the population), maximizing identifying power per probe.
    """
    pool = [pid for pid in available_ids if pid in _BY_ID]
    if not pool:
        return []
    seed = int(hashlib.sha256(f"{agent_id}:{nonce}".encode()).hexdigest(), 16)
    rng = random.Random(seed)
    rng.shuffle(pool)
    return pool[: min(k, len(pool))]
