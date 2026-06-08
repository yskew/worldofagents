"""Offline evaluation harness for the signature engine (RFC 0003).

Generates a deterministic labeled dataset of trajectory pairs (same-agent vs
different-agent) across several subsets, then scores every pair under the four
flag combinations and reports discrimination metrics (ROC-AUC, EER, mean
separation). This is the powered eval the RFC 0001/0002 deferred their default
flips to.

Deterministic: seeded RNG, so results are reproducible across runs/machines.

Usage:
    docker compose exec api python scripts/eval_signature.py
    docker compose exec api python scripts/eval_signature.py --json   # machine-readable
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from app.config import settings
from app.schemas.agent import TrajectoryStep
from app.services.signature_engine import (
    compare_signatures,
    extract_features,
    features_to_vector,
)

SEED = 1234
SAMPLES_PER_PROFILE = 12
MAX_DIFF_PAIRS = 500  # cap cross-profile pairs for runtime

# Each profile: tool distribution + a small content word bank. Distinct profiles
# model distinct agents; same profile sampled twice models the same agent on two
# occasions (natural run-to-run variation).
PROFILES = {
    "coder": {
        "tools": {"search": 0.25, "read_file": 0.30, "edit_file": 0.20, "run_tests": 0.15, "commit": 0.10},
        "words": "fix bug function test pass file implement refactor".split(),
    },
    "devops": {
        "tools": {"deploy": 0.25, "health_check": 0.20, "monitor": 0.20, "rollback": 0.15, "promote": 0.20},
        "words": "deploy staging production rollback healthy pipeline release".split(),
    },
    "researcher": {
        "tools": {"web_search": 0.40, "read_page": 0.30, "summarize": 0.15, "write_file": 0.15},
        "words": "research source finding evidence summary report analysis".split(),
    },
    "data": {
        "tools": {"query_db": 0.30, "transform": 0.25, "validate": 0.20, "load": 0.15, "profile": 0.10},
        "words": "rows schema pipeline warehouse validate transform load".split(),
    },
    "security": {
        "tools": {"clone": 0.20, "scan_deps": 0.25, "scan_secrets": 0.25, "scan_iac": 0.20, "report": 0.10},
        "words": "vulnerability secret severity scan exposed finding remediate".split(),
    },
}

# Two profiles with the SAME histogram shape but DISJOINT tools — the RFC 0002
# shape-collision case. Kept separate so we can report it on its own.
SHAPE_PROFILES = {
    "shapeA": {"tools": {"a1": 0.40, "a2": 0.30, "a3": 0.20, "a4": 0.10}, "words": []},
    "shapeB": {"tools": {"b1": 0.40, "b2": 0.30, "b3": 0.20, "b4": 0.10}, "words": []},
}


def _sample_tools(profile: dict, n: int, rng: random.Random) -> list[str]:
    names = list(profile["tools"])
    weights = list(profile["tools"].values())
    return rng.choices(names, weights=weights, k=n)


def _make_trajectory(profile: dict, rng: random.Random, length: int, with_content: bool):
    steps = []
    for name in _sample_tools(profile, length, rng):
        steps.append(TrajectoryStep(type="tool_call", name=name))
        if with_content and profile["words"] and rng.random() < 0.4:
            sentence = " ".join(rng.choices(profile["words"], k=rng.randint(4, 10)))
            steps.append(TrajectoryStep(type="message", name="assistant", content=sentence))
    return steps


def _build_subset(profiles: dict, rng: random.Random, length_range, with_content: bool):
    """Return {profile_name: [feature_dict, ...]} for the given config."""
    out = {}
    for pname, profile in profiles.items():
        samples = []
        for _ in range(SAMPLES_PER_PROFILE):
            length = rng.randint(*length_range)
            traj = _make_trajectory(profile, rng, length, with_content)
            f = extract_features(traj)
            samples.append(f)
        out[pname] = samples
    return out


def _pairs(subset: dict, rng: random.Random):
    """Yield (features_a, features_b, label) — label 1 = same agent."""
    same, diff = [], []
    names = list(subset)
    for pname in names:
        for a, b in combinations(range(len(subset[pname])), 2):
            same.append((subset[pname][a], subset[pname][b], 1))
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            for a in subset[names[i]]:
                for b in subset[names[j]]:
                    diff.append((a, b, 0))
    rng.shuffle(diff)
    diff = diff[:MAX_DIFF_PAIRS]
    return same + diff


def _score_pairs(pairs, metric: str) -> tuple[np.ndarray, np.ndarray]:
    """Return (pos_scores, neg_scores) for the given metric under current flags."""
    pos, neg = [], []
    for fa, fb, label in pairs:
        va = features_to_vector(fa)
        vb = features_to_vector(fb)
        result = compare_signatures(fa, va, fb, vb)
        if metric == "overall":
            s = result["overall_score"]
        else:
            s = result["breakdown"].get(metric)
            if s is None:
                continue  # abstained metric — exclude from that metric's curve
        (pos if label == 1 else neg).append(s)
    return np.array(pos, dtype=float), np.array(neg, dtype=float)


def roc_auc(pos: np.ndarray, neg: np.ndarray) -> float:
    """Mann-Whitney U estimate of P(pos > neg). 0.5 = chance, 1.0 = perfect."""
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    allv = np.concatenate([pos, neg])
    order = allv.argsort(kind="mergesort")
    ranks = np.empty(len(allv), dtype=float)
    ranks[order] = np.arange(1, len(allv) + 1)
    # average ranks for ties
    _, inv, counts = np.unique(allv, return_inverse=True, return_counts=True)
    tie_avg = np.zeros(len(counts))
    sums = np.zeros(len(counts))
    np.add.at(sums, inv, ranks)
    tie_avg = sums / counts
    ranks = tie_avg[inv]
    r_pos = ranks[: len(pos)].sum()
    return (r_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def eer(pos: np.ndarray, neg: np.ndarray) -> float:
    """Equal error rate via threshold sweep."""
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    thresholds = np.unique(np.concatenate([pos, neg]))
    best = 1.0
    for t in thresholds:
        far = float(np.mean(neg >= t))   # different agents accepted
        frr = float(np.mean(pos < t))    # same agents rejected
        gap = abs(far - frr)
        if gap < best:
            best = gap
            eer_val = (far + frr) / 2
    return eer_val


CONFIGS = [
    ("V1 baseline", False, False),
    ("RFC0001 only", True, False),
    ("RFC0002 only", False, True),
    ("RFC0001+0002", True, True),
]


def run():
    # Features are flag-independent (extract_features does not read flags), so
    # build the dataset once and reuse it across all four flag configurations.
    subsets = {
        "full": _build_subset(PROFILES, random.Random(SEED), (6, 14), with_content=True),
        "tool_only": _build_subset(PROFILES, random.Random(SEED + 1), (6, 14), with_content=False),
        "short": _build_subset(PROFILES, random.Random(SEED + 2), (3, 5), with_content=False),
        "shape_collision": _build_subset(SHAPE_PROFILES, random.Random(SEED + 3), (6, 14), with_content=False),
    }
    pair_sets = {name: _pairs(sub, random.Random(SEED + 7)) for name, sub in subsets.items()}

    orig_score = settings.SCORE_NORMALIZATION_V2
    orig_vec = settings.VECTOR_ENCODING_V2
    report = {}
    try:
        for label, score_v2, vec_v2 in CONFIGS:
            settings.SCORE_NORMALIZATION_V2 = score_v2
            settings.VECTOR_ENCODING_V2 = vec_v2
            report[label] = {}
            for sub_name, pairs in pair_sets.items():
                pos, neg = _score_pairs(pairs, "overall")
                cpos, cneg = _score_pairs(pairs, "cosine_score")
                report[label][sub_name] = {
                    "n_same": int(len(pos)), "n_diff": int(len(neg)),
                    "auc": round(roc_auc(pos, neg), 4),
                    "eer": round(eer(pos, neg), 4),
                    "separation": round(float(pos.mean() - neg.mean()), 4),
                    "cosine_auc": round(roc_auc(cpos, cneg), 4),
                }
    finally:
        settings.SCORE_NORMALIZATION_V2 = orig_score
        settings.VECTOR_ENCODING_V2 = orig_vec

    return report


def _print_report(report: dict):
    subsets = ["full", "tool_only", "short", "shape_collision"]
    for sub in subsets:
        print(f"\n=== subset: {sub} ===")
        print(f"{'config':<16}{'AUC':>8}{'EER':>8}{'separation':>12}{'cosineAUC':>11}")
        for label in report:
            m = report[label][sub]
            print(f"{label:<16}{m['auc']:>8}{m['eer']:>8}{m['separation']:>12}{m['cosine_auc']:>11}")
    # sample sizes (same across configs)
    any_label = next(iter(report))
    print("\nsample sizes:", {s: (report[any_label][s]["n_same"], report[any_label][s]["n_diff"]) for s in subsets})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()
    rep = run()
    if args.json:
        print(json.dumps(rep, indent=2))
    else:
        _print_report(rep)
