from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from app.schemas.agent import TrajectoryStep
from app.services.signature_engine import (
    compare_signatures,
    extract_features,
    features_to_vector,
    merge_features,
)


def _make_trajectory(steps: list[tuple[str, str, str | None]]) -> list[TrajectoryStep]:
    return [
        TrajectoryStep(type=t, name=n, content=c) for t, n, c in steps
    ]


TRAJ_A = _make_trajectory([
    ("tool_call", "search", None),
    ("tool_call", "read_file", None),
    ("message", "assistant", "Here is the content of the file you requested."),
    ("tool_call", "search", None),
    ("tool_call", "write_file", None),
    ("message", "assistant", "I have written the updated content to the file."),
    ("tool_call", "read_file", None),
    ("message", "assistant", "The file has been updated successfully."),
])

TRAJ_B = _make_trajectory([
    ("action", "deploy", None),
    ("action", "monitor", None),
    ("message", "system", "Deployment complete. Monitoring for errors."),
    ("action", "rollback", None),
    ("message", "system", "Rollback initiated due to high error rate."),
])


class TestExtractFeatures:
    def test_basic_feature_keys(self):
        features = extract_features(TRAJ_A)
        assert "tool_call_histogram" in features
        assert "transition_matrix" in features
        assert "trigram_transitions" in features
        assert "response_length_stats" in features
        assert "vocabulary_stats" in features
        assert "timing_stats" in features
        assert "structural_features" in features

    def test_histogram_sums_to_one(self):
        features = extract_features(TRAJ_A)
        hist = features["tool_call_histogram"]
        assert abs(sum(hist.values()) - 1.0) < 1e-9

    def test_transition_matrix_correct(self):
        simple = _make_trajectory([
            ("tool_call", "A", None),
            ("tool_call", "B", None),
            ("tool_call", "A", None),
            ("tool_call", "C", None),
        ])
        features = extract_features(simple)
        tm = features["transition_matrix"]
        assert tm["A"]["B"] == 0.5
        assert tm["A"]["C"] == 0.5
        assert tm["B"]["A"] == 1.0

    def test_trigram_transitions(self):
        simple = _make_trajectory([
            ("tool_call", "A", None),
            ("tool_call", "B", None),
            ("tool_call", "C", None),
            ("tool_call", "A", None),
        ])
        features = extract_features(simple)
        tri = features["trigram_transitions"]
        assert "A|B" in tri
        assert tri["A|B"]["C"] == 1.0

    def test_response_length_stats(self):
        traj = _make_trajectory([
            ("message", "m", "hello"),
            ("message", "m", "world!"),
        ])
        features = extract_features(traj)
        stats = features["response_length_stats"]
        assert stats["count"] == 2
        assert stats["mean"] == 5.5

    def test_vocabulary_stats(self):
        traj = _make_trajectory([
            ("message", "m", "the quick brown fox"),
            ("message", "m", "the lazy dog"),
        ])
        features = extract_features(traj)
        vs = features["vocabulary_stats"]
        assert vs["total_tokens"] == 7
        assert vs["unique_tokens"] == 6
        assert vs["type_token_ratio"] > 0

    def test_timing_stats_with_timestamps(self):
        now = datetime.now(timezone.utc)
        traj = [
            TrajectoryStep(type="tool_call", name="a", timestamp=now),
            TrajectoryStep(type="tool_call", name="b", timestamp=now + timedelta(seconds=10)),
            TrajectoryStep(type="tool_call", name="c", timestamp=now + timedelta(seconds=25)),
        ]
        features = extract_features(traj)
        ts = features["timing_stats"]
        assert ts is not None
        assert ts["mean_interval_s"] == 12.5
        assert ts["max_interval_s"] == 15.0

    def test_timing_stats_no_timestamps(self):
        features = extract_features(TRAJ_A)
        assert features["timing_stats"] is None

    def test_structural_features(self):
        features = extract_features(TRAJ_A)
        sf = features["structural_features"]
        assert sf["sequence_length"] == 8
        assert sf["unique_action_types"] > 0
        assert 0 <= sf["tool_call_ratio"] <= 1


class TestFeaturesToVector:
    def test_dimension(self):
        features = extract_features(TRAJ_A)
        vec = features_to_vector(features)
        assert len(vec) == 256

    def test_normalized(self):
        features = extract_features(TRAJ_A)
        vec = features_to_vector(features)
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 1e-6


class TestCompareSignatures:
    def test_identical_trajectories_high_score(self):
        sig_a = extract_features(TRAJ_A)
        vec_a = features_to_vector(sig_a)
        result = compare_signatures(sig_a, vec_a, sig_a, vec_a)
        assert result["overall_score"] >= 0.95
        assert result["verdict"] == "pass"

    def test_different_trajectories_low_score(self):
        sig_a = extract_features(TRAJ_A)
        vec_a = features_to_vector(sig_a)
        sig_b = extract_features(TRAJ_B)
        vec_b = features_to_vector(sig_b)
        result = compare_signatures(sig_a, vec_a, sig_b, vec_b)
        assert result["overall_score"] < 0.5
        assert result["verdict"] in ("fail", "warning")

    def test_returns_breakdown(self):
        sig = extract_features(TRAJ_A)
        vec = features_to_vector(sig)
        result = compare_signatures(sig, vec, sig, vec)
        assert "jsd_score" in result["breakdown"]
        assert "cosine_score" in result["breakdown"]
        assert "markov_score" in result["breakdown"]
        assert "stats_score" in result["breakdown"]

    def test_similar_trajectories_moderate_score(self):
        traj_similar = _make_trajectory([
            ("tool_call", "search", None),
            ("tool_call", "read_file", None),
            ("message", "assistant", "Here is some content from the file."),
            ("tool_call", "write_file", None),
            ("message", "assistant", "Updated the file as requested."),
        ])
        sig_a = extract_features(TRAJ_A)
        vec_a = features_to_vector(sig_a)
        sig_b = extract_features(traj_similar)
        vec_b = features_to_vector(sig_b)
        result = compare_signatures(sig_a, vec_a, sig_b, vec_b)
        assert result["overall_score"] > 0.5


class TestMergeFeatures:
    def test_merge_preserves_keys(self):
        sig_a = extract_features(TRAJ_A)
        sig_b = extract_features(TRAJ_A)
        merged = merge_features(sig_a, sig_b)
        assert set(merged.keys()) == set(sig_a.keys())

    def test_merge_histogram_sums_to_one(self):
        sig_a = extract_features(TRAJ_A)
        sig_b = extract_features(TRAJ_B)
        merged = merge_features(sig_a, sig_b)
        hist = merged["tool_call_histogram"]
        assert abs(sum(hist.values()) - 1.0) < 1e-9


class TestJSDEdgeCases:
    def test_identical_distributions(self):
        sig = extract_features(TRAJ_A)
        vec = features_to_vector(sig)
        result = compare_signatures(sig, vec, sig, vec)
        assert result["breakdown"]["jsd_score"] >= 0.99

    def test_disjoint_distributions(self):
        sig_a = extract_features(TRAJ_A)
        sig_b = extract_features(TRAJ_B)
        vec_a = features_to_vector(sig_a)
        vec_b = features_to_vector(sig_b)
        result = compare_signatures(sig_a, vec_a, sig_b, vec_b)
        assert result["breakdown"]["jsd_score"] < 0.3
