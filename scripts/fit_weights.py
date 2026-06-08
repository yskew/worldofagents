"""Fit ensemble metric weights from the labeled eval dataset (RFC 0004).

The four ensemble metrics (jsd, cosine, markov, stats) are combined as a
weighted average. The legacy weights (0.25/0.30/0.25/0.20) were hand-chosen.
This script fits them from data: logistic regression of same/different on the
four sub-scores, with non-negative coefficients normalized to sum 1.

Deterministic (seeded dataset + deterministic optimizer). Run it, copy the
printed weights into app/config.py::LEARNED_METRIC_WEIGHTS with provenance.

Usage:
    docker compose exec api python scripts/fit_weights.py
"""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from app.config import settings
from app.services.signature_engine import compare_signatures, features_to_vector
from scripts.eval_signature import PROFILES, SEED, _build_subset, _pairs, roc_auc

METRICS = ["jsd_score", "cosine_score", "markov_score", "stats_score"]
KEYS = ["jsd", "cosine", "markov", "stats"]


def _feature_matrix():
    """Build (X, y) from full-subset pairs where all four metrics are measurable,
    scored under the active (shipped) encoding."""
    subset = _build_subset(PROFILES, random.Random(SEED), (6, 14), with_content=True)
    pairs = _pairs(subset, random.Random(SEED + 7))
    rows, labels = [], []
    for fa, fb, label in pairs:
        va, vb = features_to_vector(fa), features_to_vector(fb)
        bd = compare_signatures(fa, va, fb, vb)["breakdown"]
        vals = [bd.get(m) for m in METRICS]
        if any(v is None for v in vals):
            continue  # need all four present to fit base weights
        rows.append(vals)
        labels.append(label)
    return np.array(rows, dtype=float), np.array(labels, dtype=float)


def _fit_logreg(X: np.ndarray, y: np.ndarray, lr: float = 0.5, epochs: int = 5000,
                l2: float = 0.05):
    """L2-regularized batch gradient descent. Features share the [0,1] scale, so
    raw coefficients are directly comparable as importances. Regularization
    discourages the optimizer from zeroing out metrics on a single dataset."""
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(epochs):
        z = X @ w + b
        p = 1.0 / (1.0 + np.exp(-z))
        grad_w = X.T @ (p - y) / n + l2 * w
        grad_b = float(np.mean(p - y))
        w -= lr * grad_w
        b -= lr * grad_b
    return w, b


def _to_weights(coef: np.ndarray) -> dict:
    clamped = np.clip(coef, 0.0, None)  # drop anti-correlated (shouldn't occur)
    if clamped.sum() == 0:
        clamped = np.ones_like(clamped)
    norm = clamped / clamped.sum()
    return {k: round(float(v), 4) for k, v in zip(KEYS, norm)}


def main():
    print(f"Encoding: VECTOR_ENCODING_V2={settings.VECTOR_ENCODING_V2}, "
          f"SCORE_NORMALIZATION_V2={settings.SCORE_NORMALIZATION_V2}")
    X, y = _feature_matrix()
    print(f"Fitting on {len(y)} pairs ({int(y.sum())} same / {int(len(y) - y.sum())} different)")

    coef, bias = _fit_logreg(X, y)
    learned = _to_weights(coef)
    base = {"jsd": 0.25, "cosine": 0.30, "markov": 0.25, "stats": 0.20}

    # Compare discrimination of base vs learned weighting on the same pairs.
    def auc_for(weights: dict) -> float:
        wv = np.array([weights[k] for k in KEYS])
        scores = X @ wv
        return roc_auc(scores[y == 1], scores[y == 0])

    print(f"\nraw logreg coef: {[round(c, 3) for c in coef]}  bias={bias:.3f}")
    print(f"base weights   : {base}   AUC={auc_for(base):.4f}")
    print(f"learned weights: {learned}   AUC={auc_for(learned):.4f}")
    print("\nPaste into app/config.py::LEARNED_METRIC_WEIGHTS:")
    print(f"    {learned}")


if __name__ == "__main__":
    main()
