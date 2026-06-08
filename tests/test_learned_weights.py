"""RFC 0004 — learned ensemble weights.

Verifies the learned-weights artifact is valid, that the flag swaps weights only
in the V2 aggregator (legacy V1 stays fixed), and that the fitting utilities
behave on a known separable case.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.config import LEARNED_METRIC_WEIGHTS, settings
from app.schemas.agent import TrajectoryStep
from app.services.signature_engine import (
    compare_signatures,
    extract_features,
    features_to_vector,
)
from scripts.fit_weights import _fit_logreg, _to_weights


def _traj():
    return [
        TrajectoryStep(type="tool_call", name="search"),
        TrajectoryStep(type="tool_call", name="read_file"),
        TrajectoryStep(type="message", name="assistant", content="found the file, fixing it now"),
        TrajectoryStep(type="tool_call", name="edit_file"),
        TrajectoryStep(type="tool_call", name="run_tests"),
        TrajectoryStep(type="message", name="assistant", content="all tests pass"),
    ]


class TestLearnedWeightsArtifact:
    def test_valid_distribution(self):
        assert set(LEARNED_METRIC_WEIGHTS) == {"jsd", "cosine", "markov", "stats"}
        assert all(w >= 0 for w in LEARNED_METRIC_WEIGHTS.values())
        assert sum(LEARNED_METRIC_WEIGHTS.values()) == pytest.approx(1.0, abs=1e-3)


class TestFlagSwapsWeights:
    def _effective(self, monkeypatch, learned: bool):
        monkeypatch.setattr(settings, "SCORE_NORMALIZATION_V2", True)
        monkeypatch.setattr(settings, "VECTOR_ENCODING_V2", True)
        monkeypatch.setattr(settings, "USE_LEARNED_WEIGHTS", learned)
        f = extract_features(_traj())
        v = features_to_vector(f)
        # identical comparison -> all four metrics measurable -> effective == base
        return compare_signatures(f, v, f, v)["breakdown"]["effective_weights"]

    def test_default_uses_base_weights(self, monkeypatch):
        eff = self._effective(monkeypatch, learned=False)
        assert eff == pytest.approx({"jsd": 0.25, "cosine": 0.30, "markov": 0.25, "stats": 0.20}, abs=1e-6)

    def test_flag_uses_learned_weights(self, monkeypatch):
        eff = self._effective(monkeypatch, learned=True)
        assert eff == pytest.approx(LEARNED_METRIC_WEIGHTS, abs=1e-3)

    def test_v1_aggregator_ignores_learned_weights(self, monkeypatch):
        """Legacy V1 path must stay on the fixed base weights regardless."""
        monkeypatch.setattr(settings, "SCORE_NORMALIZATION_V2", False)
        monkeypatch.setattr(settings, "VECTOR_ENCODING_V2", False)
        monkeypatch.setattr(settings, "USE_LEARNED_WEIGHTS", True)
        f = extract_features(_traj())
        v = features_to_vector(f)
        bd = compare_signatures(f, v, f, v)["breakdown"]
        # V1 breakdown has no effective_weights and identical -> 1.0 overall
        assert "effective_weights" not in bd
        assert compare_signatures(f, v, f, v)["overall_score"] == pytest.approx(1.0, abs=1e-6)


class TestFitUtilities:
    def test_to_weights_normalizes_and_clamps(self):
        w = _to_weights(np.array([2.0, -1.0, 1.0, 1.0]))
        assert w["cosine"] == 0.0  # negative clamped
        assert sum(w.values()) == pytest.approx(1.0, abs=1e-6)
        assert w["jsd"] > w["markov"]  # larger coef -> larger weight

    def test_fit_recovers_dominant_feature(self):
        rng = np.random.default_rng(0)
        # feature 0 perfectly separates; others are noise
        n = 200
        y = rng.integers(0, 2, size=n).astype(float)
        X = np.column_stack([
            y * 0.8 + 0.1,                    # informative
            rng.random(n),                    # noise
            rng.random(n),                    # noise
            rng.random(n),                    # noise
        ])
        coef, _ = _fit_logreg(X, y, epochs=2000)
        assert coef[0] == max(coef)
