# World of Agents: An Identity Layer for AI Agents

## Thesis Document for Presentation

---

## 1. THE PROBLEM

### 1.1 What is happening today

AI agents are autonomous software programs that act on behalf of humans — they write code, deploy infrastructure, send emails, query databases, and interact with APIs. The number of AI agents in production is growing exponentially. OpenAI's GPTs, Anthropic's Claude with MCP, LangChain agents, Microsoft Copilot, Google's Gemini agents, and thousands of custom-built agents are operating in enterprise and consumer environments daily.

Every single one of these agents has an identity problem.

### 1.2 The identity gap

When an AI agent needs to access a service (GitHub, Snowflake, Slack, an internal API, an MCP server), it authenticates in one of two ways:

**Option A: No identity at all.** The agent operates with no authentication, relying on the assumption that it's running in a trusted environment. This is common in local setups where agents inherit the host machine's permissions.

**Option B: Stolen identity.** A developer copies their personal OAuth token, API key, or session cookie into the agent's environment variables. The agent now has full, indistinguishable access to everything the human can do. There is no audit trail that differentiates whether an action was taken by the human or by the agent.

Neither option is acceptable. Service accounts (the traditional answer for non-human workloads) don't fit either — they are static, long-lived, and designed for predictable, non-autonomous workloads. Agents are autonomous, probabilistic, and their behavior changes with every prompt.

### 1.3 The specific questions nobody can answer

When an AI agent makes a request to any system, that system cannot answer these fundamental questions:

1. **"Which human is responsible for this action?"** — The question that underlies all of human IAM (Identity and Access Management) is unanswerable for agent actions.

2. **"Is this the same agent that was authorized?"** — If an agent's model is swapped, its system prompt is changed, or it is replaced entirely, no system can detect this. The credentials remain valid regardless of who or what is using them.

3. **"Is this agent behaving normally?"** — Even if you know which agent is acting, there is no baseline to compare against. An agent that suddenly starts accessing resources it has never touched before looks identical to one doing its normal job.

### 1.4 Why this matters now

Three forces are converging:

- **MCP (Model Context Protocol) and agent-to-agent protocols are exploding.** Anthropic's MCP, Google's A2A protocol, and similar standards are creating an ecosystem where agents call other agents and external tools. A scan of ~2,000 MCP servers found that every single one lacked authentication. The identity vacuum is real and growing.

- **Enterprise adoption is accelerating.** Companies are deploying agents internally for code review, incident response, data pipeline management, and customer support. Each agent needs credentials. Each credential is a liability.

- **Regulatory pressure is building.** NIST launched the CAISI AI Agent Standards Initiative in February 2026. The IETF has four active drafts on agent identity. The Cloud Security Alliance published an Agentic AI IAM Framework. Standards are coming — the question is whether they'll be built by vendors with lock-in incentives or by an open community.

---

## 2. THE INSIGHT

### 2.1 Four layers of agent identity

Identity for AI agents has four layers. Three of them already exist in mature, battle-tested systems:

| Layer | What it does | Who provides it today |
|-------|-------------|----------------------|
| **Human Identity** | Establishes who the human owner is | Okta, Google Workspace, Azure AD, Auth0 — mature and ubiquitous |
| **Binding** | Provable link between a human and their agent | **Nobody — this is missing** |
| **Agent Runtime Identity** | How a system recognizes this specific agent | **Nobody — this is missing** |
| **Authorization** | Scoped, short-lived credentials at runtime | OAuth 2.0, OIDC, RFC 8693 — standards exist and work |

The critical insight is that the mistake every prior attempt has made is trying to build all four layers from scratch, or building them in the wrong order. We build only the two missing layers (Binding and Agent Runtime Identity) and delegate everything else to systems that already work.

### 2.2 Delegation, not impersonation

The most important architectural decision in World of Agents is how the agent authenticates to downstream systems:

**The agent does not get its own credentials. It gets the human's credentials, with attribution.**

When an agent needs to call a downstream system, World of Agents issues a JWT (JSON Web Token) that contains:

```json
{
  "iss": "worldofagents",
  "sub": "alice@company.com",
  "act": { "sub": "agent_abc123" },
  "similarity_score": 0.94,
  "exp": 1717003600
}
```

- `sub` (subject) = the human's identity (Alice)
- `act.sub` (actor subject) = the agent's identity

From the downstream system's perspective, **the principal is Alice**. All authorization, audit, and billing flow under Alice's existing identity. But the `act` claim provides full attribution of which agent actually wielded the token.

This is the RFC 8693 (OAuth 2.0 Token Exchange) delegation pattern. It means:

- No new principal is created in any IdP
- No fragmented audit log
- No new auth model for relying parties to learn
- The agent is invisible to systems that don't care about it, and fully attributed for systems that do

### 2.3 Behavioral signatures: the novel piece

The second missing layer — Agent Runtime Identity — is where our core intellectual property lies.

Every AI agent has a behavioral fingerprint. A coding agent calls `search`, `read_file`, `edit_file`, and `run_tests` in predictable patterns. A DevOps agent calls `deploy`, `health_check`, and `monitor`. A research agent calls `web_search` repeatedly, then `write_file`. These patterns are as distinctive as a human's keystroke dynamics.

Academic research confirms this is viable:

- **LLMmap (USENIX Security 2025):** 8 probing queries achieve >95% accuracy identifying 42 different LLM versions
- **GitHub Agent Fingerprinting (January 2026):** 41 features achieve 97.2% F1-score distinguishing Codex, Copilot, Devin, Cursor, and Claude Code
- **Stylometric Ensemble (2025):** 0.9988 precision with 0.0004 false-positive rate distinguishing Claude, Gemini, Llama, and OpenAI outputs

We compute a behavioral signature from an agent's trajectory (the sequence of tool calls, messages, and actions it takes) and store it at registration. At verification time, we compare the agent's current behavior against its stored signature.

**Critical honesty point:** Behavioral signatures are anomaly detection, not authentication. The cryptographic hardness is in the agent key and the IdP-issued token. The behavioral signature detects drift, impersonation, and model swaps — it does not prove identity. We will never claim otherwise.

---

## 3. WHAT WE BUILT

### 3.1 System architecture

World of Agents is a working MVP consisting of:

- **Backend API** — Python FastAPI service handling registration, verification, comparison, and JWT issuance
- **Behavioral Signature Engine** — Feature extraction and comparison system using an ensemble of statistical metrics
- **Database** — PostgreSQL with pgvector extension for behavioral embeddings
- **Frontend** — React application with a retro pixel-art aesthetic, real-time visualizations of signature analysis
- **Authentication** — Clerk for human identity, with custom RS256 JWT issuance for agent delegation tokens

The entire system runs in Docker Compose (4 containers: API, frontend, PostgreSQL, and email testing) and is deployable to Railway or any Docker-compatible hosting.

### 3.2 Registration flow

When a human registers an agent:

1. The human authenticates via Clerk (email, Google, GitHub, etc.)
2. They submit the agent's name, description, and a **sample trajectory** — a JSON array of the agent's recent actions:

```json
[
  {"type": "tool_call", "name": "search"},
  {"type": "tool_call", "name": "read_file"},
  {"type": "message", "name": "assistant", "content": "Here is the result."},
  {"type": "tool_call", "name": "edit_file"},
  {"type": "tool_call", "name": "run_tests"},
  {"type": "message", "name": "assistant", "content": "All tests pass."}
]
```

3. The system computes a **behavioral signature** from this trajectory (detailed in section 3.4)
4. A cryptographically random **agent key** is generated (base62-encoded, 48 bytes), hashed with bcrypt, and stored
5. The plain-text key is returned **exactly once** — it is never stored or retrievable again

The result is a triple stored in the database:
- `agent_id` (UUID) — the agent's unique identifier
- `key_hash` — bcrypt hash of the agent key (used for cryptographic authentication)
- `signature` — the behavioral profile (used for anomaly detection)

### 3.3 Verification flow

When an agent needs to prove its identity:

1. The agent (or its orchestrator) calls `POST /verify` with:
   - `agent_id` — which agent it claims to be
   - `agent_key` — the secret key issued at registration
   - `trajectory` — the agent's recent actions (current behavioral sample)

2. The system performs two checks:
   - **Cryptographic check:** Does the agent key match the stored bcrypt hash? (Strong — binary pass/fail)
   - **Behavioral check:** Does the current trajectory match the stored behavioral signature? (Probabilistic — returns a similarity score 0.0 to 1.0)

3. If both checks pass (key matches AND similarity score ≥ 0.7), the system:
   - Issues a signed RS256 JWT with `sub=human_identity` and `act.sub=agent_id`
   - Logs the verification attempt (agent_id, score, pass/fail, IP address)
   - Returns the JWT, similarity score, and detailed breakdown to the caller

4. The agent presents this JWT to downstream systems. Those systems can verify it using the World of Agents JWKS (JSON Web Key Set) endpoint at `/.well-known/jwks.json`.

### 3.4 The behavioral signature engine (core IP)

This is the most technically novel component. The engine extracts seven categories of features from any agent trajectory:

**Feature 1: Tool Call Histogram**
A normalized frequency distribution of which tools/actions the agent calls. For a coding agent, this might be `{search: 0.2, read_file: 0.3, edit_file: 0.2, run_tests: 0.15, message: 0.15}`. Two agents with similar tool distributions are likely the same type of agent.

**Feature 2: Bigram Transition Matrix**
A Markov model of sequential tool-call transitions. "After calling `search`, the agent calls `read_file` 60% of the time and `edit_file` 40% of the time." This captures the agent's behavioral flow, not just which tools it uses but the order in which it uses them.

**Feature 3: Trigram Transitions**
Same concept extended to three-step sequences. "After calling `search` then `read_file`, the agent calls `edit_file` 80% of the time." This captures more complex behavioral patterns.

**Feature 4: Response Length Statistics**
Statistical properties of the agent's message content: mean length, variance, and skewness. A verbose agent produces different statistics than a terse one.

**Feature 5: Vocabulary Statistics**
Token-level analysis of the agent's language: unique token count, total token count, type-token ratio (lexical diversity), and the 20 most frequent tokens. Different models and different system prompts produce measurably different vocabularies.

**Feature 6: Timing Statistics**
If timestamps are provided, inter-action intervals are analyzed: mean interval, standard deviation, and maximum interval. An agent that takes 2 seconds between actions has a different timing profile than one that takes 30 seconds.

**Feature 7: Structural Features**
High-level trajectory properties: total sequence length, number of unique action types, ratio of tool calls to messages, and ratio of error/retry actions. These capture the agent's overall behavioral shape.

#### Storage

Features are stored in two formats:
- **Structured JSONB** — the full feature dictionary, human-readable, debuggable, per-metric comparison possible
- **256-dimensional vector** (via pgvector) — a dense embedding for fast similarity queries. The vector encodes all seven feature categories into fixed positional ranges, L2-normalized.

#### Comparison Ensemble

When comparing two signatures, four metrics are computed and combined with learned weights:

| Metric | What it measures | Weight | Method |
|--------|-----------------|--------|--------|
| **Tool Distribution (JSD)** | Are the same tools used in similar proportions? | 25% | Jensen-Shannon divergence on histograms, converted to similarity |
| **Feature Vector (Cosine)** | How similar are the overall behavioral embeddings? | 30% | Cosine similarity on 256-dim vectors |
| **Sequence Pattern (Markov)** | Do the tools get called in the same order? | 25% | Per-state JSD on transition probability distributions |
| **Statistical Profile** | Does the agent communicate similarly? | 20% | Normalized difference in response length means and type-token ratios |

The weighted aggregate produces a single similarity score from 0.0 to 1.0:
- **≥ 0.7:** PASS — agent identity verified, JWT issued
- **0.4 – 0.7:** WARNING — some behavioral overlap, but significant divergence
- **≤ 0.4:** FAIL — behavioral profiles don't match, likely a different agent

#### Refinement

Agents evolve over time. The `/refine` endpoint accepts additional trajectory data and merges it into the stored signature using exponential weighted averaging (70% existing, 30% new). This prevents a single trajectory submission from overwriting the signature (security consideration) while allowing the profile to gradually adapt to legitimate behavioral changes.

### 3.5 API endpoints

The complete API surface:

**Authenticated endpoints (require Clerk session):**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/agents/register` | POST | Register a new agent with a behavioral sample |
| `/agents` | GET | List all agents owned by the authenticated human |
| `/agents/{id}` | GET | Get detailed agent information |
| `/agents/{id}` | DELETE | Revoke an agent (soft delete — sets status to "revoked") |
| `/agents/{id}/refine` | POST | Submit additional trajectory data to improve the signature |
| `/agents/{id}/rotate-key` | POST | Generate a new agent key, invalidating the old one |

**Open endpoints (no authentication required):**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/verify` | POST | Verify an agent's identity and get a signed JWT |
| `/compare` | POST | Compare two trajectories for behavioral similarity |
| `/agents/{id}/public` | GET | View an agent's public profile and verification statistics |
| `/.well-known/jwks.json` | GET | JWKS endpoint for JWT signature verification |
| `/health` | GET | System health check |
| `/health/db` | GET | Database connectivity check |

### 3.6 Data model

Three database tables in PostgreSQL:

**`humans`** — Clerk-synced user records
- `id` (UUID, primary key)
- `clerk_id` (unique, indexed — from Clerk webhook)
- `display_name`, `email`
- `created_at`

**`agents`** — Registered agent identities
- `id` (UUID, primary key)
- `human_id` (foreign key → humans)
- `name`, `description`
- `key_hash` (bcrypt), `key_salt`
- `signature` (JSONB — structured behavioral features)
- `signature_vector` (pgvector Vector(256) — dense embedding)
- `status` (active / revoked)
- `created_at`, `updated_at`

**`verification_log`** — Audit trail of all verification attempts
- `id` (UUID, primary key)
- `agent_id` (foreign key → agents)
- `similarity_score` (float)
- `passed` (boolean)
- `ip_address`
- `requested_at`

### 3.7 Security properties

| Threat | Defense | Strength |
|--------|---------|----------|
| Random attacker without the key | Agent key (bcrypt-hashed, 48-byte random) | **Cryptographic — strong** |
| Attacker who steals the key but doesn't know the agent's behavior | Behavioral signature mismatch | **Probabilistic — soft** |
| Agent silently swapped for a different model | Trajectory drift detection | **Probabilistic — operational** |
| Compromised human account | Revoke via Clerk deprovisioning → key revocation | **Cryptographic + operational — strong** |
| Key compromise detected | Key rotation endpoint (new key, old key invalidated immediately) | **Cryptographic — strong** |

### 3.8 Frontend application

The web application provides:

**Landing page (unauthenticated):**
- Project thesis and explanation with animated pixel-art visualizations
- Interactive 3D pixelated wireframe globe (Three.js rendered at 96x96, upscaled with nearest-neighbor)
- Sections covering the problem, the insight, how behavioral signatures work, and the delegation model
- Clerk sign-in modal styled to match the retro aesthetic

**Platform (authenticated):**
- Dashboard with agent count statistics, recent agents list, and quick action links
- Agent registry with registration form, agent table, key management, and revocation
- Verification tool with split-panel layout (form left, results right), animated score arcs, and metric breakdown bars
- Comparison tool with dual trajectory editors, robot-fight animation, and side-by-side analysis
- Pixel-flip page transition animation when signing in (blocks dissolve row-by-row left-to-right)

**Design system:**
- Warm dark palette: paper (#1c1916), coral (#d97757), cream (#f0eee6), peach (#e89b7d)
- Monospace typography: Space Mono for text, Silkscreen for headings
- Scanline overlay for retro CRT feel
- Pixelated canvas animations: globe, shield scanner, robot battle, floating astronaut, orbiting satellite
- No gradients, no shadows, no rounded corners — sharp, retro, functional

---

## 4. WHAT WE INTEGRATE (NOT BUILD)

A core design principle is integrating existing solutions rather than building from scratch:

| Concern | Solution | Why not build it |
|---------|----------|-----------------|
| Human authentication | **Clerk** (cloud) | Handles magic links, OAuth, MFA, session management, user profiles. 50K free MAU. |
| Password hashing for humans | **Clerk** | Clerk manages this entirely |
| Agent key hashing | **bcrypt** (standard library) | Industry-standard, well-studied |
| JWT signing | **PyJWT + cryptography** (RS256) | Standard libraries, no custom crypto |
| Database | **PostgreSQL + pgvector** | Mature, supports vector similarity natively |
| Vector embeddings | **pgvector** extension | No separate vector DB needed |
| Statistical computations | **scipy + numpy** | Industry-standard scientific computing |
| Frontend framework | **React + Vite + Tailwind CSS** | Fast development, excellent tooling |
| 3D rendering | **Three.js** | Pixelated globe with no custom WebGL |
| Container orchestration | **Docker Compose** | Standard, portable, reproducible |
| Database migrations | **Alembic** | Standard for SQLAlchemy projects |

What we actually invented:
1. The binding flow (how a human links an agent to their identity)
2. The behavioral signature extraction and comparison engine
3. The token-exchange broker (issuing delegated JWTs for agents)
4. The agent lifecycle model (register, verify, refine, rotate, revoke)

---

## 5. THE COMPETITIVE LANDSCAPE

### 5.1 Who else is working on this

The agent identity space is active but fragmented:

**Standards bodies (all drafts, nothing ratified):**
- IETF WIMSE (Workload Identity in Multi-System Environments) — the foundational standard
- IETF draft-klrc-aiagent-auth — 9-component Agent Identity Management System (from AWS, Zscaler, Ping Identity)
- NVIDIA's AIP (Agent Identity Protocol) — Ed25519 keypairs, Agent Authentication Tokens
- OpenID Connect for Agents (OIDC-A 1.0) — delegation chain validation
- NIST CAISI — AI Agent Interoperability Profile planned for Q4 2026

**Open-source projects:**
- **ZeroID (Highflame)** — closest competitor. Implements RFC 8693 token exchange, SDKs in Python/TS/Rust, PostgreSQL-based. Apache 2.0. Does NOT do behavioral verification.
- **AIP (Agent Identity Protocol)** — Ed25519 keys, auth tokens per tool call, MCP proxy. Reference implementations in Python/Go/Rust. Also an IETF draft.
- **Microsoft Agent Governance Toolkit** — 7-package system covering all 10 OWASP Agentic AI risks. MIT license.

**Platform approaches (vendor-locked):**
- **Microsoft Entra Agent ID** — most complete platform implementation, GA March 2026. Every agent gets an Entra identity. Microsoft-ecosystem-only.
- **Google Vertex AI** — agents get cryptographic IDs as IAM principals. Google-ecosystem-only.
- **Okta/Auth0 for AI Agents** — GA 2025-2026. Proprietary.

### 5.2 Our differentiation

| Capability | World of Agents | ZeroID | AIP | Entra Agent ID |
|------------|----------------|--------|-----|---------------|
| Behavioral verification | **Yes (core feature)** | No | No | No |
| Open source | Yes | Yes | Yes | No |
| Vendor-neutral | Yes | Yes | Yes | No (Microsoft) |
| Self-hosted | Yes | Yes | Yes | No |
| RFC 8693 delegation | Yes (own JWTs) | Yes | No | Partial |
| Human-agent binding | Yes | Yes | Partial | Yes |
| Signature refinement | Yes | No | No | No |
| Key rotation | Yes | No | Yes | Yes |

**No production system implements behavioral verification.** This is the unique contribution. The Otsuka et al. survey (April 2026, ~80 sources) identified "Agent Identity Integrity Gap" as a critical unsolved problem: agents can be cloned, impersonated, or puppeteered mid-session while credentials remain valid. Our behavioral signature addresses this directly.

---

## 6. TEST COVERAGE

The system has 116 automated tests across 9 test suites:

| Suite | Tests | Coverage |
|-------|-------|----------|
| Registration flows | 10 | Register with various trajectory types, validation, key security |
| Agent management | 9 | CRUD, cross-user isolation, revocation, refinement |
| Verification flows | 10 | Same/similar/different trajectories, key validation, audit logging |
| JWT token flows | 6 | Claim correctness, JWKS verification, unique JTI |
| Compare flows | 8 | Identical/similar/different, symmetry, no-auth access |
| Public profile | 5 | Profile data, verification stats, revoked state |
| Multi-user isolation | 2 | Three-user isolation, cross-user verification |
| Full lifecycle | 2 | 12-step lifecycle test, impersonation detection |
| System health | 2 | Health and DB connectivity |

Key test scenarios:
- **Impersonation detection:** Register a coding agent, verify with malicious behavior → score drops, verification fails
- **Key rotation security:** After rotation, old key returns 401, new key works
- **Multi-tenant isolation:** User A cannot see, modify, or delete User B's agents, but anyone can verify any agent
- **Signature symmetry:** Comparing A→B produces the same score as B→A
- **Full lifecycle:** Register → verify → refine → verify → rotate key → verify with old key (fails) → verify with new key → check audit log → revoke → verify (fails) → public profile (404) → owner still sees "revoked" status

Overall code coverage: **86%**

---

## 7. TECHNOLOGY STACK

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend API | FastAPI (Python) | 0.115+ |
| ORM | SQLAlchemy (async) | 2.0 |
| Database | PostgreSQL | 17 |
| Vector embeddings | pgvector | 0.8.0 |
| Migrations | Alembic | 1.14+ |
| Key hashing | bcrypt | 4.2+ |
| JWT signing | PyJWT + cryptography (RS256) | 2.10+ |
| Statistical analysis | scipy + numpy | 1.14+ / 2.0+ |
| Human auth | Clerk | React SDK |
| Frontend | React + TypeScript + Vite | 19 / 5.0 / 8.0 |
| Styling | Tailwind CSS | 4.0 |
| 3D rendering | Three.js | Latest |
| Containerization | Docker Compose | v2 |
| Production hosting | Railway-ready | - |

---

## 8. WHAT'S NEXT (ROADMAP)

### Next 90 days
- IP/CIDR posture checking (allowed IP ranges per agent)
- Per-action risk scoring
- World ID integration for proof-of-unique-personhood (sybil resistance)
- Agent versioning model and drift alerting

### 90–180 days
- OIDC login at registration (Okta, Google Workspace, Auth0 direct integration)
- OAuth 2.0 Token Exchange broker with external IdPs (ZITADEL integration for enterprise federation)
- Scope pre-authorization UX (agent can only request specific scopes)
- Verifier SDK libraries (TypeScript first, Python next) for downstream services
- Reference MCP server integration

### 180–365 days
- Lifecycle webhooks (deprovisioning, key rotation, transfer)
- Cross-org delegation pattern
- A2A (Agent-to-Agent) reference verifier
- Submission to IETF agent-identity working groups

---

## 9. THE ONE-SENTENCE PITCH

**World of Agents is the missing identity layer for AI agents — a free, open platform that lets any agent prove which human owns it and act on that human's behalf using delegated credentials, with full behavioral verification and attribution.**

We do not reinvent the identity wheel. We finish it.

---

## 10. APPENDIX: RUNNING THE PROJECT

### Local development

```bash
# Clone and start
git clone <repo-url>
cd worldofagents
cp .env.example .env
docker compose up --build -d

# Run migrations
docker compose exec api alembic upgrade head

# Seed demo data
docker compose exec api python scripts/seed.py

# Run tests
docker compose exec api pytest tests/ -v

# Access
# Frontend: http://localhost:5173
# API docs: http://localhost:8000/docs
# API health: http://localhost:8000/health
```

### Services

| Service | Port | Purpose |
|---------|------|---------|
| Frontend | 5173 | React application |
| API | 8000 | FastAPI backend |
| PostgreSQL | 5434 | Database (mapped from 5432) |
| Mailpit | 8025 | Email testing UI |

### Demo data

The seed script creates:
- 1 demo user (Demo User / demo@worldofagents.dev)
- 5 agents: code-assistant, devops-deployer, research-analyst, data-pipeline, security-scanner
- 4 active agents, 1 revoked (for demo purposes)
- 34 verification log entries with realistic scores
- Agent keys printed to console for testing `/verify`

### Production deployment (Railway)

1. Push to GitHub
2. Create Railway project, add PostgreSQL plugin
3. Deploy API from repo root (auto-detects Dockerfile)
4. Deploy frontend from `frontend/` directory using `Dockerfile.prod`
5. Set environment variables (Clerk keys, RSA keys, API URL)
6. Migrations run automatically on deploy via `railway.json`
