"""Tests for the RFC 0003 evaluation harness (scripts/eval_signature.py).

Validates the metric implementations (ROC-AUC, EER) on known cases and smoke-
tests the dataset generator + pair scoring on a tiny sample.
"""
from __future__ import annotations

import random

import numpy as np
import pytest

from scripts.eval_signature import (
    PROFILES,
    _build_subset,
    _pairs,
    _score_pairs,
    eer,
    roc_auc,
)


class TestROCAUC:
    def test_perfect_separation(self):
        pos = np.array([0.8, 0.9, 1.0])
        neg = np.array([0.0, 0.1, 0.2])
        assert roc_auc(pos, neg) == pytest.approx(1.0)

    def test_perfect_inversion(self):
        pos = np.array([0.0, 0.1, 0.2])
        neg = np.array([0.8, 0.9, 1.0])
        assert roc_auc(pos, neg) == pytest.approx(0.0)

    def test_identical_distributions_is_chance(self):
        pos = np.array([0.5, 0.5, 0.5])
        neg = np.array([0.5, 0.5, 0.5])
        assert roc_auc(pos, neg) == pytest.approx(0.5)

    def test_known_intermediate(self):
        # one negative sits above one positive -> 3/4 correctly ordered pairs
        pos = np.array([0.2, 0.9])
        neg = np.array([0.1, 0.5])
        assert roc_auc(pos, neg) == pytest.approx(0.75)


class TestEER:
    def test_perfect_separation_zero_eer(self):
        pos = np.array([0.8, 0.9, 1.0])
        neg = np.array([0.0, 0.1, 0.2])
        assert eer(pos, neg) == pytest.approx(0.0, abs=1e-9)

    def test_total_overlap_high_eer(self):
        pos = np.array([0.4, 0.5, 0.6])
        neg = np.array([0.4, 0.5, 0.6])
        assert eer(pos, neg) > 0.3


class TestHarnessSmoke:
    def test_generate_and_score(self):
        rng = random.Random(0)
        subset = _build_subset(
            {k: PROFILES[k] for k in list(PROFILES)[:2]}, rng, (5, 8), with_content=True
        )
        assert len(subset) == 2
        pairs = _pairs(subset, random.Random(1))
        labels = {label for _, _, label in pairs}
        assert labels == {0, 1}  # both same- and different-agent pairs present

        pos, neg = _score_pairs(pairs, "overall")
        assert len(pos) > 0 and len(neg) > 0
        assert all(0.0 <= s <= 1.0 for s in np.concatenate([pos, neg]))
        # same-agent should, on average, score higher than different-agent
        assert pos.mean() > neg.mean()
