from __future__ import annotations

import math
from collections import Counter, defaultdict

import numpy as np
from scipy.spatial.distance import cosine, jensenshannon

from app.config import settings
from app.schemas.agent import TrajectoryStep

VECTOR_DIM = settings.SIGNATURE_VECTOR_DIM


def extract_features(trajectory: list[TrajectoryStep]) -> dict:
    action_names = [_step_action_name(s) for s in trajectory]
    contents = [s.content for s in trajectory if s.content]
    timestamps = [s.timestamp for s in trajectory if s.timestamp]

    return {
        "tool_call_histogram": _tool_call_histogram(action_names),
        "transition_matrix": _transition_matrix(action_names),
        "trigram_transitions": _trigram_transitions(action_names),
        "response_length_stats": _response_length_stats(contents),
        "vocabulary_stats": _vocabulary_stats(contents),
        "timing_stats": _timing_stats(timestamps),
        "structural_features": _structural_features(trajectory, action_names),
    }


def features_to_vector(features: dict) -> list[float]:
    vec = np.zeros(VECTOR_DIM, dtype=np.float64)

    histogram = features.get("tool_call_histogram", {})
    _fill_sorted_values(vec, 0, 50, histogram)

    bigrams = features.get("transition_matrix", {})
    _fill_transition_values(vec, 50, 100, bigrams)

    trigrams = features.get("trigram_transitions", {})
    _fill_transition_values(vec, 150, 50, trigrams)

    rstats = features.get("response_length_stats", {})
    vec[200] = rstats.get("mean", 0) / 1000.0
    vec[201] = rstats.get("variance", 0) / 1e6
    vec[202] = rstats.get("skewness", 0) / 10.0

    vstats = features.get("vocabulary_stats", {})
    vec[210] = vstats.get("type_token_ratio", 0)
    vec[211] = vstats.get("unique_tokens", 0) / 1000.0
    vec[212] = vstats.get("total_tokens", 0) / 10000.0

    tstats = features.get("timing_stats") or {}
    vec[220] = tstats.get("mean_interval_s", 0) / 100.0
    vec[221] = tstats.get("std_interval_s", 0) / 100.0
    vec[222] = tstats.get("max_interval_s", 0) / 1000.0

    sf = features.get("structural_features", {})
    vec[230] = sf.get("sequence_length", 0) / 100.0
    vec[231] = sf.get("unique_action_types", 0) / 20.0
    vec[232] = sf.get("tool_call_ratio", 0)
    vec[233] = sf.get("error_retry_ratio", 0)

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm

    return vec.tolist()


# Base ensemble weights. Sum to 1.0; the single source of truth for both regimes.
_METRIC_WEIGHTS = {"jsd": 0.25, "cosine": 0.30, "markov": 0.25, "stats": 0.20}
_NEUTRAL_SCORE = 0.5  # legacy (V1) value injected for unmeasurable metrics


def compare_signatures(
    sig_a: dict,
    vec_a: list[float],
    sig_b: dict,
    vec_b: list[float],
) -> dict:
    # Raw metric values. jsd/cosine are always computable; markov/stats may
    # abstain (return None) when the trajectory lacks the structure to measure.
    raw = {
        "jsd": _jsd_score(sig_a, sig_b),
        "cosine": _cosine_score(vec_a, vec_b),
        "markov": _markov_score(sig_a, sig_b),
        "stats": _stats_score(sig_a, sig_b),
    }

    if settings.SCORE_NORMALIZATION_V2:
        overall, breakdown = _aggregate_v2(raw)
    else:
        overall, breakdown = _aggregate_v1(raw)

    pass_threshold = settings.VERIFICATION_PASS_THRESHOLD
    fail_threshold = settings.VERIFICATION_FAIL_THRESHOLD

    if overall >= pass_threshold:
        verdict = "pass"
    elif overall <= fail_threshold:
        verdict = "fail"
    else:
        verdict = "warning"

    return {
        "overall_score": round(overall, 4),
        "breakdown": breakdown,
        "verdict": verdict,
    }


def _aggregate_v1(raw: dict) -> tuple[float, dict]:
    """Legacy behavior: unmeasurable metrics vote a neutral 0.5; fixed weights."""
    scores = {k: (_NEUTRAL_SCORE if v is None else v) for k, v in raw.items()}
    overall = sum(_METRIC_WEIGHTS[k] * scores[k] for k in _METRIC_WEIGHTS)
    breakdown = {
        "jsd_score": round(scores["jsd"], 4),
        "cosine_score": round(scores["cosine"], 4),
        "markov_score": round(scores["markov"], 4),
        "stats_score": round(scores["stats"], 4),
    }
    return overall, breakdown


def _aggregate_v2(raw: dict) -> tuple[float, dict]:
    """RFC 0001: abstaining metrics are excluded and their weight redistributed
    proportionally over the metrics that produced a value."""
    applicable = {k: v for k, v in raw.items() if v is not None}
    total_w = sum(_METRIC_WEIGHTS[k] for k in applicable)

    if total_w > 0:
        overall = sum(_METRIC_WEIGHTS[k] * applicable[k] for k in applicable) / total_w
        effective = {k: (_METRIC_WEIGHTS[k] / total_w if k in applicable else 0.0)
                     for k in _METRIC_WEIGHTS}
    else:
        # No metric was measurable at all; nothing to assert similarity from.
        overall = 0.0
        effective = {k: 0.0 for k in _METRIC_WEIGHTS}

    breakdown = {
        "jsd_score": _round_or_none(raw["jsd"]),
        "cosine_score": _round_or_none(raw["cosine"]),
        "markov_score": _round_or_none(raw["markov"]),
        "stats_score": _round_or_none(raw["stats"]),
        "effective_weights": {k: round(w, 4) for k, w in effective.items()},
    }
    return overall, breakdown


def _round_or_none(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def merge_features(existing: dict, new: dict, existing_weight: float = 0.7) -> dict:
    nw = 1.0 - existing_weight
    merged = {}

    merged["tool_call_histogram"] = _merge_histograms(
        existing.get("tool_call_histogram", {}),
        new.get("tool_call_histogram", {}),
        existing_weight,
        nw,
    )
    merged["transition_matrix"] = _merge_transitions(
        existing.get("transition_matrix", {}),
        new.get("transition_matrix", {}),
        existing_weight,
        nw,
    )
    merged["trigram_transitions"] = _merge_transitions(
        existing.get("trigram_transitions", {}),
        new.get("trigram_transitions", {}),
        existing_weight,
        nw,
    )
    merged["response_length_stats"] = _merge_stats(
        existing.get("response_length_stats", {}),
        new.get("response_length_stats", {}),
        existing_weight,
        nw,
    )
    merged["vocabulary_stats"] = _merge_stats(
        existing.get("vocabulary_stats", {}),
        new.get("vocabulary_stats", {}),
        existing_weight,
        nw,
    )
    merged["timing_stats"] = _merge_stats(
        existing.get("timing_stats") or {},
        new.get("timing_stats") or {},
        existing_weight,
        nw,
    ) or None
    merged["structural_features"] = _merge_stats(
        existing.get("structural_features", {}),
        new.get("structural_features", {}),
        existing_weight,
        nw,
    )

    return merged


# --- Internal helpers ---


def _step_action_name(step: TrajectoryStep) -> str:
    return step.name or step.type


def _tool_call_histogram(names: list[str]) -> dict[str, float]:
    if not names:
        return {}
    counts = Counter(names)
    total = sum(counts.values())
    return {k: v / total for k, v in sorted(counts.items())}


def _transition_matrix(names: list[str]) -> dict[str, dict[str, float]]:
    if len(names) < 2:
        return {}
    transitions: dict[str, Counter] = defaultdict(Counter)
    for a, b in zip(names, names[1:]):
        transitions[a][b] += 1
    result = {}
    for src, counts in sorted(transitions.items()):
        total = sum(counts.values())
        result[src] = {k: v / total for k, v in sorted(counts.items())}
    return result


def _trigram_transitions(names: list[str]) -> dict[str, dict[str, float]]:
    if len(names) < 3:
        return {}
    transitions: dict[str, Counter] = defaultdict(Counter)
    for a, b, c in zip(names, names[1:], names[2:]):
        key = f"{a}|{b}"
        transitions[key][c] += 1
    result = {}
    for src, counts in sorted(transitions.items()):
        total = sum(counts.values())
        result[src] = {k: v / total for k, v in sorted(counts.items())}
    return result


def _response_length_stats(contents: list[str]) -> dict:
    if not contents:
        return {"mean": 0, "variance": 0, "skewness": 0, "count": 0}
    lengths = [len(c) for c in contents]
    arr = np.array(lengths, dtype=np.float64)
    mean = float(np.mean(arr))
    var = float(np.var(arr))
    std = math.sqrt(var) if var > 0 else 0
    skew = float(np.mean(((arr - mean) / std) ** 3)) if std > 0 else 0
    return {"mean": round(mean, 4), "variance": round(var, 4), "skewness": round(skew, 4), "count": len(lengths)}


def _vocabulary_stats(contents: list[str]) -> dict:
    if not contents:
        return {"unique_tokens": 0, "total_tokens": 0, "type_token_ratio": 0, "top_20_tokens": {}}
    all_tokens = []
    for c in contents:
        all_tokens.extend(c.lower().split())
    total = len(all_tokens)
    unique = len(set(all_tokens))
    ttr = unique / total if total > 0 else 0
    top_20 = dict(Counter(all_tokens).most_common(20))
    return {"unique_tokens": unique, "total_tokens": total, "type_token_ratio": round(ttr, 4), "top_20_tokens": top_20}


def _timing_stats(timestamps: list) -> dict | None:
    if len(timestamps) < 2:
        return None
    sorted_ts = sorted(timestamps)
    intervals = [(b - a).total_seconds() for a, b in zip(sorted_ts, sorted_ts[1:])]
    arr = np.array(intervals, dtype=np.float64)
    return {
        "mean_interval_s": round(float(np.mean(arr)), 4),
        "std_interval_s": round(float(np.std(arr)), 4),
        "max_interval_s": round(float(np.max(arr)), 4),
    }


def _structural_features(trajectory: list[TrajectoryStep], names: list[str]) -> dict:
    total = len(trajectory)
    tool_calls = sum(1 for s in trajectory if s.type == "tool_call")
    errors = sum(
        1 for s in trajectory
        if (s.name and any(k in s.name.lower() for k in ("error", "retry")))
        or (s.metadata and s.metadata.get("error"))
    )
    return {
        "sequence_length": total,
        "unique_action_types": len(set(names)),
        "tool_call_ratio": round(tool_calls / total, 4) if total > 0 else 0,
        "error_retry_ratio": round(errors / total, 4) if total > 0 else 0,
    }


def _jsd_score(sig_a: dict, sig_b: dict) -> float:
    hist_a = sig_a.get("tool_call_histogram", {})
    hist_b = sig_b.get("tool_call_histogram", {})
    if not hist_a and not hist_b:
        return 1.0
    all_keys = sorted(set(hist_a) | set(hist_b))
    p = np.array([hist_a.get(k, 0) for k in all_keys], dtype=np.float64)
    q = np.array([hist_b.get(k, 0) for k in all_keys], dtype=np.float64)
    p_sum = p.sum()
    q_sum = q.sum()
    if p_sum > 0:
        p = p / p_sum
    if q_sum > 0:
        q = q / q_sum
    dist = jensenshannon(p, q)
    if np.isnan(dist):
        return 0.0
    return 1.0 - dist


def _cosine_score(vec_a: list[float], vec_b: list[float]) -> float:
    a = np.array(vec_a, dtype=np.float64)
    b = np.array(vec_b, dtype=np.float64)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    dist = cosine(a, b)
    if np.isnan(dist):
        return 0.0
    return 1.0 - dist


def _markov_score(sig_a: dict, sig_b: dict) -> float | None:
    """Per-state JSD over transition matrices. Returns None (abstain) when there
    is no transition structure to compare (e.g. trajectories with < 2 steps)."""
    model = sig_a.get("transition_matrix", {})
    observed = sig_b.get("transition_matrix", {})
    if not model or not observed:
        return None

    all_src = set(model) | set(observed)
    if not all_src:
        return None

    match_score = 0.0
    total_weight = 0.0

    for src in all_src:
        m_probs = model.get(src, {})
        o_probs = observed.get(src, {})

        if not m_probs and not o_probs:
            continue

        if not m_probs or not o_probs:
            total_weight += 1.0
            continue

        all_dest = set(m_probs) | set(o_probs)
        p = np.array([m_probs.get(d, 0) for d in all_dest])
        q = np.array([o_probs.get(d, 0) for d in all_dest])
        p_sum = p.sum()
        q_sum = q.sum()
        if p_sum > 0:
            p = p / p_sum
        if q_sum > 0:
            q = q / q_sum

        dist = jensenshannon(p, q)
        if np.isnan(dist):
            dist = 1.0
        match_score += (1.0 - dist)
        total_weight += 1.0

    if total_weight == 0:
        return None
    return match_score / total_weight


def _stats_score(sig_a: dict, sig_b: dict) -> float | None:
    """Compares response-length and vocabulary profiles. Returns None (abstain)
    when neither is computable (e.g. tool-only trajectories with no content)."""
    scores = []
    rls_a = sig_a.get("response_length_stats", {})
    rls_b = sig_b.get("response_length_stats", {})
    if rls_a.get("count", 0) > 0 and rls_b.get("count", 0) > 0:
        mean_a, mean_b = rls_a["mean"], rls_b["mean"]
        max_mean = max(abs(mean_a), abs(mean_b), 1)
        scores.append(1.0 - min(abs(mean_a - mean_b) / max_mean, 1.0))

    vs_a = sig_a.get("vocabulary_stats", {})
    vs_b = sig_b.get("vocabulary_stats", {})
    if vs_a.get("total_tokens", 0) > 0 and vs_b.get("total_tokens", 0) > 0:
        ttr_diff = abs(vs_a.get("type_token_ratio", 0) - vs_b.get("type_token_ratio", 0))
        scores.append(1.0 - min(ttr_diff, 1.0))

    if not scores:
        return None
    return sum(scores) / len(scores)


def _fill_sorted_values(vec: np.ndarray, start: int, length: int, histogram: dict):
    sorted_items = sorted(histogram.items(), key=lambda x: -x[1])
    for i, (_, v) in enumerate(sorted_items[:length]):
        vec[start + i] = v


def _fill_transition_values(vec: np.ndarray, start: int, length: int, transitions: dict):
    values = []
    for src in sorted(transitions.keys()):
        for dest in sorted(transitions[src].keys()):
            values.append(transitions[src][dest])
    for i, v in enumerate(values[:length]):
        vec[start + i] = v


def _merge_histograms(a: dict, b: dict, wa: float, wb: float) -> dict:
    all_keys = set(a) | set(b)
    merged = {}
    for k in all_keys:
        merged[k] = wa * a.get(k, 0) + wb * b.get(k, 0)
    total = sum(merged.values())
    if total > 0:
        merged = {k: v / total for k, v in sorted(merged.items())}
    return merged


def _merge_transitions(a: dict, b: dict, wa: float, wb: float) -> dict:
    all_src = set(a) | set(b)
    merged = {}
    for src in sorted(all_src):
        da = a.get(src, {})
        db = b.get(src, {})
        merged[src] = _merge_histograms(da, db, wa, wb)
    return merged


def _merge_stats(a: dict, b: dict, wa: float, wb: float) -> dict:
    if not a and not b:
        return {}
    all_keys = set(a) | set(b)
    merged = {}
    for k in all_keys:
        va = a.get(k)
        vb = b.get(k)
        if isinstance(va, dict) or isinstance(vb, dict):
            merged[k] = va or vb
        elif isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            merged[k] = round(wa * va + wb * vb, 4)
        else:
            merged[k] = va if va is not None else vb
    return merged
