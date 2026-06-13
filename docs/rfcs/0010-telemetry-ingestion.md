# RFC 0010 — Telemetry Ingestion (OTel-native + adapters)

- **Status:** Implemented (spike)
- **Area:** `app/services/telemetry.py`, `POST /telemetry/ingest`, frontend Telemetry page
- **Constraint:** Clerk untouched; agent-key authenticated.

---

## 1. Why

Signatures were only ever computed from trajectories **hand-submitted** to
`/verify`, `/compare`, `/register`. The richer, continuous source is the agent's
**runtime telemetry**. Ingesting it:

- **produces the real labeled corpus** every off-by-default feature is blocked on
  (RFC 0004 weights, 0006 calibration, 0008 discriminative probes, learned
  embeddings) — traces are tagged by which agent emitted them,
- **feeds continuous attestation** (a future live-stream consumer),
- **enriches features** the engine already supports but rarely receives: real
  timings, error/retry rates, true tool sequences.

## 2. Design: OTel-native, don't build another observability tool

We map traces → `TrajectoryStep` and reuse the existing signature engine. We do
**not** build a tracing UI or storage; we consume the ecosystem's formats:

- **OpenTelemetry GenAI** is the primary, vendor-neutral wire format.
- **Langfuse** and **Braintrust** adapters map their trace shapes too (both also
  speak OTel, so the adapters are thin).

`app/services/telemetry.py` provides `map_otel` / `map_langfuse` /
`map_braintrust` → trajectory, plus `summarize()` for a UI/pattern view. Mappers
extract tool calls, model turns, **timestamps**, and **error** status from each
format and are tolerant of partial spans.

## 3. Endpoint

`POST /telemetry/ingest` (agent-key auth, so the agent's own runtime can push
without a human session; Clerk untouched):

```
{ agent_id, agent_key, source: otel|langfuse|braintrust, spans: [...], apply: bool }
->
{ source, ingested_spans, mapped_steps, summary: {tool_histogram, error_rate,
  mean_interval_s, unique_tools, sequence_length, tool_call_ratio}, applied }
```

- `apply: false` → map + summarize only (preview), no signature change.
- `apply: true` → merge the derived trajectory into the stored signature
  (exponential-weighted, same as `/refine`).
- Rate-limited (RFC 0007); 503 when `TELEMETRY_ENABLED=false`.

**Privacy:** raw spans are never persisted — only derived signature features.

## 4. Frontend

- `TelemetryPanel` renders the extracted patterns (tool distribution, error
  rate, unique tools, mean interval) in the pixel aesthetic.
- `Telemetry` page: paste a trace (OTel/Langfuse/Braintrust), preview or apply,
  see the patterns. Routed at `/telemetry` with a nav entry.
- `api.ingestTelemetry` client method (agent-key auth, no Clerk token).

## 5. Testing

- **API:** `tests/test_telemetry.py` (10) — all three mappers (tool/message/error
  + timing), summary, unknown source, and the endpoint (apply, preview, bad key
  401, unknown agent 404, empty spans 422).
- **UI:** Vitest + React Testing Library — `TelemetryPanel.test.tsx` (3, renders
  patterns / preview state / empty trace) and `api.test.ts` (2, client posts +
  error handling). Plus `tsc -b` typecheck, `vite build`, and eslint.
- Full backend suite: **209 passed**. Frontend: **5 passed**, build green.

This also stands up the project's first **frontend test harness** (Vitest + RTL),
reusable for every future UI change.

## 6. Next steps

- Pull-mode adapters (poll Langfuse/Braintrust APIs) in addition to push.
- Stream consumer for continuous mid-session attestation.
- Use the accumulated corpus to re-fit and flip RFC 0004 / 0006 / 0008.
- Content redaction/hashing options for stricter privacy modes.
