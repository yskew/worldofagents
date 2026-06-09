# RFC 0008 — Active Challenge-Response Verification

- **Status:** Implemented (spike)
- **Area:** `app/services/challenge.py`, `challenge_bank.py`, `POST /challenge`, `POST /verify/active`, `POST /agents/{id}/challenge-profile`
- **Depends on:** RFC 0001/0002 (signature engine), RFC 0007 (rate limiting)

---

## 1. Why (the SOTA reframe)

Passive `/verify` accepts whatever trajectory the caller submits and compares it
to the stored signature. Its fatal weakness, which the whole field shares: an
attacker who once observed the agent can **replay a recorded "good" trajectory**
and pass. Behavioral identity is only as strong as it is *fresh and unspoofable*.

The SOTA move (LLMmap, USENIX 2025: >95% model ID from 8 crafted probes) is
**active measurement**: the *verifier* chooses what to ask, freshly, each time.
The agent must respond to *those* probes *now*. A recording can't answer a
question it never saw, and an impostor with a different model / system prompt /
tool set answers measurably differently.

This RFC adds active verification alongside passive `/verify`.

## 2. Protocol

```
register agent ─▶ POST /agents/{id}/challenge-profile   (authed, once)
                    store per-probe response signatures

verify (active):
  POST /challenge {agent_id}
    ─▶ server picks probes (seeded by a fresh nonce), returns
       { challenge_token (signed, nonced, expiring), probes:[{id,stimulus}] }
  agent executes those probes LIVE
  POST /verify/active {agent_id, agent_key, challenge_token, responses}
    ─▶ validate token (HMAC sig, expiry, single-use nonce)
    ─▶ compare each response to the stored per-probe profile (ensemble)
    ─▶ if mean score >= threshold: issue delegated JWT
```

## 3. Why it resists the attacks

| Attack | Defense |
|--------|---------|
| Replay a recorded passing response | Challenge token is **single-use** (nonce store) and **short-lived** (expiry). The recorded response was bound to a spent nonce. |
| Forge / edit a challenge | Token is **HMAC-signed**; any tamper fails `decode()` (400). |
| Use another agent's challenge | Token binds `agent_id`; mismatch rejected (400). |
| Predict which probes will be asked | Probe selection is **seeded by the server's fresh nonce**, unknown to the caller until issuance. |
| Impostor with the stolen key | Key check still passes, but **behavioral responses diverge** from the profile → score below threshold → fail. |

The agent key remains the cryptographic factor; active verification makes the
*behavioral* factor fresh and replay-proof rather than a static sample.

## 4. Implementation

- **`challenge.py`** — stateless tokens: `b64(payload).b64(hmac_sha256(payload))`,
  payload `{agent_id, probe_ids, nonce, iat, exp}`. No DB row needed; integrity
  from HMAC, freshness from expiry, single-use from an in-memory nonce store
  (use a shared store for multi-instance, like the RFC 0007 limiter).
- **`challenge_bank.py`** — probe definitions and nonce-seeded selection. Reuses
  the existing signature engine to score responses against the profile.
- **`agents.challenge_profile`** (JSONB, nullable; migration `d4e5f6a7b8c9`) —
  `{probe_id: signature}` captured at profiling time.
- Endpoints are rate-limited (RFC 0007) and gated like the other open routes.

## 5. Demonstrated

Live, end-to-end: genuine agent → `verified=True` (score 1.0, JWT issued);
**replay of the same valid request → HTTP 409**; impostor with the correct key
but different behavior → `verified=False` (score 0.33). Tests in
`tests/test_active_verification.py` (10) cover token primitives and every attack
above. Full suite: 191 passed.

## 6. Limitations & next steps (toward full SOTA)

This is a spike. To make it production- and research-grade:

- **Discriminative probe selection.** Today selection is nonce-seeded random over
  the agent's profiled probes. The real win is ranking probes by
  *discriminativeness* — where the agent's response diverges most from the
  population — to maximize identifying power per probe (LLMmap's core idea).
- **Probe realism.** Stimuli are abstract scenarios; a production bank would use
  probes empirically shown to separate models/agents, validated on the RFC 0003
  corpus.
- **Profile freshness.** Profiles should refine over time (cf. `/refine`) and
  carry a confidence that grows with observations.
- **Shared nonce store** (Redis) for horizontal scale.
- **Binding to runtime attestation** (RFC future): combine the behavioral
  challenge with a signed model/prompt manifest to make the identity
  cryptographic, not just probabilistic.
