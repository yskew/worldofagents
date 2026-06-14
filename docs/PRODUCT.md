# World of Agents: Product Document

*Version 0.2 · status: research MVP with extended integration layer*

---

## 1. One-liner

**The missing identity layer for AI agents**, an open platform that lets any
agent prove which human owns it, continuously verify its behavioral identity, and
act on its owner's behalf with scoped, attributable, short-lived credentials.

## 2. The problem

AI agents act in the world on behalf of humans, they write code, deploy
infrastructure, query data, send messages, and call other agents and tools. Every
one of them authenticates today in one of two unacceptable ways:

1. **No identity**, runs in a trusted environment with inherited permissions.
2. **Stolen identity**, a human's OAuth token / API key pasted into the agent's
   environment, giving it full, *indistinguishable* access.

So no downstream system can answer three questions that underlie all of IAM:

1. **Which human is responsible** for this action?
2. **Is this the same agent** that was authorized (not a swapped model / changed
   prompt / hijacked session)?
3. **Is this agent behaving normally** right now?

Service accounts don't fit: they are static and long-lived, whereas agents are
autonomous, probabilistic, and change behavior every prompt. The pressure is
acute and growing, agent-to-agent protocols (MCP, A2A) are proliferating, and a
widely-cited observation is that essentially all surveyed MCP servers ship with
no authentication at all.

## 3. The insight: build the two missing layers, integrate the rest

Agent identity has four layers; two are solved and two are missing:

| Layer | Provided by | We |
|-------|-------------|----|
| Human identity | Okta, Entra, Auth0, Google, Clerk | **integrate** |
| **Binding** (human ↔ agent) | nobody | **build** |
| **Agent runtime identity** (recognize *this* agent) | nobody | **build** |
| Authorization (scoped, short-lived creds) | OAuth 2.0 / OIDC / RFC 8693 | **integrate** |

We build Binding and Runtime Identity, and we *finish* the wheel by delegating
human auth and authorization to mature systems. Runtime identity is the novel
part: a **behavioral signature** computed from an agent's trajectory (its tool
calls, messages, timing, errors), used for verification and continuous
anomaly detection, combined with a cryptographic agent key so the soft signal
never stands alone.

## 4. Target users & personas

| Persona | Need | Primary surfaces |
|---------|------|------------------|
| **Platform / IAM engineer** (enterprise) | Govern internal agents; least-privilege downstream access; audit "which human, which agent" | Broker (RFC 8693), CAEP signals into existing IdP |
| **Agent developer** | Register an agent, get a credential, prove identity to downstream services | Register / Verify / Active challenge / SDK |
| **MCP / tool-server operator** | Stop unauthenticated agents from calling tools | MCP authorization server |
| **Security / SOC analyst** | Detect mid-session hijack, model swap, anomalous behavior | Continuous attestation + Signals feed |
| **Compliance / risk** | Attribution + audit trail for agent actions | Verification log, public profiles, CAEP events |

## 5. What the product does (capabilities)

1. **Register & bind** an agent to a human; issue a one-time bcrypt-hashed agent key.
2. **Verify** identity two ways:
   - *Passive*, submit a trajectory; cryptographic key check + behavioral
     similarity → delegated RS256 JWT (`sub`=human, `act.sub`=agent).
   - *Active (challenge-response)*, the verifier issues fresh, single-use,
     server-chosen probes the agent must answer live; defeats trajectory replay.
3. **Authorize downstream** via an RFC 8693 token-exchange broker: human IdP token
   + agent attestation → scoped, audience-bound, short-lived delegated token a
   relying party accepts. Federates Okta / Entra / Auth0 / Google alongside Clerk.
4. **Gate tool calls** with a reference MCP / A2A authorization server: a tool call
   requires a valid attestation token + per-agent tool allowlist.
5. **Attest continuously**: CUSUM drift detection over a live behavioral stream
   raises `warning` / `alarm` on model swap, injection, or hijack mid-session.
6. **Emit risk signals**: Shared Signals / CAEP transmitter emits signed Security
   Event Tokens (behavioral-anomaly, session-revoked) that IdPs consume in their
   continuous access evaluation.
7. **Ingest telemetry**: OpenTelemetry GenAI / Langfuse / Braintrust traces enrich
   signatures from real runtime behavior (the data flywheel).
8. **Find similar agents**: pgvector ANN search + ensemble re-rank.

## 6. Differentiation

| Capability | World of Agents | ZeroID | NVIDIA AIP | Entra Agent ID |
|------------|:---:|:---:|:---:|:---:|
| Behavioral verification | **✅ core** | ❌ | ❌ | ❌ |
| Active challenge-response | **✅** | ❌ | ❌ | ❌ |
| Continuous mid-session attestation | **✅** | ❌ | ❌ | ❌ |
| CAEP risk emission to IdPs | **✅** | ❌ | ❌ | partial |
| MCP/A2A tool-call gating | **✅** | ❌ | partial | ❌ |
| RFC 8693 delegation | ✅ | ✅ | ❌ | partial |
| Open-source, vendor-neutral, self-hosted | ✅ | ✅ | ✅ | ❌ |

**The defensible position:** don't become another IdP login button, become the
**agent-behavior risk signal** the existing IdP stack subscribes to, and the
**authorization layer** for the MCP/A2A greenfield. No production system today
does behavioral verification; that is the wedge.

## 7. Product principles

- **Delegation, not impersonation**, the agent wields the human's identity *with
  attribution*, never a new principal.
- **Honest about strength**, cryptographic factors (key, signed tokens) are hard;
  behavioral signals are anomaly detection. We never conflate the two.
- **Integrate, don't reinvent**, Clerk/OIDC for humans, OAuth/RFC 8693 for authz,
  OpenTelemetry/Langfuse/Braintrust for telemetry, pgvector for search.
- **Standards-first**, RFC 8693, RFC 8417/8935/8936 (SETs), OpenID CAEP/SSF,
  OpenTelemetry GenAI, MCP.
- **Ship behind flags; flip on evidence**, every behavioral change is gated and
  validated before becoming default.

## 8. Success metrics

- **Discrimination quality:** ROC-AUC / EER separating same-agent vs different-agent
  (and the harder short / shape-collision / tool-only subsets).
- **Replay resistance:** % of recorded-trajectory replays rejected (target 100% for
  active verification).
- **Mean windows-to-alarm** for a hijacked session (lower is better).
- **Adoption:** registered agents; downstream tokens minted; CAEP receivers
  subscribed; MCP tool calls gated; telemetry traces ingested.
- **Integrity:** false-accept rate on impostors; false-reject rate on legitimate
  drift (must stay low to be trustworthy).

## 9. Roadmap

- **Now (shipped):** behavioral engine v2, active verification, broker + OIDC,
  telemetry ingestion, CAEP emitter, MCP auth server, continuous attestation.
- **Next:** merge the stack; flip learned weights + calibration once the telemetry
  corpus exists; wire attestation→CAEP; Redis-backed state; verifier SDKs.
- **Later:** real benchmark + leaderboard; learned contrastive embeddings;
  cryptographic TEE/manifest root; decentralized + ZK verification; IETF/OpenID
  standards submission.

## 10. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| Behavioral signal is probabilistic / spoofable | Pair with cryptographic key + active challenge + continuous attestation; never the sole gate |
| Mimicry by an attacker who knows the target's behavior | Active, server-chosen probes; adversarial evaluation; future learned encoders |
| Synthetic-data overfitting (weights, calibration) | Keep off by default until validated on a real corpus (telemetry) |
| Privacy of trajectories | Persist only derived features, not raw spans; metadata-only / redaction modes; future ZK |
| Vendor lock-in perception | Open-source, standards-based, self-hostable; integrate rather than replace |
| Multi-instance correctness | Move in-memory stores to a shared store before horizontal scale |

## 11. Status & honest caveats

This is a research MVP. The behavioral engine, active verification, broker,
telemetry, CAEP, MCP, and continuous attestation are implemented and tested
(automated + live). Current quantitative evaluation is on a **synthetic** dataset
(see the research paper); learned weights and calibration are therefore disabled
by default. Several stores are in-memory (single-instance). These are explicitly
tracked in `FEATURES.md` and the per-RFC documents.
