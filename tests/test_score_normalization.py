"""RFC 0001 — confidence-aware ensemble score normalization.

These tests pin the legacy (V1) scoring behavior as a characterization snapshot,
then assert the new (V2) abstention behavior and the invariants that must hold
across both regimes (symmetry, range, identical->1.0, impersonation still fails).

The engine reads `settings.SCORE_NORMALIZATION_V2` at call time, so each test
toggles the flag explicitly via monkeypatch rather than relying on the default.
"""
from __future__ import annotations

import pytest

from app.config import settings
from app.schemas.agent import TrajectoryStep
from app.services.signature_engine import (
    compare_signatures,
    extract_features,
    features_to_vector,
)


def _traj(steps: list[tuple[str, str, str | None]]) -> list[TrajectoryStep]:
    return [TrajectoryStep(type=t, name=n, content=c) for t, n, c in steps]


# The five archetypes shipped in scripts/seed.py, inlined so the test is
# independent of seed data drift.
ARCHETYPES = {
    "code-assistant": _traj([
        ("tool_call", "search", None),
        ("tool_call", "read_file", None),
        ("message", "assistant", "I found the relevant file. Let me read the implementation."),
        ("tool_call", "edit_file", None),
        ("message", "assistant", "I've applied the fix to the function. Running tests now."),
        ("tool_call", "run_tests", None),
        ("message", "assistant", "All 14 tests pass. The bug is fixed."),
    ]),
    "devops-deployer": _traj([
        ("action", "deploy", None),
        ("action", "health_check", None),
        ("action", "monitor", None),
        ("message", "system", "Deployment to staging complete. All health checks pass."),
        ("action", "promote_to_prod", None),
        ("message", "system", "Production deployment successful."),
    ]),
    "research-analyst": _traj([
        ("tool_call", "web_search", None),
        ("tool_call", "web_search", None),
        ("tool_call", "read_page", None),
        ("tool_call", "web_search", None),
        ("message", "assistant", "Based on my research across 12 sources, here are the key findings on agent identity protocols."),
        ("tool_call", "write_file", None),
        ("message", "assistant", "Research report saved to report.md."),
    ]),
    "data-pipeline": _traj([
        ("tool_call", "query_database", None),
        ("tool_call", "transform_data", None),
        ("tool_call", "validate_schema", None),
        ("message", "assistant", "Schema validation passed. 4,231 rows processed."),
        ("tool_call", "load_warehouse", None),
        ("message", "assistant", "Data loaded to warehouse. Pipeline complete."),
    ]),
    "security-scanner": _traj([
        ("tool_call", "clone_repo", None),
        ("tool_call", "scan_dependencies", None),
        ("tool_call", "scan_secrets", None),
        ("tool_call", "scan_iac", None),
        ("message", "assistant", "Scan complete. Found 2 high-severity dependency vulnerabilities and 1 exposed API key."),
        ("tool_call", "create_report", None),
    ]),
}


def _sigs():
    out = {}
    for name, traj in ARCHETYPES.items():
        f = extract_features(traj)
        out[name] = (f, features_to_vector(f))
    return out


@pytest.fixture
def v1(monkeypatch):
    monkeypatch.setattr(settings, "SCORE_NORMALIZATION_V2", False)


@pytest.fixture
def v2(monkeypatch):
    monkeypatch.setattr(settings, "SCORE_NORMALIZATION_V2", True)


# --- Characterization: freeze legacy (V1) scores -----------------------------

# Snapshot captured from the current engine with the flag OFF. Any drift here
# while the flag is off is a regression in legacy behavior.
V1_SNAPSHOT = {
    ("code-assistant", "devops-deployer"): 0.4804,
    ("code-assistant", "research-analyst"): 0.5289,
    ("code-assistant", "data-pipeline"): 0.5279,
    ("code-assistant", "security-scanner"): 0.4780,
    ("devops-deployer", "research-analyst"): 0.4516,
    ("devops-deployer", "data-pipeline"): 0.5231,
    ("devops-deployer", "security-scanner"): 0.4733,
    ("research-analyst", "data-pipeline"): 0.4941,
    ("research-analyst", "security-scanner"): 0.4864,
    ("data-pipeline", "security-scanner"): 0.5237,
}


class TestV1Characterization:
    def test_legacy_matrix_unchanged(self, v1):
        sigs = _sigs()
        for (a, b), expected in V1_SNAPSHOT.items():
            fa, va = sigs[a]
            fb, vb = sigs[b]
            got = compare_signatures(fa, va, fb, vb)["overall_score"]
            assert got == pytest.approx(expected, abs=1e-3), f"{a} vs {b}"

    def test_legacy_self_comparison_is_one(self, v1):
        sigs = _sigs()
        for name, (f, v) in sigs.items():
            assert compare_signatures(f, v, f, v)["overall_score"] == pytest.approx(1.0, abs=1e-6)

    def test_legacy_breakdown_has_no_nulls(self, v1):
        """V1 never abstains: every sub-score is a float, no effective_weights key."""
        sigs = _sigs()
        fa, va = sigs["security-scanner"]  # tool-heavy, sparse content
        fb, vb = sigs["data-pipeline"]
        bd = compare_signatures(fa, va, fb, vb)["breakdown"]
        assert all(isinstance(bd[k], float) for k in
                   ("jsd_score", "cosine_score", "markov_score", "stats_score"))


# --- V2 abstention behavior --------------------------------------------------

class TestV2Abstention:
    def test_tool_only_trajectory_abstains_on_stats(self, v2):
        """A trajectory with no message content cannot compute stats -> abstain."""
        tool_only = _traj([
            ("tool_call", "a", None),
            ("tool_call", "b", None),
            ("tool_call", "a", None),
        ])
        f = extract_features(tool_only)
        v = features_to_vector(f)
        bd = compare_signatures(f, v, f, v)["breakdown"]
        assert bd["stats_score"] is None
        assert bd["effective_weights"]["stats"] == 0.0
        # remaining weights renormalize to sum to 1.0
        assert sum(bd["effective_weights"].values()) == pytest.approx(1.0, abs=1e-6)

    def test_single_step_trajectory_abstains_on_markov(self, v2):
        one = _traj([("tool_call", "only", "just one step here")])
        f = extract_features(one)
        v = features_to_vector(f)
        bd = compare_signatures(f, v, f, v)["breakdown"]
        assert bd["markov_score"] is None
        assert bd["effective_weights"]["markov"] == 0.0

    def test_effective_weights_present_in_v2(self, v2):
        sigs = _sigs()
        f, v = sigs["code-assistant"]
        bd = compare_signatures(f, v, f, v)["breakdown"]
        assert "effective_weights" in bd
        assert sum(bd["effective_weights"].values()) == pytest.approx(1.0, abs=1e-6)


# --- Invariants that must hold in BOTH regimes -------------------------------

@pytest.mark.parametrize("flag", [False, True])
class TestInvariants:
    def _set(self, monkeypatch, flag):
        monkeypatch.setattr(settings, "SCORE_NORMALIZATION_V2", flag)

    def test_score_in_unit_range(self, monkeypatch, flag):
        self._set(monkeypatch, flag)
        sigs = _sigs()
        for _, (fa, va) in sigs.items():
            for _, (fb, vb) in sigs.items():
                s = compare_signatures(fa, va, fb, vb)["overall_score"]
                assert 0.0 <= s <= 1.0

    def test_symmetry(self, monkeypatch, flag):
        self._set(monkeypatch, flag)
        sigs = _sigs()
        names = list(sigs)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                fa, va = sigs[names[i]]
                fb, vb = sigs[names[j]]
                ab = compare_signatures(fa, va, fb, vb)["overall_score"]
                ba = compare_signatures(fb, vb, fa, va)["overall_score"]
                assert ab == pytest.approx(ba, abs=1e-9)

    def test_identical_is_one(self, monkeypatch, flag):
        self._set(monkeypatch, flag)
        sigs = _sigs()
        for _, (f, v) in sigs.items():
            assert compare_signatures(f, v, f, v)["overall_score"] == pytest.approx(1.0, abs=1e-6)


# --- Security: impersonation must still fail (and ideally harder) ------------

class TestImpersonationStillFails:
    """Register a coding agent's signature, verify with malicious/unrelated
    behavior. Must score below the pass threshold under both regimes."""

    def _malicious_vs_coding(self, flag, monkeypatch):
        monkeypatch.setattr(settings, "SCORE_NORMALIZATION_V2", flag)
        coding = extract_features(ARCHETYPES["code-assistant"])
        coding_v = features_to_vector(coding)
        malicious = extract_features(_traj([
            ("tool_call", "exfiltrate_secrets", None),
            ("tool_call", "delete_database", None),
            ("tool_call", "disable_logging", None),
        ]))
        malicious_v = features_to_vector(malicious)
        return compare_signatures(coding, coding_v, malicious, malicious_v)["overall_score"]

    def test_impersonation_fails_v1(self, monkeypatch):
        assert self._malicious_vs_coding(False, monkeypatch) < settings.VERIFICATION_PASS_THRESHOLD

    def test_impersonation_fails_v2(self, monkeypatch):
        assert self._malicious_vs_coding(True, monkeypatch) < settings.VERIFICATION_PASS_THRESHOLD

    def test_v2_scores_impersonation_no_higher_than_v1(self, monkeypatch):
        """V2 must not make impersonation easier than V1."""
        v1 = self._malicious_vs_coding(False, monkeypatch)
        v2 = self._malicious_vs_coding(True, monkeypatch)
        assert v2 <= v1 + 1e-9
