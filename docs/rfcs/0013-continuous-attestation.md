# RFC 0013 — Continuous Mid-Session Attestation

- **Status:** Implemented (spike)
- **Area:** `app/services/attestation.py`, `app/api/attestation.py`, Attestation UI
- **Base:** branched off `main` (independent PR).

---

## 1. Why

Verification is point-in-time: an agent proves itself once, then acts freely.
The unsolved "Agent Identity Integrity Gap" is exactly the gap *after* that
point: an agent can be model-swapped, prompt-injected, or hijacked mid-session
while its credential stays valid. This adds **continuous** attestation — monitor
the agent's behavior over a live session and detect sustained drift from its
baseline.

## 2. Design — CUSUM change-point detection

Each session is anchored to the agent's baseline signature. For every incoming
behavioral *window* we compute similarity to the baseline (the existing ensemble)
and update a one-sided CUSUM:

```
cusum = max(0, cusum + (ATTEST_REF_SIMILARITY - window_similarity))
status = alarm if cusum >= ATTEST_ALARM_THRESHOLD
         warning if cusum >= ATTEST_WARN_THRESHOLD
         else ok
```

- Normal variation (similarity above the reference) **does not accumulate** — the
  term goes negative and CUSUM stays at 0, so consistent agents never alarm.
- Sustained divergence accumulates and escalates `ok → warning → alarm`, and the
  detector **self-heals** if behavior returns to normal.

Defaults: `ref=0.5`, `warn=0.3`, `alarm=0.6` (≈ 4 fully-divergent windows to
alarm). Session state is in-memory (per-process); multi-instance needs a shared
store.

## 3. API

- `POST /attest/start` `{agent_id, agent_key}` → `{session_id}` (agent-key
  authenticated; anchors to the stored baseline).
- `POST /attest/step` `{session_id, trajectory}` → `{window_similarity, cusum,
  status, windows}`.

The emitted `status` is the natural live feed for the RFC 0011 CAEP emitter:
an `alarm` should raise a behavioral-anomaly Shared Signals event.

## 4. Demonstrated

Live: three consistent windows → `ok` (cusum 0); switching to hijacked behavior
→ `ok → warning` and on to `alarm` (similarity ~0.34, +0.16/window). Self-heals
when behavior returns (unit-tested).

## 5. Testing (API + UI)

- **API:** `tests/test_attestation.py` (6) — consistent stays ok, drift alarms,
  self-healing, invalid key (401), unknown session (404), unknown agent (404).
  Full backend suite **122 passed**.
- **UI:** Vitest `AttestationStatus.test.tsx` (3) + `api.test.ts` (2) = **5
  passed**; `tsc -b` + `vite build` + eslint clean. (Re-establishes the harness.)

## 6. Next steps

- Wire `alarm` → CAEP emit (RFC 0011) when the branches merge.
- Adaptive/per-agent thresholds learned from the telemetry corpus (RFC 0010).
- Windowing strategy (sliding vs tumbling) and EWMA variants.
- Shared session store (Redis) for horizontal scale.
