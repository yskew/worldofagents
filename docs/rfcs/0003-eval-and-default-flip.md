# RFC 0003 — Signature Eval Harness and V2 Default Flip

- **Status:** Implemented
- **Area:** `scripts/eval_signature.py`, `app/config.py` defaults
- **Depends on:** RFC 0001 (scoring), RFC 0002 (vector encoding)

---

## 1. Why

RFC 0001 and RFC 0002 both shipped behind flags defaulting to `False`, each
deferring its default flip to "a statistically powered eval." This RFC builds
that eval and records the decision.

## 2. Method

`scripts/eval_signature.py` generates a **deterministic** (seeded) labeled
dataset of trajectory pairs and scores every pair under all four flag
combinations, reporting discrimination metrics.

- **Profiles:** 5 realistic agent profiles (coder, devops, researcher, data,
  security), each a tool distribution + content word bank. Two extra profiles
  (`shapeA`/`shapeB`) share an identical histogram *shape* but use *disjoint*
  tools — the RFC 0002 collision case.
- **Pairs:** same-agent = two samples from one profile; different-agent = samples
  from two profiles. Different-agent pairs capped at 500 per subset for runtime.
- **Subsets:** `full` (with content), `tool_only` (no messages — RFC 0001's
  target), `short` (length 3–5), `shape_collision`.
- **Metrics:** ROC-AUC (Mann-Whitney), Equal Error Rate (threshold sweep), mean
  separation `mean(same) − mean(different)`, on the overall score; plus the
  cosine sub-score AUC (the quantity RFC 0002 changes). Implemented in numpy —
  no new dependencies.

Reproduce: `docker compose exec api python scripts/eval_signature.py`.

## 3. Results

Overall-score metrics (higher AUC / separation better, lower EER better), and
the cosine sub-score AUC:

| Subset | Config | AUC | EER | Separation | Cosine AUC |
|--------|--------|----:|----:|-----------:|-----------:|
| full | V1 baseline | 0.9751 | 0.0673 | 0.1836 | 0.508 |
| full | **RFC0001+0002** | **0.9943** | **0.0337** | **0.2283** | **0.8156** |
| tool_only | V1 baseline | 0.9991 | 0.0095 | 0.2041 | 0.5103 |
| tool_only | **RFC0001+0002** | **0.9999** | **0.0085** | **0.3107** | **0.819** |
| short | V1 baseline | 0.9143 | 0.1683 | 0.1086 | 0.4977 |
| short | **RFC0001+0002** | **0.9572** | **0.0879** | **0.1661** | **0.7303** |
| shape_collision | V1 baseline | 0.9999 | 0.0073 | 0.2360 | 0.4987 |
| shape_collision | **RFC0001+0002** | **1.0000** | **0.0000** | **0.3789** | **0.8838** |

Sample sizes: full/tool_only/short = 330 same / 500 different; shape_collision =
132 / 144.

### Reading the numbers

- **Cosine sub-score (RFC 0002):** AUC moves from ~**0.50 (chance)** to
  **0.73–0.88** across every subset. The legacy cosine metric was effectively
  not discriminating at all — it was fooled by distribution shape. This is the
  headline result.
- **Overall AUC:** the combined config beats V1 baseline on **every** subset
  (notably short 0.914 → 0.957), and EER drops everywhere.
- **Separation:** improves on every subset, largest on the RFC 0001 targets
  (tool_only 0.204 → 0.311) and the RFC 0002 target (shape_collision 0.236 →
  0.379).

### Honest caveats

- On `full`, RFC 0001 *alone* nudges AUC by −0.001 (0.9751 → 0.9740) — within
  noise — while improving separation. With RFC 0002 also on (the shipping
  config) full AUC is clearly above baseline (0.9943).
- AUCs on tool_only/shape_collision are near-saturated (~1.0); separation is the
  more sensitive signal there, and it improves.
- The dataset is synthetic. It models distributional and shape differences well
  but not real-model idiosyncrasies; treat absolute AUCs as directional and the
  V1-vs-V2 *deltas* as the signal.

## 4. Decision

**Flip both defaults to `True`** in `app/config.py`:
`SCORE_NORMALIZATION_V2` and `VECTOR_ENCODING_V2`. Justification: the combined
config dominates the V1 baseline on AUC, EER, and separation across all subsets,
with the cosine metric going from useless to genuinely discriminating, and no
material regression anywhere.

Both flags remain as escape hatches (`=false` restores exact legacy behavior);
the full test suite passes under both regimes.

## 5. Rollout notes

- Stored vectors created under the legacy encoding should be re-embedded:
  `docker compose exec api python scripts/reembed.py`. Live verification is
  already correct without it (`/verify` recomputes from the JSONB signature).
- Verification-log scores written before the flip are tagged `score_version`
  NULL/1; new ones are 2. `avg_similarity_score` on public profiles blends
  regimes until old logs age out — acceptable, and inspectable via the column.

## 6. Future work

- Replace the synthetic generator with a corpus of real agent trajectories.
- The labeled set is the training input for **learned ensemble weights**
  (RFC 0004) and **score calibration** — both now unblocked.
