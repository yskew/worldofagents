# RFC 0004 — Learned Ensemble Weights

- **Status:** Implemented (mechanism), **default OFF** (not adopted)
- **Area:** `app/services/signature_engine.py`, `scripts/fit_weights.py`, `app/config.py`
- **Depends on:** RFC 0003 (eval dataset)

---

## 1. Why

The four ensemble metrics are combined with weights `0.25/0.30/0.25/0.20` that
were hand-picked. The thesis describes them as "learned" — they were not. This
RFC builds the machinery to fit them from labeled data and evaluates whether to
adopt the result.

## 2. What was built

- `scripts/fit_weights.py` — L2-regularized logistic regression of
  same/different on the four sub-scores (deterministic, seeded). Coefficients are
  clamped to non-negative and normalized to sum 1, producing drop-in weights.
- `config.LEARNED_METRIC_WEIGHTS` — the fitted artifact (a versioned constant).
- `USE_LEARNED_WEIGHTS` flag — when on, the **V2 aggregator** uses the learned
  weights; the legacy V1 aggregator is untouched. Composes with RFC 0001
  abstention (learned weights are the base; redistribution still applies).

## 3. Result of fitting

Fit on the RFC 0003 full-subset pairs (all four metrics measurable), V2 encoding:

| | jsd | cosine | markov | stats | AUC (full) |
|--|----:|-------:|-------:|------:|-----------:|
| base (hand-set) | 0.25 | 0.30 | 0.25 | 0.20 | 0.9990 |
| learned (L2) | 0.479 | 0.156 | 0.352 | 0.013 | 1.0000 |

## 4. Decision: build it, do not adopt it yet

**Keep `USE_LEARNED_WEIGHTS=False`.** The fit overfits the synthetic generator:

- The generator makes **tool identity almost fully determine the agent**, so the
  fit piles weight on `jsd` (tool distribution) and `markov` (sequence) and
  nearly **zeros out `cosine` and `stats`**.
- That directly contradicts RFC 0002, which we adopted *because* cosine became a
  genuinely discriminating signal — these learned weights would throw that away.
- The gain is **0.999 → 1.000 AUC on an already-saturated subset** — noise, not a
  real improvement.
- Down-weighting `stats`/`cosine` reflects the synthetic content being random
  word-bank text, not a property of real agents.

Shipping weights overfit to synthetic data would be worse than the principled
hand-set weights. The honest move is to land the mechanism and the fitting tool,
and defer adoption until we can fit on a **real labeled corpus**.

## 5. What unblocks adoption

- A real trajectory corpus (the RFC 0003 §6 follow-up). Re-run `fit_weights.py`,
  replace `LEARNED_METRIC_WEIGHTS`, validate via the eval harness on held-out
  data, then flip `USE_LEARNED_WEIGHTS` in a follow-up.
- Cross-validation / train-test split in the fitter (currently fits on all
  pairs) once data volume supports it.

## 6. Tests

`tests/test_learned_weights.py`: artifact validity (non-negative, sums to 1), the
flag swaps weights only in the V2 path (V1 stays fixed), and the fitter recovers
the dominant feature on a known separable case.
