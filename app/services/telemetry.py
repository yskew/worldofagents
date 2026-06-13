"""Telemetry ingestion mappers (RFC 0010).

Maps agent execution traces from the common observability formats into the
engine's TrajectoryStep model, so behavioral signatures can be enriched from
*real* runtime telemetry (true timings, error rates, tool sequences) rather than
hand-submitted trajectories.

Design: OTel-native first (the vendor-neutral wire format), plus thin adapters
for Langfuse and Braintrust, which both also speak OTel. We map to trajectories;
we do not store raw spans — only derived signature features persist.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.agent import TrajectoryStep
from app.services.signature_engine import extract_features

# OTel GenAI operation names that represent a model turn (vs a tool call).
_OTEL_LLM_OPS = {"chat", "generate_content", "text_completion", "embeddings"}


def _ts_from_unix_nano(v) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(v) / 1e9, tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def _ts_from_unix_seconds(v) -> datetime | None:
    try:
        return datetime.fromtimestamp(float(v), tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def _ts_from_iso(v) -> datetime | None:
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None


def _as_text(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, str):
        return v
    return str(v)


def map_otel(spans: list[dict]) -> list[TrajectoryStep]:
    """OpenTelemetry GenAI spans -> trajectory. Tolerant of partial spans."""
    steps: list[TrajectoryStep] = []
    for span in spans:
        attrs = span.get("attributes", {}) or {}
        ts = _ts_from_unix_nano(span.get("startTimeUnixNano") or span.get("start_time_unix_nano"))
        status = (span.get("status") or {}).get("code")
        is_error = str(status).upper() in ("ERROR", "STATUS_CODE_ERROR", "2")

        tool_name = attrs.get("gen_ai.tool.name") or attrs.get("tool.name")
        op = attrs.get("gen_ai.operation.name")
        name = span.get("name", "")

        if tool_name or name.startswith("execute_tool"):
            step_type, step_name = "tool_call", tool_name or name.replace("execute_tool", "").strip() or "tool"
            content = None
        elif op in _OTEL_LLM_OPS or name.startswith(("chat", "generate")):
            step_type, step_name = "message", "assistant"
            content = _as_text(attrs.get("gen_ai.completion") or attrs.get("gen_ai.response.content"))
        else:
            # generic span -> action
            step_type, step_name, content = "action", name or "span", None

        steps.append(TrajectoryStep(
            type=step_type, name=step_name, content=content, timestamp=ts,
            metadata={"error": True} if is_error else None,
        ))
    return steps


def map_langfuse(observations: list[dict]) -> list[TrajectoryStep]:
    """Langfuse observations (SPAN/GENERATION/EVENT) -> trajectory."""
    steps: list[TrajectoryStep] = []
    for obs in observations:
        otype = (obs.get("type") or "").upper()
        ts = _ts_from_iso(obs.get("startTime") or obs.get("start_time"))
        is_error = (obs.get("level") or "").upper() == "ERROR"
        name = obs.get("name") or otype.lower()
        if otype == "GENERATION":
            step_type, step_name = "message", "assistant"
            content = _as_text(obs.get("output"))
        else:  # SPAN / EVENT -> tool/action
            step_type, step_name, content = "tool_call", name, None
        steps.append(TrajectoryStep(
            type=step_type, name=step_name, content=content, timestamp=ts,
            metadata={"error": True} if is_error else None,
        ))
    return steps


def map_braintrust(spans: list[dict]) -> list[TrajectoryStep]:
    """Braintrust spans -> trajectory."""
    steps: list[TrajectoryStep] = []
    for span in spans:
        sa = span.get("span_attributes", {}) or {}
        stype = (sa.get("type") or "").lower()
        name = sa.get("name") or span.get("name") or stype or "span"
        metrics = span.get("metrics", {}) or {}
        ts = _ts_from_unix_seconds(metrics.get("start"))
        is_error = bool(span.get("error"))
        if stype in ("llm", "completion"):
            step_type, step_name = "message", "assistant"
            content = _as_text(span.get("output"))
        else:  # tool / function / task
            step_type, step_name, content = "tool_call", name, None
        steps.append(TrajectoryStep(
            type=step_type, name=step_name, content=content, timestamp=ts,
            metadata={"error": True} if is_error else None,
        ))
    return steps


MAPPERS = {"otel": map_otel, "langfuse": map_langfuse, "braintrust": map_braintrust}


def map_spans(source: str, spans: list[dict]) -> list[TrajectoryStep]:
    mapper = MAPPERS.get(source)
    if mapper is None:
        raise ValueError(f"unknown telemetry source: {source}")
    return mapper(spans)


def summarize(trajectory: list[TrajectoryStep]) -> dict:
    """Human/UI-facing pattern summary derived from a mapped trajectory."""
    features = extract_features(trajectory)
    sf = features["structural_features"]
    timing = features.get("timing_stats") or {}
    return {
        "tool_histogram": features["tool_call_histogram"],
        "unique_tools": sf["unique_action_types"],
        "sequence_length": sf["sequence_length"],
        "tool_call_ratio": sf["tool_call_ratio"],
        "error_rate": sf["error_retry_ratio"],
        "mean_interval_s": timing.get("mean_interval_s"),
    }
