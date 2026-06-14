# World of Agents: A Behavioral Identity and Continuous Attestation Layer for AI Agents

Raghul V

Affiliation (to be completed)

**Author Note**

Correspondence concerning this article should be addressed to the first author
(contact to be completed). A reproducible software artifact accompanies this work,
including the signature engine, the evaluation harness, per-component design notes,
and automated test reports. The quantitative results reported here were obtained on
a synthetic benchmark; this scope is stated explicitly throughout the paper, and a
real corpus evaluation is identified as the primary direction for future work.

---

## Abstract

AI agents increasingly act on behalf of people, yet they authenticate to downstream
systems either with no identity or with a human operator's borrowed credentials.
Relying parties are therefore unable to answer three questions that underpin
identity and access management: which person is accountable for an action, whether
the acting agent is the one that was authorized, and whether that agent is behaving
normally. This paper presents World of Agents, an open and standards-based identity
layer that supplies the two capabilities the ecosystem currently lacks, a provable
human to agent binding and a runtime identity that recognizes a specific agent from
its behavior, while delegating human authentication and authorization to
established systems. The central mechanism is a behavioral signature computed from
an agent's execution trajectory. It is paired with a cryptographic agent key and an
OAuth 2.0 Token Exchange token (Jones et al., 2020) so that the probabilistic signal
never operates alone. Point in time verification is extended in five ways: active
challenge response verification that resists trajectory replay; continuous mid
session attestation using a cumulative sum change detector; a token exchange broker
with OpenID Connect federation; a Shared Signals transmitter (Tulshibagwale et al.,
2025) that feeds behavioral risk into existing identity providers; and an
authorization server for the Model Context Protocol (Anthropic, 2024) that gates
tool calls on attestation. On a deterministic synthetic benchmark, a hashed and
confidence aware signature representation raises the discriminative power of the
embedding similarity from chance (area under the receiver operating characteristic
curve, AUC, of approximately 0.50) to a range of 0.73 to 0.88, and it improves
overall separation between same agent and different agent comparisons across every
trajectory subset without degrading full length trajectories. Active verification
rejects replayed sessions completely, and continuous attestation raises an alarm
within a small number of divergent windows while leaving consistent behavior
untouched. We are deliberate about distinguishing cryptographic guarantees from
probabilistic ones, and about the synthetic nature of the present evaluation.

*Keywords*: agent identity, behavioral fingerprinting, continuous access
evaluation, token exchange, anomaly detection, AI security

---

## Introduction

The population of AI agents in production has grown quickly. Coding assistants,
deployment agents, research and data pipelines, and customer facing assistants now
operate continuously, and they increasingly invoke one another and external tools
through protocols such as the Model Context Protocol (Anthropic, 2024). Every one of
these agents must authenticate, and today it usually does so in one of two
unsatisfactory ways. In the first, the agent presents no identity at all and relies
on the ambient permissions of a trusted host. In the second, a human operator's
OAuth token or API key is copied into the agent's environment, which grants the
agent access that is indistinguishable from the human's own.

Both patterns leave a receiving system unable to answer questions that are routine
for human identity. It cannot determine which person is accountable for a given
action. It cannot tell whether the agent making a request is the same one that was
authorized, as opposed to a swapped model, an edited system prompt, or a session
that has been taken over. It cannot assess whether the agent's current behavior is
consistent with its past behavior. Conventional service accounts do not close this
gap, because they are static and long lived, whereas agents are autonomous and
their behavior shifts with each prompt.

This paper makes the following contributions.

First, it offers a four layer account of agent identity that isolates the two layers
the ecosystem lacks, binding and runtime identity, and an implementation that builds
only those two and delegates the remainder to mature standards.

Second, it describes a behavioral signature engine and an ensemble similarity
metric, together with two representation changes, confidence aware metric
abstention and a hashed and bounded vector encoding, that we evaluate against a
legacy baseline.

Third, it introduces active challenge response verification, which makes behavioral
verification fresh and resistant to replay.

Fourth, it introduces continuous mid session attestation based on a cumulative sum
change detector (Page, 1954), which addresses the integrity gap that exists after
the initial check.

Fifth, it presents an integration layer that places behavioral attestation inside
real authorization paths: a token exchange broker with OpenID Connect federation, a
Shared Signals and Continuous Access Evaluation transmitter, an authorization server
for the Model Context Protocol, and telemetry ingestion from common observability
formats.

Sixth, it reports a reproducible synthetic evaluation, states an explicit threat
model, and gives an honest account of which guarantees are cryptographic and which
are probabilistic.

## Background and Related Work

### Behavioral and Stylometric Fingerprinting

A growing literature shows that language models and the agents built on them carry
identifiable fingerprints. Pasquini et al. (2024) demonstrated that a small set of
crafted probe queries can identify a model's family and version with high accuracy,
an approach they call active fingerprinting. Behavioral identity in our system draws
on the same intuition, namely that an agent's tool use, sequencing, verbosity, and
timing form a distinctive pattern. The difference in emphasis is that we use the
signature for verification and continuous attestation inside an authorization flow,
rather than for passive identification alone, and we add server chosen probing and
sequential change detection on top of it.

### Standards for Delegation and Risk Signaling

The delegation pattern at the center of our design is OAuth 2.0 Token Exchange
(Jones et al., 2020), which lets one party act with attribution on behalf of
another. We issue JSON Web Tokens (Jones et al., 2015) and publish a key set so that
relying parties can verify them. For risk signaling we implement the OpenID Shared
Signals Framework (Tulshibagwale et al., 2025) and the Continuous Access Evaluation
Profile (Cappalli & Tulshibagwale, 2025). These rely on the Security Event Token
(Hunt et al., 2018), on push and poll delivery (Backman et al., 2020b, 2020a), and
on standard subject identifiers (Backman et al., 2023). To our knowledge, the
standards ecosystem supplies human identity, delegation, and a transport for risk
signals, but it does not specify how the behavioral risk signal itself is produced.
That is the gap this work addresses.

### Commercial and Platform Approaches

Vendor platforms have begun to assign identities to agents. Microsoft (2025)
announced Entra Agent ID, which gives each agent a directory identity, and Google
(n.d.) documents an agent identity model for its agent platform. These approaches
provide directory presence and lifecycle management within their respective
ecosystems. They do not perform behavioral verification or continuous behavioral
attestation, and they are tied to a single vendor. Our system is open, vendor
neutral, and self hostable, and it treats behavioral attestation as a first class
control.

### Techniques

Several established techniques underpin the implementation. We compare
distributions with the Jensen Shannon divergence (Lin, 1991). We encode categorical
features into fixed positions with feature hashing (Weinberger et al., 2009), which
gives a stable mapping from tool name to vector dimension. We perform approximate
nearest neighbor search over the pgvector column using hierarchical navigable small
world graphs (Malkov & Yashunin, 2020). We calibrate scores into probabilities with
Platt scaling (Platt, 1999). We detect drift with the cumulative sum procedure
(Page, 1954). Agent keys are hashed with bcrypt (Provos & Mazières, 1999). For
telemetry we consume the OpenTelemetry semantic conventions for generative AI
systems (OpenTelemetry Authors, n.d.) alongside two widely used trace formats.

## Threat Model

The assets we protect are the human principal's downstream access, the integrity of
the binding between a human and an agent, and the trustworthiness of the claim that
an agent is behaving as authorized.

We consider five adversaries. The first is an outsider who lacks the agent key and
attempts to impersonate a registered agent. The second is a thief who has obtained
the agent key but does not know how the agent behaves. The third replaces the agent
with a different model or reconfigures its prompt after authorization. The fourth
hijacks a session that began legitimately, for example through prompt injection. The
fifth replays a previously observed and valid trajectory in order to pass
verification.

The following table states each defense and, importantly, how strong it is. We do
not claim cryptographic strength where the mechanism is probabilistic.

| Threat | Defense | Strength |
|--------|---------|----------|
| Outsider without the key | Agent key, bcrypt hashed, 48 random bytes | Cryptographic, strong |
| Key thief | Behavioral signature mismatch | Probabilistic, soft |
| Model or prompt swap | Trajectory drift detection, passive and continuous | Probabilistic, operational |
| Mid session hijack | Continuous attestation with a cumulative sum detector | Probabilistic, operational |
| Replay | Active challenge with a fresh, single use, server chosen probe set | Cryptographic freshness on the challenge, soft on the behavior |
| Detected key compromise | Key rotation, revocation, and a session revoked risk event | Cryptographic and operational |

A fully cryptographic runtime root, such as remote attestation of model weights and
prompt inside a trusted execution environment, is out of scope for this paper and is
discussed under future work. We treat behavioral signals as anomaly detection rather
than as authentication.

## System Design

### The Four Layer Model

Agent identity separates into human identity, binding, runtime identity, and
authorization. Human identity and authorization are well served by existing
systems, so we build only binding and runtime identity and delegate the rest. A
successful verification produces a signed token in which the subject claim names the
human and the actor claim names the agent, following the token exchange pattern
(Jones et al., 2020). The agent therefore wields the human's identity with explicit
attribution rather than as a newly created principal.

### Behavioral Signature Engine

A trajectory is an ordered list of steps. Each step is a tool call, a message, or an
action, and it may carry content, a timestamp, and error metadata. From a trajectory
we extract seven families of features: a normalized tool call histogram, bigram and
trigram transition matrices over tool calls, response length statistics, vocabulary
statistics, inter action timing statistics, and structural features such as length,
the number of distinct action types, the ratio of tool calls to messages, and the
ratio of error or retry steps. We persist the signature both as structured data and
as a 256 dimension vector.

Verification compares a stored signature against a fresh sample with a weighted
ensemble of four metrics: tool distribution similarity computed from the Jensen
Shannon divergence (Lin, 1991) at 25 percent, embedding cosine similarity at 30
percent, sequence similarity computed as a per state divergence over transition
matrices at 25 percent, and a statistical profile at 20 percent. The result is a
score between zero and one with pass, warning, and fail bands.

We introduce two changes to the representation, each behind a feature flag for safe
rollout. The first is confidence aware scoring. Metrics that cannot be computed for
a particular trajectory, for example sequence similarity for a one step trajectory
or statistics for a trajectory with no message content, previously contributed a
neutral value of one half. Because two of the four metrics could behave this way,
nearly half of the score could drift toward the midpoint. In the revised design an
unmeasurable metric abstains, and its weight is redistributed across the metrics
that did produce a value.

The second change is the vector encoding. The legacy encoding placed histogram
values into vector positions by sorted magnitude. As a result, two agents that used
different tools but shared a similar distribution shape landed their values in the
same positions, and the cosine metric compared shape rather than tool identity. The
revised encoding places each tool and transition into a position determined by a
stable hash of its name, using signed feature hashing (Weinberger et al., 2009), so
that a given tool maps to the same dimension for every agent. It replaces fixed
divisors with bounded transforms and uses the full dimensionality. The hash is
process independent, which matters because vectors are persisted and must remain
comparable across restarts.

### Architecture

The service is built on a Python web framework backed by PostgreSQL with the
pgvector extension. Human authentication uses a hosted identity provider in the base
deployment, and the broker additionally accepts any OpenID Connect provider. Tokens
are signed with RS256 and verified through a published key set, and risk signals are
delivered as Security Event Tokens. A web client presents the platform. The stored
vector is a derived cache of the encoding independent structured signature, which
lets the system recompute vectors on demand and keep verification correct across
encoding changes.

## Implementation of the Identity and Attestation Layer

### Active Challenge Response Verification

Passive verification accepts any submitted trajectory, which makes it vulnerable to
replay. In active verification the verifier, not the agent, drives the exchange. The
service issues a signed, single use challenge that binds a server chosen and nonce
seeded subset of probes. The agent must respond to those specific probes, and the
responses are scored against a stored per probe profile. The nonce defeats replay,
because a recorded response was bound to a nonce that has already been consumed. The
server chosen selection defeats precomputation. An impostor who holds a valid key
but behaves differently still fails the behavioral score.

### Token Exchange Broker with Federation

A token exchange endpoint (Jones et al., 2020) accepts a human identity token, which
it validates through a pluggable provider registry, and an agent attestation token,
which is the verification token described above. In return it issues a scoped,
audience bound, and short lived delegated token that a relying party can accept.
Behavioral verification therefore gates real downstream authorization. Per agent
scope allowances enforce least privilege, and the broker checks that the human
presenting the request actually owns the agent named in the attestation token.

### Shared Signals and Continuous Access Evaluation

The service operates as a transmitter for the Shared Signals Framework
(Tulshibagwale et al., 2025) and the Continuous Access Evaluation Profile (Cappalli &
Tulshibagwale, 2025). A failed behavioral check emits a behavioral anomaly event,
and a revocation emits a session revoked event. Events are encoded as Security Event
Tokens (Hunt et al., 2018), carry standard subject identifiers (Backman et al.,
2023), and are delivered by poll (Backman et al., 2020a) or by push (Backman et al.,
2020b). This positions the system as a source of agent behavior signals that
existing identity providers can consume during continuous access evaluation.

### Authorization for the Model Context Protocol

Tool servers in the Model Context Protocol ecosystem frequently expose tools without
authentication. We provide a reference authorization layer. A tool call must present
a valid attestation token, verified against the published key set, and the requested
tool must appear in the agent's allowlist. Otherwise the call is denied. The decision
function is what a production tool server or proxy would invoke before dispatch.

### Continuous Mid Session Attestation

To address swap and hijack after the initial check, a session is anchored to the
agent's baseline signature, and each incoming behavioral window is scored against it.
A one sided cumulative sum statistic accumulates the positive part of the difference
between a reference similarity and the observed window similarity (Page, 1954). Normal
variation, where similarity sits above the reference, does not accumulate, while
sustained divergence accumulates and escalates the status from acceptable to warning
to alarm. The statistic decreases again when behavior returns to baseline, so the
detector recovers without manual reset. The alarm status is the natural live input
to the risk transmitter described above.

### Telemetry Ingestion

To gather real behavior, and ultimately a real corpus, the service ingests agent
traces in the OpenTelemetry generative AI format (OpenTelemetry Authors, n.d.) and in
two common commercial trace formats. It maps spans to trajectory steps, preserving
timing and error status, and enriches the agent's signature. The mapping reuses the
existing engine rather than building a separate observability product, and the
service persists only derived features, not raw spans.

## Evaluation

### Method

We constructed a deterministic and seeded synthetic benchmark. It defines several
agent profiles, each consisting of a tool distribution and a small content
vocabulary, and it includes a pair of profiles that share an identical histogram
shape but use disjoint tools, which isolates the shape collision failure mode. A
same agent pair draws two samples from one profile, and a different agent pair draws
from two profiles. We report results on four subsets: full trajectories that include
content, tool only trajectories with no messages, short trajectories of length three
to five, and the shape collision case. On each subset we compute the area under the
receiver operating characteristic curve and the equal error rate for the same agent
versus different agent decision, the mean separation between the two score
distributions, and the area under the curve for the cosine sub score on its own. The
sample sizes are 330 same agent pairs and 500 different agent pairs per subset, and
132 and 144 for the shape collision subset. All metrics are implemented directly,
and the harness is reproducible.

We compare two configurations: V1, the legacy scoring and legacy vector encoding,
and V1 plus V2, which combines confidence aware scoring with the hashed encoding.

### Discrimination Results

The following table reports the four metrics per subset for both configurations.

| Subset | Configuration | AUC | Equal error rate | Separation | Cosine AUC |
|--------|---------------|----:|-----------------:|-----------:|-----------:|
| Full | V1 | 0.9751 | 0.0673 | 0.1836 | 0.508 |
| Full | V1 plus V2 | 0.9943 | 0.0337 | 0.2283 | 0.8156 |
| Tool only | V1 | 0.9991 | 0.0095 | 0.2041 | 0.5103 |
| Tool only | V1 plus V2 | 0.9999 | 0.0085 | 0.3107 | 0.819 |
| Short | V1 | 0.9143 | 0.1683 | 0.1086 | 0.4977 |
| Short | V1 plus V2 | 0.9572 | 0.0879 | 0.1661 | 0.7303 |
| Shape collision | V1 | 0.9999 | 0.0073 | 0.2360 | 0.4987 |
| Shape collision | V1 plus V2 | 1.0000 | 0.0000 | 0.3789 | 0.8838 |

The clearest result concerns the cosine sub score. Under the legacy encoding its
area under the curve is approximately 0.50 on every subset, which is no better than
chance. The embedding was effectively not discriminating, because it was fooled by
distribution shape. The hashed encoding raises this value to a range of 0.73 to
0.88. Overall area under the curve and separation improve on every subset, and the
gains are most visible on short trajectories, where the area under the curve rises
from 0.914 to 0.957, and on the shape collision case, where separation rises from
0.236 to 0.379 and the equal error rate falls to zero.

Two targeted measurements support the same conclusion. On a pair of agents that use
disjoint tools but share a distribution shape, the cosine similarity falls from
0.888, a clear false positive, to 0.282. On the tool only subset, the separation
between same agent and different agent scores rises from 0.3225 to 0.4032, an
increase of about 25 percent, while full length trajectories produce results
identical to the legacy path, which confirms there is no regression there.

### Replay Resistance and Attestation

Active challenge response verification rejected every replayed session in testing,
because the single use nonce is consumed on first use. It also rejected tampered and
wrong agent challenge tokens, and it failed behaviorally divergent impostors that
held a valid key, where an observed active score of about 0.31 contrasted with a
score of 1.0 for a genuine response. Continuous attestation held at the acceptable
status, with a cumulative sum of zero, across consistent windows. When behavior
switched to a divergent pattern, with a per window similarity near 0.34 that
accumulated about 0.16 of drift per window, the status escalated to warning and then
to alarm at roughly the fourth window under the default thresholds, and it recovered
when behavior returned to baseline.

### Calibration and Learned Weights

Platt scaling of the raw ensemble score (Platt, 1999) improved the Brier score from
0.242, when the raw score was treated as a probability, to 0.092, and it mapped the
operational threshold of 0.7 to a calibrated probability of about 0.9997. Separately,
fitting the ensemble weights by regularized logistic regression on the synthetic set
produced weights that strongly favored the tool distribution and sequence metrics
and nearly removed the cosine and statistics metrics, in exchange for an area under
the curve change from 0.999 to 1.000 on an already saturated subset. This is a clear
case of overfitting to the generator. We therefore ship both calibration and learned
weights but disable them by default until a real corpus is available. We regard
reporting this negative result, rather than enabling the features, as a contribution
to honest evaluation practice.

### Software Validation

The implementation is covered by an automated suite that exercises every component
on the backend and the user interface, and each behavioral change was validated in
both the legacy and the revised regimes to confirm backward compatibility. Each
capability was also exercised end to end against a running deployment. Per component
test reports accompany the artifact.

## Discussion

The evaluation supports three claims. The first is that representation matters more
than the choice of ensemble weights. Simply encoding tool identity in a stable way,
rather than by magnitude, turned a chance level embedding into a useful one, which
is why we adopt the new encoding by default but do not adopt learned weights. The
second is that freshness is the decisive lever for behavioral security. A passive
behavioral check can be replayed, whereas a server chosen and single use challenge
cannot, and this costs nothing in model quality. The third is that continuous
monitoring outperforms a one time check, because the integrity gap lives after
authorization, and a lightweight sequential test catches sustained drift while
ignoring benign variation. Placing these signals into standards based authorization
paths, namely the token exchange broker, the risk transmitter, and the tool call
gate, is what converts a similarity score into an enforceable control.

## Limitations

Several limitations bound the strength of our claims.

The evaluation is synthetic. The generator models distributional, sequential, and
shape differences, but it does not capture the idiosyncrasies of real models, and
the absolute values of the area under the curve are near saturation. The numbers
should be read as relative comparisons between V1 and V2 rather than as production
performance.

The behavioral layer is probabilistic. Behavioral signatures are anomaly detection,
not authentication. An adversary who accurately mimics a target's behavior and also
holds the key can pass the behavioral check. We mitigate this with active probing
and continuous attestation, but we do not claim cryptographic identity from behavior.

There is no cryptographic runtime root at present. We do not attest the model weights
or the system prompt through a trusted execution environment, which is the principal
direction for future work.

The deployment keeps several pieces of state in process, including rate limiter
counters, challenge nonces, the risk event queue, and attestation sessions.
Horizontal scaling requires a shared store.

Thresholds and weights are either hand set or fit on synthetic data, and
telemetry derived enrichment assumes well formed traces from a submitter
authenticated by the agent key.

## Ethics and Responsible Disclosure

The system is defensive in purpose. It improves attribution and anomaly detection
for actions taken by agents. Trajectories can be sensitive, so the service persists
only derived features rather than raw spans, and it supports redaction and metadata
only modes, with zero knowledge verification identified as future work. Behavioral
fingerprinting can identify which model or agent acted, which raises privacy
considerations, and operators should disclose monitoring. No third party systems
were attacked during this work, and all evaluation used self generated data. The
dual use risk is limited, because the techniques detect impersonation rather than
enable it.

## Future Work

Priorities include a real trajectory benchmark with a public leaderboard, learned
contrastive embeddings of trajectories to replace the hand crafted statistics, a
cryptographic runtime root that binds model and prompt hashes through remote
attestation, decentralized verification using verifiable credentials together with
zero knowledge proofs of signature match, a full transport implementation for the
Model Context Protocol and an agent to agent handshake, the full stream lifecycle
for Shared Signals, per agent thresholds learned from telemetry, and submission of
the behavioral attestation profile to the relevant standards bodies.

## Conclusion

Agent identity needs more than a credential. It needs a way to bind an agent to a
responsible human, to recognize the agent from its behavior, to keep checking after
the first request, and to feed that judgment into the authorization decisions that
already govern access. World of Agents assembles these pieces from established
standards and a behavioral signature engine, and it is candid about which guarantees
are hard and which are statistical. The evaluation, although synthetic, shows that a
careful representation makes the behavioral signal genuinely discriminating, that
active challenges remove the replay weakness of passive checks, and that continuous
attestation closes the integrity gap that opens after authorization.

## References

Anthropic. (2024). *Introducing the Model Context Protocol*. https://www.anthropic.com/news/model-context-protocol

Backman, A., Jones, M., Scurtescu, M., Ansari, M., & Nadalin, A. (2020a). *Poll-based security event token (SET) delivery using HTTP* (RFC 8936). RFC Editor. https://doi.org/10.17487/RFC8936

Backman, A., Jones, M., Scurtescu, M., Ansari, M., & Nadalin, A. (2020b). *Push-based security event token (SET) delivery using HTTP* (RFC 8935). RFC Editor. https://doi.org/10.17487/RFC8935

Backman, A., Scurtescu, M., & Jain, P. (2023). *Subject identifiers for security event tokens* (RFC 9493). RFC Editor. https://doi.org/10.17487/RFC9493

Cappalli, T., & Tulshibagwale, A. (2025). *OpenID continuous access evaluation profile 1.0* (Final specification). OpenID Foundation. https://openid.net/specs/openid-caep-1_0-final.html

Google. (n.d.). *Agent identity overview*. Google Cloud documentation. Retrieved June 14, 2026, from https://docs.cloud.google.com/gemini-enterprise-agent-platform/govern/agent-identity-overview

Hunt, P., Jones, M., Denniss, W., & Ansari, M. (2018). *Security event token (SET)* (RFC 8417). RFC Editor. https://doi.org/10.17487/RFC8417

Jones, M., Bradley, J., & Sakimura, N. (2015). *JSON Web Token (JWT)* (RFC 7519). RFC Editor. https://doi.org/10.17487/RFC7519

Jones, M., Nadalin, A., Campbell, B., Bradley, J., & Mortimore, C. (2020). *OAuth 2.0 token exchange* (RFC 8693). RFC Editor. https://doi.org/10.17487/RFC8693

Lin, J. (1991). Divergence measures based on the Shannon entropy. *IEEE Transactions on Information Theory, 37*(1), 145–151. https://doi.org/10.1109/18.61115

Malkov, Y. A., & Yashunin, D. A. (2020). Efficient and robust approximate nearest neighbor search using hierarchical navigable small world graphs. *IEEE Transactions on Pattern Analysis and Machine Intelligence, 42*(4), 824–836. https://doi.org/10.1109/TPAMI.2018.2889473

Microsoft. (2025). *Announcing Microsoft Entra Agent ID: Secure and manage your AI agents*. Microsoft Tech Community. https://techcommunity.microsoft.com/blog/microsoft-entra-blog/announcing-microsoft-entra-agent-id-secure-and-manage-your-ai-agents/3827392

OpenTelemetry Authors. (n.d.). *Semantic conventions for generative AI systems*. OpenTelemetry, Cloud Native Computing Foundation. Retrieved June 14, 2026, from https://opentelemetry.io/docs/specs/semconv/gen-ai/

Page, E. S. (1954). Continuous inspection schemes. *Biometrika, 41*(1–2), 100–115. https://doi.org/10.1093/biomet/41.1-2.100

Pasquini, D., Kornaropoulos, E. M., & Ateniese, G. (2024). *LLMmap: Fingerprinting for large language models*. arXiv. https://arxiv.org/abs/2407.15847

Platt, J. C. (1999). Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods. In A. J. Smola, P. Bartlett, B. Schölkopf, & D. Schuurmans (Eds.), *Advances in large margin classifiers* (pp. 61–74). MIT Press.

Provos, N., & Mazières, D. (1999). A future-adaptable password scheme. In *Proceedings of the 1999 USENIX Annual Technical Conference* (pp. 81–92). USENIX Association. https://www.usenix.org/legacy/event/usenix99/provos/provos.pdf

Tulshibagwale, A., Cappalli, T., Scurtescu, M., Backman, A., Bradley, J., & Miel, S. (2025). *OpenID shared signals framework specification 1.0* (Final specification). OpenID Foundation. https://openid.net/specs/openid-sharedsignals-framework-1_0-final.html

Weinberger, K., Dasgupta, A., Langford, J., Smola, A., & Attenberg, J. (2009). Feature hashing for large scale multitask learning. In *Proceedings of the 26th Annual International Conference on Machine Learning* (pp. 1113–1120). Association for Computing Machinery. https://doi.org/10.1145/1553374.1553516

## Appendix A: Reproducibility

The synthetic evaluation is produced by the evaluation harness with a fixed seed,
and it emits the table reported under Discrimination Results. The weight fitting and
calibration fitting procedures are separate scripts. Two feature flags govern the
representation under study, one for confidence aware scoring and one for the hashed
vector encoding, and both default to on. Two further flags, for learned weights and
for calibration, default to off. Setting both representation flags off restores the
exact legacy behavior used as the V1 baseline. Per component design notes and test
reports accompany the artifact.
