"""RFC 0002 — principled signature vector encoding.

Covers: V1 preservation under the flag off, cross-process determinism of the
hashed encoding (guards against salted builtin hash()), the shape-collision fix
(the headline bug), full-dimension utilization, and invariants under both
encodings.
"""
from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
import pytest

from app.config import settings
from app.schemas.agent import TrajectoryStep
from app.services.signature_engine import (
    _features_to_vector_v1,
    compare_signatures,
    extract_features,
    features_to_vector,
)


def _traj(names: list[str], with_content: bool = False) -> list[TrajectoryStep]:
    steps = []
    for i, n in enumerate(names):
        steps.append(TrajectoryStep(
            type="tool_call", name=n,
            content=(f"step {i} did {n}" if with_content else None),
        ))
    return steps


@pytest.fixture
def v1(monkeypatch):
    monkeypatch.setattr(settings, "VECTOR_ENCODING_V2", False)


@pytest.fixture
def v2(monkeypatch):
    monkeypatch.setattr(settings, "VECTOR_ENCODING_V2", True)


def _cosine(features_a, features_b) -> float:
    """Cosine sub-score between two feature dicts under the active encoding."""
    va = features_to_vector(features_a)
    vb = features_to_vector(features_b)
    return compare_signatures(features_a, va, features_b, vb)["breakdown"]["cosine_score"]


# --- V1 preservation ---------------------------------------------------------

class TestV1Preserved:
    def test_dispatch_matches_legacy(self, v1):
        f = extract_features(_traj(["search", "read_file", "edit_file"], with_content=True))
        assert features_to_vector(f) == _features_to_vector_v1(f)


# --- Determinism (no salted hash) -------------------------------------------

class TestDeterminism:
    def _subprocess_vector(self, hashseed: str) -> list[float]:
        code = (
            "import json,sys; sys.path.insert(0,'.');"
            "from app.config import settings; settings.VECTOR_ENCODING_V2=True;"
            "from app.schemas.agent import TrajectoryStep as T;"
            "from app.services.signature_engine import extract_features, features_to_vector;"
            "traj=[T(type='tool_call',name=n) for n in ['search','read_file','search','edit_file','run_tests']];"
            "print(json.dumps(features_to_vector(extract_features(traj))))"
        )
        out = subprocess.check_output(
            [sys.executable, "-c", code],
            env={"PYTHONHASHSEED": hashseed, "PATH": __import__("os").environ.get("PATH", "")},
        )
        return json.loads(out)

    def test_v2_vector_is_process_independent(self):
        """Different PYTHONHASHSEED must not change the vector. If builtin hash()
        leaked in, these would differ."""
        a = self._subprocess_vector("0")
        b = self._subprocess_vector("123456")
        assert a == pytest.approx(b, abs=1e-12)


# --- The shape-collision fix (headline) -------------------------------------

class TestShapeCollisionFix:
    def test_v2_separates_same_shape_disjoint_tools(self, monkeypatch):
        """Two agents with the SAME histogram shape but DISJOINT tools.
        V1 places sorted-by-magnitude values in the same slots -> high cosine
        (the bug). V2 hashes by tool name -> the histogram bands barely overlap,
        so cosine drops to reflect that these are different agents."""
        coding = extract_features(_traj(["a", "a", "a", "b", "b", "c"]))
        devops = extract_features(_traj(["x", "x", "x", "y", "y", "z"]))

        monkeypatch.setattr(settings, "VECTOR_ENCODING_V2", False)
        cos_v1 = _cosine(coding, devops)

        monkeypatch.setattr(settings, "VECTOR_ENCODING_V2", True)
        cos_v2 = _cosine(coding, devops)

        # V1 is misled into high similarity; V2 corrects it.
        assert cos_v1 > 0.8
        assert cos_v2 < cos_v1 - 0.2

    def test_v2_same_tools_closer_than_disjoint_tools(self, v2):
        """We fixed false positives without inverting the ordering: an agent
        compared to a reordered run of ITSELF must be clearly more similar than
        to an agent using entirely different tools."""
        base = extract_features(_traj(["search", "read_file", "search", "edit_file", "run_tests"]))
        reordered = extract_features(_traj(["search", "search", "read_file", "edit_file", "run_tests"]))
        disjoint = extract_features(_traj(["deploy", "monitor", "rollback", "deploy", "health"]))
        assert _cosine(base, reordered) > _cosine(base, disjoint) + 0.2

    def test_v2_realistic_same_agent_stays_similar(self, v2):
        """Realistic same-agent variation (shared tools + content, mild
        sequence drift) must remain a clear PASS-range overall score, so the
        encoding does not introduce false rejects of legitimate agents."""
        a = extract_features(_traj(
            ["search", "read_file", "edit_file", "run_tests"], with_content=True))
        b = extract_features(_traj(
            ["search", "read_file", "edit_file", "read_file", "run_tests"], with_content=True))
        va, vb = features_to_vector(a), features_to_vector(b)
        assert compare_signatures(a, va, b, vb)["overall_score"] > 0.6


# --- Dimension utilization ---------------------------------------------------

class TestDimensionUtilization:
    def test_v2_reaches_dims_dead_under_v1(self, monkeypatch):
        """Indices 100-149 are never written by V1; V2's bigram band (96-175)
        can populate them. Verify at least one such dim becomes nonzero."""
        f = extract_features(_traj(
            ["search", "read_file", "edit_file", "run_tests", "commit", "push", "deploy", "verify"]
        ))
        monkeypatch.setattr(settings, "VECTOR_ENCODING_V2", False)
        v1vec = np.array(features_to_vector(f))
        monkeypatch.setattr(settings, "VECTOR_ENCODING_V2", True)
        v2vec = np.array(features_to_vector(f))

        assert np.count_nonzero(v1vec[100:150]) == 0
        assert np.count_nonzero(v2vec[100:150]) > 0


# --- Invariants under both encodings ----------------------------------------

@pytest.mark.parametrize("flag", [False, True])
class TestInvariants:
    def _set(self, monkeypatch, flag):
        monkeypatch.setattr(settings, "VECTOR_ENCODING_V2", flag)

    def test_dimension_and_norm(self, monkeypatch, flag):
        self._set(monkeypatch, flag)
        f = extract_features(_traj(["search", "read_file", "edit_file"], with_content=True))
        vec = features_to_vector(f)
        assert len(vec) == 256
        assert np.linalg.norm(vec) == pytest.approx(1.0, abs=1e-6)

    def test_identical_is_one(self, monkeypatch, flag):
        self._set(monkeypatch, flag)
        f = extract_features(_traj(["search", "read_file", "edit_file"], with_content=True))
        v = features_to_vector(f)
        assert compare_signatures(f, v, f, v)["overall_score"] == pytest.approx(1.0, abs=1e-6)

    def test_symmetry(self, monkeypatch, flag):
        self._set(monkeypatch, flag)
        fa = extract_features(_traj(["search", "read_file", "edit_file"], with_content=True))
        fb = extract_features(_traj(["deploy", "monitor", "rollback"], with_content=True))
        va, vb = features_to_vector(fa), features_to_vector(fb)
        ab = compare_signatures(fa, va, fb, vb)["overall_score"]
        ba = compare_signatures(fb, vb, fa, va)["overall_score"]
        assert ab == pytest.approx(ba, abs=1e-9)

    def test_score_in_range(self, monkeypatch, flag):
        self._set(monkeypatch, flag)
        fa = extract_features(_traj(["a", "b", "c"]))
        fb = extract_features(_traj(["x", "y", "z"]))
        va, vb = features_to_vector(fa), features_to_vector(fb)
        s = compare_signatures(fa, va, fb, vb)["overall_score"]
        assert 0.0 <= s <= 1.0


# --- Empty / degenerate inputs ----------------------------------------------

class TestEmptyInputs:
    @pytest.mark.parametrize("flag", [False, True])
    def test_empty_features_zero_vector(self, monkeypatch, flag):
        monkeypatch.setattr(settings, "VECTOR_ENCODING_V2", flag)
        vec = features_to_vector({})
        assert len(vec) == 256
        assert all(x == 0.0 for x in vec)
