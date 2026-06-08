# RFC 0001 — Confidence-Aware Ensemble Score Normalization

- **Status:** Draft (for discussion before implementation)
- **Area:** Behavioral signature engine (`app/services/signature_engine.py`)
- **Author:** (contributor)
- **Affects:** `/verify`, `/compare`, verification log, public profile stats, frontend breakdown UI

---

## 1. Problem statement

The verification score is a weighted ensemble of four metrics:

```
overall = 0.25·jsd + 0.30·cosine + 0.25·markov + 0.20·stats
```

Two of the four metrics inject a **neutral `0.5`** when they cannot be computed, instead of abstaining:

- `_markov_score` returns `0.5` when either transition matrix is empty — i.e. trajectories shorter than 2 distinct transitions (`signature_engine.py:285`, `:289`, `:323`).
- `_stats_score` returns `0.5` when there is no comparable message content (`signature_engine.py:343`).

Together these carry **45% of the weight**. The practical consequences:

1. **Tool-only trajectories are systematically mis-scored.** Many real agent trajectories are mostly `tool_call` steps with little/no message content, so `stats_score` collapses to `0.5` *as the normal case*, not an edge case. 20% of every such score is noise.
2. **Short trajectories drift toward `0.5`.** A genuine agent submitting a brief trajectory is pulled *down* from a true high score; an impostor with a brief trajectory is pulled *up* toward the 0.7 pass line. The bias cuts against the security goal in the worst direction.
3. **The `0.5` is silent.** Callers see a `markov_score: 0.5` in the breakdown and cannot tell "moderately similar" from "not measurable." The frontend renders it as a half-full bar — visually identical to a real partial match.

This is a correctness issue in the scoring core, not a feature gap. It is the recommended first contribution because it requires **no data-model migration** (the stored signature/vector are untouched).

## 2. Goals & non-goals

**Goals**
- Metrics that cannot be computed should **abstain** (be excluded and have their weight redistributed) rather than vote `0.5`.
- Surface *measurability* to callers so a missing metric is distinguishable from a mediocre one.
- Preserve every invariant the current system and tests rely on: score ∈ [0,1], symmetry (A→B == B→A), identical trajectories ≈ 1.0, impersonation still fails.
- Be measurably better on a labeled eval set, with no regression on full trajectories.

**Non-goals (deliberately deferred — see §8)**
- Learning the weights from data.
- Changing the 256-dim vector encoding (that is RFC 0002; it *does* need migration).
- Score calibration / turning the 0–1 number into a true probability.
- Changing the 0.7/0.4 verdict thresholds.

## 3. Existing-system awareness (what this touches)

| Consumer | File | Coupling | Risk |
|----------|------|----------|------|
| `/verify` | `app/api/verify.py:35,66` | reads `overall_score`, `verdict`, `breakdown` | verdict may flip for borderline agents |
| `/compare` | `app/api/verify.py:77,82` | same | display only, low risk |
| Response schema | `app/schemas/verify.py:22,33` | `breakdown: dict` (untyped) | additive change is safe |
| Verification log | `verification_log.similarity_score`, `passed` | new rows scored under new logic | **old vs new scores mix** (see §5) |
| Public profile | `app/api/wellknown.py:61` | `avg_similarity_score` = AVG over all log rows | average blends two scoring regimes |
| Frontend bars | `frontend/src/components/BreakdownBars.tsx:13-16` | **hardcodes weights `0.25/0.30/0.25/0.20`** | displayed weights go stale if weights become dynamic |
| Frontend types | `frontend/src/lib/api.ts:53-68` | breakdown shape | additive fields are safe; removed fields break build |

The weight constants live in **three** places (engine, frontend display, this RFC). Part of this work is making the engine the single source of truth and having the API echo the *effective* weights so the frontend stops hardcoding them.

## 4. Proposed design

Replace the fixed-weight sum with **weight redistribution over the subset of metrics that produced a value.** Each metric returns either a score or `None` (abstain).

```python
# pseudocode — compare_signatures
components = {
    "jsd":    (_jsd_score(...),    0.25),
    "cosine": (_cosine_score(...), 0.30),
    "markov": (_markov_score(...), 0.25),  # returns None when unmeasurable
    "stats":  (_stats_score(...),  0.20),  # returns None when unmeasurable
}
applicable = {k: (s, w) for k, (s, w) in components.items() if s is not None}
total_w = sum(w for _, w in applicable.values())
overall = sum(s * w for s, w in applicable.values()) / total_w   # re-normalized
```

- `jsd` and `cosine` are (almost) always computable from any non-empty trajectory, so `overall` never divides by zero in practice; add a guard returning `0.0` if somehow nothing is applicable.
- `_markov_score` / `_stats_score` change their *empty* branches from `return 0.5` to `return None`. Their real computation paths are unchanged.

**Breakdown becomes self-describing (additive, backward-compatible):**

```jsonc
{
  "overall_score": 0.83,
  "verdict": "pass",
  "breakdown": {
    "jsd_score": 0.91, "cosine_score": 0.88,
    "markov_score": 0.79, "stats_score": null,   // null = abstained (was 0.5)
    "effective_weights": { "jsd": 0.31, "cosine": 0.38, "markov": 0.31, "stats": 0.0 }
  }
}
```

Existing keys keep their names; `markov_score`/`stats_score` may now be `null`; `effective_weights` is **new and optional**. The frontend reads `effective_weights` if present and falls back to the old constants if absent — so old/new clients and servers interoperate during rollout.

**Rollout is feature-flagged.** Add `SCORE_NORMALIZATION_V2: bool = False` to `app/config.py`. Default off → identical behavior to today. Flip on in staging, measure (§6), then default on in a later release. This makes the change reversible without a redeploy of code.

## 5. Backward compatibility & data

- **Stored signatures / vectors:** untouched. No Alembic migration. Existing agents verify exactly as before. This is the whole reason to do this RFC before the vector-encoding one.
- **API shape:** purely additive (`null` is already valid for `markov_score`/`stats_score` since `breakdown` is an untyped dict; `effective_weights` is new). No client breaks.
- **Historical log scores:** rows written before the flip used the old logic. `avg_similarity_score` will silently blend regimes. **Mitigation:** add a nullable `score_version SMALLINT` column to `verification_log` (a *small* additive migration — the only schema change, and optional). New rows tag `2`; old rows are `NULL`/`1`. Profile stats can then filter or report per-version. This also unlocks longitudinal before/after analysis.
- **Verdict flips:** borderline agents near 0.7 may move. We quantify this on seeded + eval data *before* flipping the flag (success metric below) and document the expected shift in the release notes.

## 6. Testing plan

Tests are easy here: the engine is pure functions, no IO. Build the safety net **before** changing logic.

1. **Characterization (lock current behavior first).** Snapshot the 5×5 score matrix across the seeded archetypes (`scripts/seed.py`: code/devops/research/data-pipeline/security) under the flag *off*. Any drift while the flag is off is a regression.
2. **Unit — abstention.** Tool-only trajectory → `stats_score is None`, `effective_weights["stats"] == 0`, and `overall` equals the renormalized 3-metric blend. Single-step trajectory → `markov_score is None`.
3. **Invariants (property tests).**
   - Score always ∈ [0, 1].
   - **Symmetry:** `compare(a,b).overall == compare(b,a).overall` (the current symmetry test must still pass under V2).
   - Identical trajectories → overall ≈ 1.0.
   - Disjoint tool sets → overall stays low (not pulled up by removed 0.5s).
4. **Security regression.** The existing impersonation test (`tests/test_user_flows.py`) — register a coding agent, verify with malicious behavior — must still **fail** under V2. Ideally it fails *harder* (lower score) because stats no longer floors at 0.5.
5. **Verdict-stability report.** A test/script that runs the eval set under flag off vs on and prints the confusion of verdicts (pass↔warning↔fail flips). Reviewed in the PR, not asserted.
6. **Coverage:** maintain ≥ 86% (current bar). New branches in `compare_signatures` are covered by tests 2–3.

## 7. Success metrics (how we know it's better, not just different)

The change must improve *discrimination*, not merely move numbers. Build a small **labeled eval set**: pairs of trajectories tagged `same-agent` / `different-agent`, including a deliberate **short / tool-only subset** (the population this RFC targets).

Primary metrics, measured V1 vs V2 on that set:

| Metric | Definition | Target |
|--------|-----------|--------|
| **ROC-AUC** | separability of same vs different | ↑ or unchanged overall; **↑ on the short/tool-only subset** |
| **Equal Error Rate (EER)** | where FAR == FRR | ↓ on the short/tool-only subset |
| **Score separation** | `mean(same) − mean(different)` | ↑ on short/tool-only; no regression on full trajectories |
| **`0.5` pile-up** | fraction of scores in [0.45, 0.55] | ↓ materially |

Acceptance bar: **no regression on full-trajectory pairs**, and a **measurable AUC/EER improvement on the short/tool-only subset**. If full-trajectory AUC regresses, the redistribution is mis-specified and we stop.

The eval set itself is a reusable artifact — it becomes the test bed for RFC 0002 and the training data for learned weights (§8).

## 8. Future enhancements this unlocks

- **Learned weights.** The thesis calls the weights "learned," but they are hardcoded. The §7 eval set is exactly the labeled data needed to fit them (logistic regression over the four sub-scores). The single-source-of-truth weights (§3) make swapping them a config change.
- **Per-metric confidence.** Abstention is binary today; a follow-up can return a confidence per metric (e.g. weight by trajectory length) so a 3-step markov contributes less than a 300-step one.
- **Score calibration.** Platt/isotonic calibration so the 0–1 number is an interpretable probability, making the 0.7 threshold defensible rather than chosen by feel.
- **Score versioning everywhere.** The `score_version` column (§5) generalizes to A/B-testing future scoring changes against live traffic.

## 9. Implementation status (branch `raghul-branch`)

- [x] Add `SCORE_NORMALIZATION_V2` flag to `app/config.py` (default `False`).
- [x] Characterization test: seeded 5×5 score snapshot (flag off) — `tests/test_score_normalization.py::TestV1Characterization`.
- [x] `_markov_score` / `_stats_score`: empty branches return `None`.
- [x] `compare_signatures`: redistribute weights over applicable metrics; emit `effective_weights` (V2) while preserving legacy output exactly (V1).
- [x] Frontend: `BreakdownBars` reads `effective_weights` with fallback and renders abstained (`null`) metrics as N/A; shared `ScoreBreakdown` type in `lib/api.ts`.
- [x] `verification_log.score_version` column + migration `a1b2c3d4e5f6`; `/verify` tags new rows (`1` legacy / `2` V2).
- [x] Eval + V1/V2 metric comparison (below).
- [ ] **Flip default to `True`** — deferred to a follow-up once reviewed and validated against real traffic.

### Measured results

Engine + RFC suites: **34 passed** (19 pre-existing + 15 new), ruff clean.

| Population | V1 separation (same − different) | V2 separation | Outcome |
|------------|:---:|:---:|---|
| Full seeded archetypes (all have content + ≥2 steps) | identical | identical | **No regression** — nothing abstains |
| Tool-only trajectories (target population) | 0.3225 | **0.4032** | **+25% separation**: legit ↑ (0.722→0.777), impostor ↓ (0.399→0.374) |

Impersonation still fails under both regimes, and V2 scores the impostor *no higher* than V1 (asserted in tests).

> Note: the example numbers above are illustrative from the dev harness, not a
> statistically powered eval. Before flipping the default, build the labeled
> eval set described in §7 and report ROC-AUC / EER on the short/tool-only
> subset vs full trajectories.
```
