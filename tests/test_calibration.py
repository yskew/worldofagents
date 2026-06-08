"""RFC 0006 — score calibration (Platt scaling)."""
from __future__ import annotations

import numpy as np

from app.config import settings
from app.schemas.agent import TrajectoryStep
from app.services.signature_engine import (
    calibrate_confidence,
    compare_signatures,
    extract_features,
    features_to_vector,
)
from scripts.fit_calibration import _fit_platt


def _sig(names, content=False):
    steps = []
    for i, n in enumerate(names):
        steps.append(TrajectoryStep(type="tool_call", name=n))
        if content:
            steps.append(TrajectoryStep(type="message", name="assistant", content=f"did {n} step {i}"))
    f = extract_features(steps)
    return f, features_to_vector(f)


class TestCalibrateFunction:
    def test_monotonic_in_raw_score(self):
        xs = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        ps = [calibrate_confidence(x) for x in xs]
        assert ps == sorted(ps)  # non-decreasing
        assert all(0.0 <= p <= 1.0 for p in ps)

    def test_extremes(self):
        assert calibrate_confidence(0.0) < 0.05
        assert calibrate_confidence(1.0) > 0.95


class TestConfidenceInResult:
    def test_absent_by_default(self, monkeypatch):
        monkeypatch.setattr(settings, "SCORE_CALIBRATION", False)
        f, v = _sig(["search", "read_file", "edit_file"], content=True)
        assert "confidence" not in compare_signatures(f, v, f, v)

    def test_present_when_enabled(self, monkeypatch):
        monkeypatch.setattr(settings, "SCORE_CALIBRATION", True)
        f, v = _sig(["search", "read_file", "edit_file"], content=True)
        res = compare_signatures(f, v, f, v)
        assert "confidence" in res
        assert 0.0 <= res["confidence"] <= 1.0

    def test_calibration_does_not_change_verdict(self, monkeypatch):
        fa, va = _sig(["search", "read_file", "edit_file"], content=True)
        fb, vb = _sig(["deploy", "monitor", "rollback"], content=True)
        monkeypatch.setattr(settings, "SCORE_CALIBRATION", False)
        v_off = compare_signatures(fa, va, fb, vb)["verdict"]
        monkeypatch.setattr(settings, "SCORE_CALIBRATION", True)
        v_on = compare_signatures(fa, va, fb, vb)["verdict"]
        assert v_off == v_on


class TestFitPlatt:
    def test_recovers_separation(self):
        rng = np.random.default_rng(0)
        n = 400
        y = rng.integers(0, 2, size=n).astype(float)
        s = np.clip(y * 0.5 + 0.25 + rng.normal(0, 0.05, n), 0, 1)
        a, b = _fit_platt(s, y, epochs=3000)
        assert a > 0  # higher score -> higher probability
        # calibrated probability separates the classes
        p = 1.0 / (1.0 + np.exp(-(a * s + b)))
        assert p[y == 1].mean() > p[y == 0].mean()
