# World of Agents — Repository Analysis Report

*Analysis date: 2026-06-08. Based on a full read of the codebase (backend, frontend, infra, tests, docs) at `main` (`04a2903`).*

---

## 1. What this project is, in one paragraph

**World of Agents** is a research-grade MVP for an **identity layer for AI agents**. Its premise: every AI agent acting in the world today does so either with *no identity* or a *stolen one* (a developer's pasted OAuth token or API key), so no downstream system can answer "which human is responsible for this action, is this the same agent that was authorized, and is it behaving normally?" The project builds the two missing pieces of agent identity — **binding** (provably linking an agent to its human owner) and **runtime identity** (recognizing a specific agent by its behavior) — while deliberately delegating the parts that already work (human auth, authorization) to mature systems. Its novel contribution is a **behavioral signature engine** that fingerprints an agent from its trajectory (sequence of tool calls + messages) and, on verification, issues a delegated **RS256 JWT** where `sub` = the human and `act.sub` = the agent (the RFC 8693 token-exchange / delegation pattern).

It is explicitly positioned (in `THESIS.md`) as a vendor-neutral, open-source, self-hosted alternative to vendor-locked offerings (Microsoft Entra Agent ID, Google Vertex) and to other open projects (ZeroID, NVIDIA AIP) — none of which do behavioral verification.

---

## 2. The core idea: four-layer identity model

From the thesis, agent identity has four layers; only two are missing, and this project builds exactly those two:

| Layer | What it does | Status today | Built here? |
|-------|-------------|--------------|-------------|
| Human Identity | Who the human owner is | Solved (Okta, Google, Clerk) | Delegated to **Clerk** |
| **Binding** | Provable human↔agent link | **Missing** | ✅ Built |
| **Agent Runtime Identity** | Recognize this specific agent | **Missing** | ✅ Built (behavioral signatures) |
| Authorization | Scoped, short-lived creds | Solved (OAuth, OIDC, RFC 8693) | Delegated (issues RFC-8693-style JWTs) |

**Design philosophy: "We do not reinvent the identity wheel. We finish it."** Clerk handles human auth; bcrypt hashes keys; PyJWT signs tokens; PostgreSQL + pgvector store embeddings; scipy/numpy do the math. The genuinely invented parts are: (1) the binding flow, (2) the behavioral signature engine, (3) the delegated-JWT broker, (4) the agent lifecycle (register/verify/refine/rotate/revoke).

---

## 3. How it works end-to-end

### Registration (authenticated, Clerk)
1. Human signs in via Clerk.
2. Submits agent name, description, and a **sample trajectory** (JSON array of `{type, name, content, timestamp, metadata}` steps).
3. Engine extracts a **behavioral signature** (7 feature categories) → stored as JSONB + a 256-dim pgvector embedding.
4. A 48-byte URL-safe random **agent key** is generated (`secrets.token_urlsafe(48)`), bcrypt-hashed, and **shown exactly once** (never stored in plaintext, never retrievable).

### Verification (open, no auth)
1. Caller posts `agent_id` + `agent_key` + a fresh `trajectory` to `POST /verify`.
2. **Cryptographic check** — bcrypt match against stored hash (hard pass/fail).
3. **Behavioral check** — current trajectory's signature is compared to the stored one → similarity score 0.0–1.0.
4. If key matches **and** score ≥ 0.7 → an **RS256 JWT** is issued (`sub`=human, `act.sub`=agent, plus `agent_name`, `similarity_score`, `jti`, `exp`). Every attempt is logged (score, pass/fail, IP).
5. Downstream systems verify the JWT against the public **`/.well-known/jwks.json`** endpoint.

### Other lifecycle ops
- **`/compare`** (open) — compare two trajectories directly, no persistence.
- **`/refine`** — merge new trajectory into the stored signature via exponential weighted averaging (70% old / 30% new) so legit drift adapts but a single submission can't overwrite the profile.
- **`/rotate-key`** — issue a new key, invalidate the old one immediately.
- **`DELETE /agents/{id}`** — soft delete (status → `revoked`).

---

## 4. The behavioral signature engine (the core IP)

Implemented in `app/services/signature_engine.py` — verified against the thesis claims.

**Seven extracted feature categories:**
1. **Tool-call histogram** — normalized frequency of each tool/action.
2. **Bigram transition matrix** — Markov model of sequential tool-call probabilities.
3. **Trigram transitions** — three-step sequence patterns.
4. **Response-length stats** — mean, variance, skewness of message lengths.
5. **Vocabulary stats** — unique/total tokens, type-token ratio, top-20 tokens.
6. **Timing stats** — mean/std/max inter-action intervals (only if timestamps present).
7. **Structural features** — sequence length, unique action types, tool-call ratio, error/retry ratio.

**Storage (dual):** full feature dict as **JSONB** (debuggable, per-metric comparison) + a **256-dim L2-normalized vector** (pgvector) for fast similarity. *Note: the vector packing uses fixed index ranges (0–49 histogram, 50–99 bigrams, 150–199 trigrams, 200s stats) and leaves ~72 of 256 slots unused — the dimension is somewhat aspirational.*

**Comparison ensemble** (weights confirmed in code, `compare_signatures`):

| Metric | Measures | Weight | Method |
|--------|----------|--------|--------|
| Tool distribution | Same tools, similar proportions? | 25% | Jensen-Shannon divergence on histograms |
| Feature vector | Overall embedding similarity | 30% | Cosine similarity on 256-dim vectors |
| Sequence pattern | Same call order? | 25% | Per-state JSD on transition matrices |
| Statistical profile | Communicates similarly? | 20% | Normalized diff of response-length means + type-token ratios |

`overall = 0.25·jsd + 0.30·cos + 0.25·markov + 0.20·stats` → verdict: **≥0.7 pass**, **≤0.4 fail**, **between = warning** (thresholds configurable via env).

**Intellectual honesty (stated explicitly in the thesis and matched by the code):** behavioral signatures are **anomaly detection, not authentication**. The cryptographic strength is the bcrypt key + the RS256 token; the signature only detects drift, impersonation, and model swaps. The project commits to never claiming otherwise. The thesis cites academic backing (LLMmap USENIX 2025; GitHub agent fingerprinting; stylometric ensembles).

---

## 5. Architecture & tech stack

```
┌────────────────────────────┐         ┌──────────────────────────────┐
│  Frontend (React 19 + Vite)│  HTTPS  │  Backend (FastAPI, async)    │
│  Clerk auth, pixel-art UI  │────────▶│  /agents /verify /compare     │
│  Three.js globe, Tailwind  │  JWT    │  /.well-known/jwks.json        │
└────────────────────────────┘         └──────────────┬───────────────┘
                                                       │ async SQLAlchemy
                                        ┌──────────────▼───────────────┐
                                        │ PostgreSQL 17 + pgvector      │
                                        │ humans / agents / verif_log   │
                                        └───────────────────────────────┘
   External services ──verify JWT via JWKS──▶ (trust sub=human, act.sub=agent)
```

**Backend:** Python 3.12, FastAPI 0.115+, SQLAlchemy 2.0 (async, asyncpg), Alembic, PostgreSQL 17 + pgvector(256), PyJWT[crypto] (RS256), bcrypt, scipy + numpy.

**Frontend:** React 19 + TypeScript + Vite 8 + Tailwind 4 (fully custom design tokens), React Router 7, Clerk React SDK, Three.js 0.184. Six pages: Landing, Dashboard, Agents, Verify, Compare, Docs. Centralized API client injects the Clerk Bearer token automatically.

**Design language:** deliberate **retro pixel-art / 80s-CRT aesthetic** — Silkscreen + Space Mono fonts, scanline overlay, zero border-radius, warm dark palette (paper `#1c1916`, coral `#d97757`, cream `#f0eee6`). Handcoded canvas animations: pixelated Three.js globe (rendered 96×96, nearest-neighbor upscaled), shield scanner, robot-fight (for `/compare`), astronaut, plus a row-by-row pixel-dissolve page transition on sign-in.

**Infra/deploy:** Docker Compose with 4 services — `api`, `frontend`, `postgres` (pgvector image, host port 5434→5432), `mailpit` (email testing). `start.sh` runs `alembic upgrade head` then uvicorn. Railway-ready via `railway.json` (health check `/health`, migrations on deploy). Two frontend Dockerfiles (dev + `.prod`).

---

## 6. Data model (3 tables, confirmed in migration `012117a4a32b`)

- **`humans`** — `id` (UUID PK), `clerk_id` (unique, indexed), `display_name`, `email`, `created_at`.
- **`agents`** — `id`, `human_id` (FK, indexed), `name`, `description`, `key_hash` + `key_salt` (bcrypt), `signature` (JSONB), `signature_vector` (Vector(256)), `status` (active/revoked), `created_at`/`updated_at`.
- **`verification_log`** — `id`, `agent_id` (FK, indexed), `similarity_score`, `passed`, `ip_address`, `requested_at`.

Extensions: `pgvector`, `uuid-ossp`.

---

## 7. API surface

**Authenticated (Clerk session):** `POST /agents/register`, `GET /agents`, `GET /agents/{id}`, `DELETE /agents/{id}`, `POST /agents/{id}/refine`, `POST /agents/{id}/rotate-key`.

**Open (no auth):** `POST /verify`, `POST /compare`, `GET /agents/{id}/public`, `GET /.well-known/jwks.json`, `GET /health`, `GET /health/db`.

The "open by design" choice is intentional: external services must be able to verify agents and fetch public profiles/keys without logging in. Only owner-scoped operations require Clerk.

---

## 8. Testing & maturity

- **116 tests across 9 suites, ~86% coverage** (claimed in docs; suite files all present). Notable scenarios: impersonation detection (coding agent verified with malicious behavior → score drops → fail), key-rotation security (old key → 401), multi-tenant isolation, signature symmetry (A→B == B→A), and a 12-step full-lifecycle test.
- Version is **v0.1.0** — explicitly a research MVP.

---

## 9. Honest assessment: gaps & caveats

The thesis is unusually candid, and the code largely backs the claims. Things to be aware of:

- **Prototype-grade hardening.** CORS is wide open (`allow_origins=["*"]` with `allow_credentials=True`); no rate limiting on the compute-heavy `/verify` and `/compare`; minimal observability/logging.
- **Dev-mode auth bypass.** If `CLERK_SECRET_KEY` is empty or the `sk_test_xxx` placeholder, auth returns a hardcoded demo user — convenient for local dev, dangerous if shipped.
- **JWT key fallback.** If RSA keys aren't supplied, the issuer auto-generates a new keypair on startup — every restart would invalidate previously issued tokens. Production must set `RSA_PRIVATE_KEY_PEM`/`RSA_PUBLIC_KEY_PEM` (generator script provided).
- **256-dim vector underutilized** (~72 unused slots); feature normalization uses fixed magic divisors rather than adaptive scaling.
- **Neutral-score defaults.** Markov and stats sub-scores return 0.5 when data is missing, which can nudge borderline verdicts.
- **Behavioral layer is soft by design** — it is anomaly detection, not proof of identity. The project says so repeatedly; just don't mistake the similarity score for cryptographic assurance.

---

## 10. Competitive positioning (per thesis)

The differentiator is **behavioral verification**, which no production system implements:

| Capability | World of Agents | ZeroID | NVIDIA AIP | Entra Agent ID |
|------------|:---:|:---:|:---:|:---:|
| Behavioral verification | **✅ core** | ❌ | ❌ | ❌ |
| Open source | ✅ | ✅ | ✅ | ❌ |
| Vendor-neutral | ✅ | ✅ | ✅ | ❌ (MS) |
| Self-hosted | ✅ | ✅ | ✅ | ❌ |
| RFC 8693 delegation | ✅ | ✅ | ❌ | partial |
| Signature refinement | ✅ | ❌ | ❌ | ❌ |

Roadmap (thesis §8): World ID for sybil resistance, OIDC federation, verifier SDKs, reference MCP server integration, and eventual submission to IETF agent-identity working groups.

---

## 11. Bottom line

World of Agents is a **coherent, well-documented MVP** that makes one genuinely novel bet — fingerprinting agents by *behavior* and folding that into a delegated-token identity broker — while sensibly reusing battle-tested infrastructure for everything else. The implementation matches its own documentation closely, including its honest framing that the behavioral layer is probabilistic anomaly detection rather than hard authentication. It is research/demo quality (v0.1.0): the core flows are real, tested, and runnable via Docker, but it needs production hardening (CORS, rate limits, key management, removing the dev auth bypass) before any real-world deployment.

**One-sentence pitch (from the repo):** *"World of Agents is the missing identity layer for AI agents — a free, open platform that lets any agent prove which human owns it and act on that human's behalf using delegated credentials, with full behavioral verification and attribution."*
