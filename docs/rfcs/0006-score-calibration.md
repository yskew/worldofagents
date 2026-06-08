# RFC 0006 — Score Calibration

- **Status:** Implemented (mechanism), **default OFF**
- **Area:** `app/services/signature_engine.py`, `scripts/fit_calibration.py`, verify/compare responses
- **Depends on:** RFC 0003 (eval dataset)

---

## 1. Why

The overall score is a weighted average in [0,1] — a similarity, not a
probability. The 0.7 / 0.4 verdict thresholds were chosen by feel. Platt scaling
maps the raw score to `P(same agent | score)`, giving an interpretable
confidence and a statistical basis for thresholds.

## 2. What was built

- `scripts/fit_calibration.py` — fits `P = sigmoid(a*score + b)` on the seeded
  eval pairs (deterministic).
- `config.CALIBRATION_PARAMS` — the fitted `{a, b}` (versioned constant).
- `signature_engine.calibrate_confidence(raw)` — applies the scaling.
- `SCORE_CALIBRATION` flag — when on, `compare_signatures` adds `confidence`,
  surfaced as an optional field on the `/verify` and `/compare` responses.

Because the map is **monotonic** (`a > 0`), it never reorders results or changes
the verdict — it is purely an added, more-interpretable number.

## 3. Fit result

On 1660 eval pairs (V2 encoding): `a = 21.4754`, `b = -6.8025`.

| | Brier score |
|--|-----------:|
| raw score used as probability | 0.2422 |
| Platt-calibrated | **0.0923** |

The calibrated probability is substantially better. Notably, a raw score of 0.7
maps to **p ≈ 0.9997** — the current pass threshold is, on this data, a very
high-confidence cutoff (arguably conservative).

## 4. Decision: ship the mechanism, default OFF

The fit is on **synthetic** data, so the absolute probabilities are only as good
as that data — exposing them as fact could mislead. The map is additive and
monotonic (no verdict risk), so this is lower-stakes than RFC 0004, but the
honest default is still OFF until re-fit on a real corpus.

Enabling later is a one-line flag flip plus, ideally, moving the verdict
thresholds into calibrated-probability space (a follow-up).

## 5. Tests

`tests/test_calibration.py`: monotonicity and extremes of `calibrate_confidence`,
`confidence` present only when enabled, verdict unchanged by calibration, and the
fitter recovers class separation on a known case.
