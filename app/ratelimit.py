"""Lightweight in-memory per-IP rate limiter (RFC 0007).

A fixed-window-ish sliding counter keyed by client IP, used as a FastAPI
dependency on the open scoring endpoints (/verify, /compare, /similar) to blunt
abuse of the compute-heavy ensemble. In-memory and per-process: fine for a
single instance; a multi-instance deployment should back this with a shared
store (e.g. Redis). Controlled by settings.RATE_LIMIT_ENABLED /
RATE_LIMIT_PER_MINUTE.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.config import settings

_WINDOW_SECONDS = 60.0
_hits: dict[str, deque] = defaultdict(deque)


def reset() -> None:
    """Clear all counters (used by tests)."""
    _hits.clear()


def rate_limit(request: Request) -> None:
    if not settings.RATE_LIMIT_ENABLED:
        return
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    dq = _hits[ip]
    cutoff = now - _WINDOW_SECONDS
    while dq and dq[0] <= cutoff:
        dq.popleft()
    if len(dq) >= settings.RATE_LIMIT_PER_MINUTE:
        retry_after = max(1, int(dq[0] + _WINDOW_SECONDS - now))
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    dq.append(now)
