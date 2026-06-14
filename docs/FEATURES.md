# World of Agents — Feature Status

Status of every capability: **shipped**, **in progress / pending**, or **future
scope**. PR and RFC references point to the design + test artifacts. "Default"
indicates whether a flag-gated capability is on by default.

Legend: ✅ shipped & tested · 🟡 built but gated off / pending wiring · ⬜ future scope

---

## 1. Core platform (baseline, `main`)

| Capability | Status | Notes |
|------------|:------:|-------|
| Agent registration with behavioral signature | ✅ | 7-feature-family signature from a sample trajectory |
| Agent key issuance (bcrypt, one-time) | ✅ | 48-byte URL-safe key, hashed at rest |
| Passive verification (`/verify`) + RS256 delegated JWT | ✅ | `sub`=human, `act.sub`=agent (RFC 8693 pattern) |
| Trajectory comparison (`/compare`) | ✅ | Stateless similarity |
| JWKS endpoint, public agent profile | ✅ | Downstream token verification |
| Human auth via Clerk | ✅ | Unchanged across all later work |
| Agent lifecycle: refine, rotate-key, revoke | ✅ | Soft-delete + audit log |
| Postgres + pgvector, Alembic migrations, Docker/Railway | ✅ | |

## 2. Signature-engine improvements

| RFC | Capability | Status | Default | PR |
|-----|------------|:------:|:------:|----|
| 0001 | Confidence-aware scoring (abstain + redistribute weights) | ✅ | **on** | #1 |
| 0002 | Hashed vector encoding (stable per-tool dims, bounded transforms) | ✅ | **on** | #1 |
| 0003 | Offline eval harness + powered default flip | ✅ | n/a | #1 |
| 0004 | Learned ensemble weights (logistic regression) | 🟡 | off | #1 |
| 0005 | `POST /similar` — pgvector ANN + ensemble re-rank (HNSW) | ✅ | on | #1 |
| 0006 | Score calibration (Platt scaling, `confidence` field) | 🟡 | off | #1 |
| 0007 | Hardening — JWT fail-loud, dev-auth gating, rate limit, CORS | ✅ | on | #1 |
| 0008 | Active challenge-response verification (replay-proof) | ✅ | additive | #1 |

> RFC 0004 and 0006 are **built and tested but intentionally disabled**: they were
> fit on synthetic data and overfit / are uncalibrated for production. They flip on
> once a real labeled corpus exists (see Telemetry, §3).

## 3. Integration & SOTA layer

| RFC | Capability | Status | PR | API tests | UI tests |
|-----|------------|:------:|----|:---------:|:--------:|
| 0009 | RFC 8693 token-exchange broker + OIDC federation (Okta/Entra/Auth0/Google), per-agent scopes | ✅ | #2 | 8 | n/a |
| 0010 | Telemetry ingestion (OpenTelemetry GenAI + Langfuse + Braintrust) → signature enrichment | ✅ | #3 | 10 | 5 |
| 0011 | Shared Signals / CAEP risk emitter (SETs, poll + push) | ✅ | #4 | 9 | 4 |
| 0012 | MCP / A2A reference authorization server (tool-call gating) | ✅ | #5 | 8 | 5 |
| 0013 | Continuous mid-session attestation (CUSUM drift detection) | ✅ | #6 | 6 | 5 |

## 4. Frontend

| Capability | Status | Notes |
|------------|:------:|-------|
| Pixel-art platform UI (Dashboard, Agents, Verify, Compare, Docs) | ✅ | Baseline |
| Telemetry, Signals, MCP, Attestation pages | ✅ | One per integration feature (PRs #3–#6) |
| Frontend test harness (Vitest + React Testing Library) | ✅ | Established in PR #3, reused thereafter |
| Effective-weights / abstained-metric rendering | ✅ | Reflects RFC 0001 |

---

## 5. Pending / in progress

These are built-but-gated or awaiting a dependency, not new research:

- **Flip learned weights (0004) and calibration (0006) defaults** — blocked on a
  real labeled corpus; Telemetry (0010) is the collection mechanism.
- **Discriminative probe selection (0008)** — current selection is nonce-seeded
  random; ranking probes by population-discriminativeness needs the corpus.
- **Cross-feature wiring** (lands when the independent PRs merge):
  - continuous-attestation `alarm` → CAEP emit (0013 → 0011),
  - MCP tool authorization derived from broker token scopes (0012 ← 0009).
- **Cross-provider account linking** — external-OIDC humans owning Clerk-registered
  agents (broker, 0009).
- **Multi-instance state** — move in-memory stores (rate limiter, challenge
  nonces, SSF queue, attestation sessions) to a shared store (Redis).
- **Full browser E2E** — requires a Clerk publishable key / dev auth fallback;
  current UI coverage is component + client + production build.

---

## 6. Future scope

Larger bets not yet started, roughly in priority order:

1. **Real-trajectory benchmark + leaderboard** — turn the synthetic eval harness
   (0003) into an open, multi-model, multi-framework corpus + public benchmark for
   agent behavioral identity. Unblocks 0004/0006/probes and the item below.
2. **Learned contrastive trajectory embeddings** — replace bag-of-statistics with
   a trained encoder (contrastive same/different objective), stored in the existing
   pgvector column behind the `features_to_vector` interface.
3. **Cryptographic runtime root (TEE / signed manifest)** — bind model-weights
   hash + system-prompt hash + tool set to remote attestation, making agent
   runtime identity *cryptographic*; behavior becomes the liveness layer atop it.
4. **Decentralized & privacy-preserving verification** — verifiable credentials /
   DIDs so receivers verify without calling home; ZK proof of signature match so
   identity is proven without revealing the trajectory.
5. **Full MCP transport + A2A handshake** — JSON-RPC over stdio/SSE; the current
   work implements the authorization decision, not the transport.
6. **Full SSF stream lifecycle** — RFC 8935 stream registration/verification
   endpoints (currently static config + poll/push).
7. **Standards contribution** — submit the behavioral-attestation profile to the
   IETF / OpenID agent-identity efforts.
8. **Adaptive thresholds & per-agent calibration** — learned from the corpus.

---

## 7. PR map

| PR | Branch | Base | Contents |
|----|--------|------|----------|
| #1 | `raghul-branch` | main | RFC 0001–0008 (engine + hardening + active verification) |
| #2 | `raghul-broker` | `raghul-branch` | RFC 0009 (token-exchange broker) |
| #3 | `raghul-telemetry` | `raghul-broker` | RFC 0010 (telemetry) + frontend harness |
| #4 | `raghul-caep` | main | RFC 0011 (Shared Signals / CAEP) |
| #5 | `raghul-mcp` | main | RFC 0012 (MCP auth server) |
| #6 | `raghul-attest` | main | RFC 0013 (continuous attestation) |

Each RFC has a design doc in `docs/rfcs/` and a test report in `docs/reports/`.
