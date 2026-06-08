"""Fit Platt scaling for the ensemble score (RFC 0006).

The raw overall score is a weighted average in [0,1], not a probability. Platt
scaling fits P(same | score) = sigmoid(a*score + b) so the number becomes an
interpretable confidence and the 0.7 threshold can be justified statistically.

Deterministic (seeded eval dataset). Run it, copy a/b into
app/config.py::CALIBRATION_PARAMS.

Usage:
    docker compose exec api python scripts/fit_calibration.py
"""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from app.config import settings
from app.services.signature_engine import compare_signatures, features_to_vector
from scripts.eval_signature import PROFILES, SEED, _build_subset, _pairs


def _scores_labels():
    scores, labels = [], []
    for sub_seed, content in [(SEED, True), (SEED + 1, False)]:
        subset = _build_subset(PROFILES, random.Random(sub_seed), (4, 14), with_content=content)
        for fa, fb, label in _pairs(subset, random.Random(sub_seed + 7)):
            va, vb = features_to_vector(fa), features_to_vector(fb)
            scores.append(compare_signatures(fa, va, fb, vb)["overall_score"])
            labels.append(label)
    return np.array(scores, dtype=float), np.array(labels, dtype=float)


def _fit_platt(s: np.ndarray, y: np.ndarray, lr: float = 0.5, epochs: int = 20000):
    a, b = 1.0, 0.0
    n = len(s)
    for _ in range(epochs):
        p = 1.0 / (1.0 + np.exp(-(a * s + b)))
        ga = float(np.sum((p - y) * s) / n)
        gb = float(np.sum(p - y) / n)
        a -= lr * ga
        b -= lr * gb
    return a, b


def _brier(s, y, a, b):
    p = 1.0 / (1.0 + np.exp(-(a * s + b)))
    return float(np.mean((p - y) ** 2))


def main():
    print(f"Encoding V2={settings.VECTOR_ENCODING_V2}, ScoreNorm V2={settings.SCORE_NORMALIZATION_V2}")
    s, y = _scores_labels()
    print(f"Fitting Platt on {len(y)} pairs ({int(y.sum())} same / {int(len(y) - y.sum())} different)")
    a, b = _fit_platt(s, y)
    print(f"\na={a:.4f} b={b:.4f}")
    print(f"Brier (raw score as prob): {_brier(s, y, 1.0, 0.0):.4f}")
    print(f"Brier (calibrated):        {_brier(s, y, a, b):.4f}")
    # report the probability the 0.7 raw threshold maps to
    p_at_07 = 1.0 / (1.0 + np.exp(-(a * 0.7 + b)))
    print(f"raw 0.7 -> calibrated p={p_at_07:.4f}")
    print("\nPaste into app/config.py::CALIBRATION_PARAMS:")
    print(f'    {{"a": {a:.4f}, "b": {b:.4f}}}')


if __name__ == "__main__":
    main()
