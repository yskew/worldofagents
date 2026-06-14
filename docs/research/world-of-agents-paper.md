# World of Agents: A Behavioral Identity and Continuous-Attestation Layer for AI Agents

**Draft preprint — prepared for submission (e.g., BlueHat Singapore and related venues).**

Authors: _Raghul V_ et al. (affiliation TBD)
Correspondence: TBD
Artifact: source, RFC design notes, and per-component test reports accompany this paper.

> Submission note: this is a working draft. All third-party citations in §11 are
> marked `[verify]` and MUST be bibliographically confirmed (venue, year, DOI)
> before submission. Quantitative results in §6 are on a **synthetic** dataset and
> are reported as such; a real-corpus evaluation is the primary future-work item.

---

## Abstract

AI agents increasingly act autonomously on behalf of humans, yet they authenticate
to downstream systems either with no identity or with a human's stolen
credentials, leaving relying parties unable to answer three foundational IAM
questions: which human is responsible, is this the same agent that was authorized,
and is it behaving normally now. We present **World of Agents**, an open,
standards-based identity layer that builds the two missing layers of agent
identity — *binding* (a provable human↔agent link) and *runtime identity*
(recognizing a specific agent by its behavior) — while delegating human
authentication and authorization to mature systems. Our core mechanism is a
**behavioral signature** computed from an agent's execution trajectory, combined
with a cryptographic agent key and an RFC 8693 delegated token so that the
probabilistic signal never stands alone. We extend point-in-time verification with
(i) **active challenge-response** verification that defeats trajectory replay,
(ii) **continuous mid-session attestation** via CUSUM change-point detection that
flags model swaps and hijacks, (iii) a **token-exchange broker** with OIDC
federation, (iv) a **Shared Signals / CAEP** transmitter that feeds behavioral
risk into existing identity providers, (v) an **MCP/A2A authorization server** that
gates tool calls on attestation, and (vi) **telemetry ingestion** (OpenTelemetry,
Langfuse, Braintrust) that enriches signatures from real runtime behavior. On a
deterministic synthetic benchmark we show that a hashed, confidence-aware
signature representation raises the discriminative power of the embedding
similarity from chance (ROC-AUC ≈ 0.50) to 0.73–0.88 and improves overall
same-vs-different separation across all trajectory subsets without regressing
full-length trajectories; active verification rejects 100% of replayed sessions;
and continuous attestation escalates to an alarm within a small number of
divergent windows while never alarming on consistent behavior. We are deliberately
explicit about what is cryptographic versus probabilistic, and about the synthetic
nature of the current evaluation.

---

## 1. Introduction

The number of AI agents operating in production — coding agents, DevOps agents,
research and data agents, customer-support agents — is growing rapidly, and they
increasingly call one another and external tools through protocols such as the
Model Context Protocol (MCP) and agent-to-agent (A2A) schemes. Each such agent
needs to authenticate, and today it does so in one of two unacceptable ways: with
**no identity**, relying on a trusted host's ambient permissions, or with a
**stolen identity**, namely a human's OAuth token or API key copied into the
agent's environment, which grants the agent full and indistinguishable access to
everything the human can do.

Consequently, a system receiving an agent's request cannot answer three questions
that underlie all identity and access management: (1) *which human is responsible*
for this action; (2) *is this the same agent* that was authorized, as opposed to a
swapped model, an altered system prompt, or a hijacked session; and (3) *is this
agent behaving normally*. Traditional service accounts do not fit: they are
static and long-lived, whereas agents are autonomous, probabilistic, and change
behavior with every prompt.

This paper makes the following contributions:

- **C1.** A four-layer framing of agent identity that isolates the two missing
  layers (binding and runtime identity) and an implementation that builds only
  those, delegating the rest to mature standards (§4).
- **C2.** A behavioral signature engine and an ensemble similarity metric, with two
  representation improvements — confidence-aware metric abstention and a hashed,
  bounded vector encoding — that we evaluate against a legacy baseline (§4.2, §6).
- **C3.** **Active challenge-response** verification that makes behavioral
  verification fresh and replay-resistant (§5.1).
- **C4.** **Continuous mid-session attestation** via CUSUM change-point detection,
  addressing the agent-identity-integrity gap *after* the initial check (§5.5).
- **C5.** An integration layer that places behavioral attestation in real
  authorization paths: an RFC 8693 token-exchange broker with OIDC federation, a
  Shared Signals/CAEP risk transmitter, an MCP/A2A authorization server, and
  OpenTelemetry/Langfuse/Braintrust telemetry ingestion (§5).
- **C6.** A reproducible synthetic evaluation, an explicit threat model, and an
  honest accounting of cryptographic versus probabilistic guarantees (§3, §6, §8).

## 2. Background and Related Work

**Agent / LLM fingerprinting.** A growing body of work shows that models and
agents exhibit identifiable behavioral and stylometric fingerprints. Active
probing of LLMs has been shown to identify model families and versions from a
small number of crafted queries [LLMmap, verify]. Output stylometry and tool-use
patterns have likewise been used to distinguish coding agents and model providers
[agent-fingerprinting, verify; stylometry, verify]. Our behavioral signature is in
this lineage but is applied to *identity verification and continuous attestation*
within an authorization flow, rather than to passive identification alone, and we
add active probing and sequential change detection.

**Agent identity standards and platforms.** Workload and agent identity is an
active standards area: OAuth 2.0 Token Exchange (RFC 8693) [verify] defines the
delegation pattern we use; the OpenID Shared Signals Framework and Continuous
Access Evaluation Profile (CAEP), with Security Event Tokens (RFC 8417) and
push/poll delivery (RFC 8935 / RFC 8936) and subject identifiers (RFC 9493)
[all verify], define how risk signals are transmitted to relying parties; and
IETF workload-identity efforts and several vendor and open-source agent-identity
projects are emerging [WIMSE; AIP; ZeroID; Entra Agent ID; Vertex; verify]. These
provide human identity, delegation, and signal transport, but to our knowledge
none performs *behavioral* verification or continuous behavioral attestation —
the gap this work targets.

**Observability and protocols.** We consume the OpenTelemetry GenAI semantic
conventions and the trace models of Langfuse and Braintrust [verify] for telemetry
ingestion, and the Model Context Protocol [verify] as the tool-calling substrate we
authorize.

**Techniques.** We use Jensen–Shannon divergence for distribution comparison, the
hashing trick / feature hashing [Weinberger et al., verify] for stable categorical
encoding, HNSW [Malkov & Yashunin, verify] for approximate nearest-neighbor search
via pgvector, Platt scaling [Platt, verify] for probability calibration, and the
CUSUM sequential change-point procedure [Page, verify] for drift detection.

## 3. Threat Model

**Assets.** The human principal's downstream access; the integrity of the
agent↔human binding; the trustworthiness of "this agent is behaving as
authorized."

**Adversaries and goals.**
- *A1 — outsider without the key:* attempts to impersonate a registered agent.
- *A2 — key thief:* obtains the agent key but not the agent's behavior.
- *A3 — model/prompt swap:* the agent is silently replaced by a different model or
  reconfigured after authorization.
- *A4 — mid-session hijack / prompt injection:* a legitimately-started session is
  taken over.
- *A5 — replay:* a previously-observed, valid trajectory is replayed to pass
  verification.

**Defenses and their strength (explicitly stated).**

| Threat | Defense | Strength |
|--------|---------|----------|
| A1 | Agent key (bcrypt, 48-byte random) | Cryptographic — strong |
| A2 | Behavioral signature mismatch | Probabilistic — soft |
| A3 | Trajectory drift detection (passive + continuous) | Probabilistic — operational |
| A4 | Continuous mid-session attestation (CUSUM) | Probabilistic — operational |
| A5 | Active challenge: fresh, single-use, server-chosen probes | Cryptographic freshness on the challenge; soft on the behavior |
| Key compromise detected | Key rotation; revocation → CAEP session-revoked | Cryptographic + operational |

**Out of scope.** A fully cryptographic runtime root (e.g., TEE attestation of
model weights and prompt) is future work (§10); we are explicit that behavioral
signals are anomaly detection, not authentication.

## 4. System Design

### 4.1 Four-layer model

Agent identity decomposes into human identity, **binding**, **agent runtime
identity**, and authorization. Human identity (Clerk/OIDC) and authorization
(OAuth 2.0 / RFC 8693) are mature; we build binding and runtime identity and
delegate the rest. A verification produces an RS256 JSON Web Token with `sub` =
the human and `act.sub` = the agent (the RFC 8693 delegation pattern), so the
agent wields the human's identity *with attribution* rather than as a new
principal.

### 4.2 Behavioral signature engine

From an agent trajectory — an ordered list of steps, each a tool call, message, or
action with optional content, timestamp, and error metadata — we extract seven
feature families: a tool-call histogram, bigram and trigram tool-transition
matrices, response-length statistics, vocabulary statistics, inter-action timing
statistics, and structural features (length, unique action types, tool-call ratio,
error/retry ratio). Features are stored as structured JSON and as a 256-dimension
vector (pgvector). Verification compares a stored signature against a fresh sample
using a weighted ensemble of four metrics: tool-distribution similarity
(Jensen–Shannon divergence, 25%), embedding cosine similarity (30%), sequence
similarity (per-state JSD over transition matrices, 25%), and a statistical
profile (20%), producing a score in [0,1] with pass/warning/fail thresholds.

We introduce two representation improvements over the original engine, each
flag-gated for safe rollout:

- **Confidence-aware scoring (RFC 0001).** Metrics that cannot be computed for a
  given trajectory (e.g., sequence or statistics for a very short or content-free
  trajectory) previously voted a neutral 0.5, biasing ~45% of the score toward
  the midpoint. They now **abstain**, and their weight is redistributed over the
  metrics that did produce a value.
- **Hashed vector encoding (RFC 0002).** The legacy encoding placed histogram
  values by sorted magnitude, so two agents with the same distribution *shape* but
  *different tools* collided in vector space — the cosine metric compared shape,
  not tool identity. We instead place each tool/transition by a stable BLAKE2b
  hash (feature hashing with signed buckets) so the same tool maps to the same
  dimension for every agent, replace magic-number normalization with bounded
  transforms, and use the full dimensionality. The encoding is process-independent
  (no salted hashing), which matters because vectors are persisted.

### 4.3 Architecture

A FastAPI service backed by PostgreSQL + pgvector; human auth via Clerk (or any
OIDC provider at the broker); RS256 signing for delegated tokens, JWKS for
downstream verification, and Security Event Tokens for risk signals; a React
frontend. The signature `vector` is a derived cache of the encoding-independent
JSON signature, which lets us recompute vectors on demand and keep verification
correct across encoding changes.

## 5. Implementation of the Identity & Attestation Layer

### 5.1 Active challenge-response verification (RFC 0008)

Passive verification accepts any submitted trajectory and is therefore vulnerable
to replay (A5). In active verification the *verifier* issues a fresh, HMAC-signed,
single-use challenge token binding a server-chosen, nonce-seeded subset of probes;
the agent must respond to *those* probes live, and responses are scored against a
stored per-probe profile. The nonce defeats replay; the server-chosen selection
defeats pre-computation; a behaviorally divergent impostor fails the score even
with a valid key.

### 5.2 Token-exchange broker + OIDC federation (RFC 0009)

An RFC 8693 endpoint exchanges a human IdP token (`subject_token`, validated via a
pluggable provider registry — Clerk by default, plus Okta/Entra/Auth0/Google) and
an agent attestation token (`actor_token`, our verification JWT) for a **scoped,
audience-bound, short-lived** delegated token. Behavioral verification thereby
gates real downstream authorization, with per-agent allowed scopes enforcing least
privilege and ownership checked across subject and actor.

### 5.3 Shared Signals / CAEP transmitter (RFC 0011)

The service is a standards-compliant SSF/CAEP transmitter: a failed behavioral
check emits a (namespaced) behavioral-anomaly Security Event Token, and revocation
emits a standard CAEP session-revoked event; SETs are delivered by poll (RFC 8936)
and optional push (RFC 8935), with RFC 9493 subjects, verifiable against the
service JWKS. This positions the system as the *agent-behavior signal source* that
existing identity providers subscribe to for continuous access evaluation.

### 5.4 MCP / A2A authorization server (RFC 0012)

A reference authorization layer for the tool-calling greenfield: a tool call must
present a valid attestation token (verified against the JWKS) and the requested
tool must be in the agent's allowlist; otherwise it is denied. The decision
function is what a production MCP server/proxy calls before dispatch.

### 5.5 Continuous mid-session attestation (RFC 0013)

To address A3/A4 *after* the initial check, a session is anchored to the agent's
baseline signature and each incoming behavioral window is scored against it. A
one-sided CUSUM accumulates `max(0, S + (ref − similarity))`; normal variation
(similarity above the reference) does not accumulate, while sustained divergence
escalates ok→warning→alarm and self-heals on recovery. The alarm status is the
natural live input to the CAEP transmitter (§5.3).

### 5.6 Telemetry ingestion (RFC 0010)

To collect real behavior (and ultimately a real corpus), the service ingests agent
traces in OpenTelemetry GenAI, Langfuse, and Braintrust formats, maps spans to
trajectory steps (preserving timing and error status), and enriches the agent's
signature. We map to trajectories and reuse the engine rather than building a
tracing product; raw spans are not persisted, only derived features.

## 6. Evaluation

### 6.1 Methodology

We built a deterministic, seeded synthetic benchmark. It defines several agent
*profiles* (coder, devops, researcher, data, security), each a tool distribution
plus a small content vocabulary, and a pair of profiles with identical histogram
*shape* but disjoint tools to probe the shape-collision failure mode. Same-agent
pairs draw two samples from one profile; different-agent pairs draw from two
profiles. We report on four subsets — `full` (with content), `tool_only` (no
messages), `short` (length 3–5), and `shape_collision` — and on each we compute
ROC-AUC and Equal Error Rate (EER) of same-vs-different discrimination, the mean
score separation, and the ROC-AUC of the cosine sub-score specifically. Sample
sizes: 330 same / 500 different per subset (132 / 144 for shape_collision). All
metrics are implemented in NumPy; the harness is reproducible
(`scripts/eval_signature.py`).

We evaluate four configurations: **V1** (legacy scoring + legacy vector), and the
combination of the two representation improvements (**V1+V2**, i.e., confidence-aware
scoring + hashed encoding).

### 6.2 Results: discrimination

| Subset | Config | ROC-AUC | EER | Separation | Cosine AUC |
|--------|--------|--------:|----:|-----------:|-----------:|
| full | V1 | 0.9751 | 0.0673 | 0.1836 | 0.508 |
| full | **V1+V2** | **0.9943** | **0.0337** | **0.2283** | **0.8156** |
| tool_only | V1 | 0.9991 | 0.0095 | 0.2041 | 0.5103 |
| tool_only | **V1+V2** | **0.9999** | **0.0085** | **0.3107** | **0.819** |
| short | V1 | 0.9143 | 0.1683 | 0.1086 | 0.4977 |
| short | **V1+V2** | **0.9572** | **0.0879** | **0.1661** | **0.7303** |
| shape_collision | V1 | 0.9999 | 0.0073 | 0.2360 | 0.4987 |
| shape_collision | **V1+V2** | **1.0000** | **0.0000** | **0.3789** | **0.8838** |

The headline result is the **cosine sub-score**: under the legacy encoding its
ROC-AUC is ≈ 0.50 (chance) on every subset — the embedding was effectively not
discriminating, being fooled by distribution shape — and the hashed encoding
raises it to 0.73–0.88. Overall ROC-AUC and separation improve on every subset,
most visibly on `short` (0.914 → 0.957) and on the shape-collision case
(separation 0.236 → 0.379, EER → 0). Two targeted micro-benchmarks corroborate
this: on a disjoint-tools/same-shape pair the cosine similarity drops from 0.888
(false positive) to 0.282, and on the tool-only subset the same-vs-different
*separation* rises from 0.3225 to 0.4032 (+25%) while full-length trajectories are
byte-identical to the legacy path (no regression).

### 6.3 Results: replay resistance and attestation

Active challenge-response (§5.1) rejects 100% of replayed valid sessions (the
single-use nonce is consumed on first use), rejects tampered and wrong-agent
challenge tokens, and fails behaviorally-divergent impostors that hold a valid key
(observed active score ≈ 0.31 vs 1.0 for a genuine response). Continuous
attestation (§5.5) holds at `ok` (CUSUM = 0) across consistent windows and
escalates ok→warning→alarm under sustained divergence (per-window similarity ≈
0.34, accumulating ≈ 0.16/window; alarm by ≈ 4 windows at the default thresholds),
and self-heals when behavior returns to baseline.

### 6.4 Results: calibration and learned weights

Platt scaling of the raw ensemble score improves the Brier score from 0.242 (raw
score used as a probability) to 0.092, and maps the operational 0.7 threshold to
a calibrated probability of ≈ 0.9997. Separately, fitting the ensemble weights by
L2-regularized logistic regression on the synthetic set yields weights that
heavily favor tool-distribution and sequence and nearly zero out the cosine and
statistics terms for only a 0.999→1.000 AUC change on a saturated subset — a
textbook overfit to the generator. We therefore **ship both calibration and
learned weights but disable them by default**, pending a real corpus. We consider
reporting this negative result, rather than enabling the features, a contribution
to honest evaluation practice.

### 6.5 Software validation

The implementation is covered by an automated suite (backend pytest across all
components and a frontend Vitest suite), with every behavioral change validated in
both the legacy and improved regimes to confirm backward compatibility, plus
live end-to-end exercises of each capability against a running stack. Per-component
test reports accompany the artifact.

## 7. Discussion

The evaluation supports three claims. First, **representation matters more than the
ensemble weights**: simply encoding tool identity stably (rather than by magnitude)
converts a chance-level embedding into a useful one, which is why we adopt V2 by
default but not learned weights. Second, **freshness is the lever for behavioral
security**: a passive behavioral check is replayable, whereas a server-chosen,
single-use challenge is not, at no model-quality cost. Third, **continuous beats
point-in-time**: the integrity gap lives after authorization, and a lightweight
sequential test catches sustained drift while ignoring benign variation. Placing
these signals into standards-based authorization paths (RFC 8693 broker, CAEP
emitter, MCP gate) is what turns a similarity score into an enforceable control.

## 8. Limitations

1. **Synthetic evaluation.** All quantitative results in §6 are on a generator that
   models distributional, sequential, and shape differences but not real-model
   idiosyncrasies; absolute AUCs are near-saturated and should be read as relative
   V1-vs-V2 deltas. A real, multi-model, multi-framework corpus is required before
   the numbers can be claimed as production performance.
2. **Probabilistic behavioral layer.** Behavioral signatures are anomaly detection,
   not authentication; an adversary who accurately mimics a target's behavior and
   holds the key can pass the behavioral check. We mitigate with active probing and
   continuous attestation but do not claim cryptographic identity from behavior.
3. **No cryptographic runtime root yet.** We do not currently attest model weights
   or system prompt via a TEE; this is the principal future-work item.
4. **Single-instance state.** Rate-limiter, challenge nonces, SSF queue, and
   attestation sessions are in-memory; horizontal scale requires a shared store.
5. **Threshold and weight tuning** are hand-set or fit on synthetic data.
6. **Telemetry-derived enrichment** assumes well-formed traces and trusts the
   agent-key-authenticated submitter.

## 9. Ethics and Responsible Disclosure

The system is defensive: it improves attribution and anomaly detection for agent
actions. Trajectories can be sensitive; we persist only derived features, not raw
spans, and provide for redaction/metadata-only modes, with zero-knowledge
verification as future work. Behavioral fingerprinting raises privacy
considerations (it can identify *which* model/agent acted); deployments should
disclose monitoring to operators. No third-party systems were attacked; all
evaluation is on self-generated data. Dual-use is limited: the techniques detect
impersonation rather than enable it.

## 10. Future Work

A real-trajectory benchmark and public leaderboard; learned contrastive trajectory
embeddings; a cryptographic runtime root via TEE/remote attestation binding model
and prompt hashes; decentralized verification (verifiable credentials / DIDs) and
zero-knowledge proofs of signature match; full MCP transport and A2A handshake;
the full SSF stream lifecycle; adaptive per-agent thresholds learned from
telemetry; and submission of the behavioral-attestation profile to the relevant
IETF/OpenID working groups.

## 11. References

> All entries below require bibliographic verification (venue, year, DOI/URL)
> before submission; several describe rapidly-evolving standards and 2024–2026
> industry efforts.

1. OAuth 2.0 Token Exchange. RFC 8693. [verify]
2. Security Event Token (SET). RFC 8417. [verify]
3. Push-Based Security Event Token Delivery. RFC 8935. [verify]
4. Poll-Based Security Event Token Delivery. RFC 8936. [verify]
5. Subject Identifiers for Security Event Tokens. RFC 9493. [verify]
6. OpenID Shared Signals Framework and CAEP. OpenID Foundation. [verify]
7. JSON Web Token (JWT). RFC 7519. [verify]
8. OpenTelemetry GenAI semantic conventions. [verify]
9. Model Context Protocol (MCP). Anthropic. [verify]
10. LLMmap: fingerprinting large language models. [verify — venue/year]
11. Agent / coding-assistant fingerprinting via tool-use features. [verify]
12. Stylometric attribution of LLM outputs. [verify]
13. K. Weinberger et al. Feature hashing for large-scale multitask learning. [verify]
14. Yu. Malkov, D. Yashunin. HNSW approximate nearest neighbor search. [verify]
15. J. Platt. Probabilistic outputs for SVMs (Platt scaling). [verify]
16. E. S. Page. Continuous inspection schemes (CUSUM). [verify]
17. IETF WIMSE (Workload Identity in Multi-System Environments). [verify]
18. Microsoft Entra Agent ID; Google Vertex AI agent identity; ZeroID; NVIDIA AIP;
    Cloud Security Alliance Agentic AI IAM; NIST agent-identity initiative. [verify]

## Appendix A. Reproducibility

- Synthetic eval: `docker compose exec api python scripts/eval_signature.py`
  (deterministic seed; emits the §6.2 table).
- Weight fit / calibration fit: `scripts/fit_weights.py`, `scripts/fit_calibration.py`.
- Feature flags: `SCORE_NORMALIZATION_V2`, `VECTOR_ENCODING_V2` (default on);
  `USE_LEARNED_WEIGHTS`, `SCORE_CALIBRATION` (default off). Setting both V2 flags
  off restores the exact legacy behavior used as the V1 baseline.
- Per-component design notes and test reports: `docs/rfcs/`, `docs/reports/`.
