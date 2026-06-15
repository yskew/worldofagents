import { useState } from 'react';
import { api, type TelemetryIngestResponse, type TelemetrySource } from '../lib/api';
import TelemetryPanel from '../components/TelemetryPanel';

const SAMPLE = JSON.stringify([
  { name: 'execute_tool search', attributes: { 'gen_ai.tool.name': 'search' }, startTimeUnixNano: 1000000000000, status: { code: 'OK' } },
  { name: 'execute_tool read_file', attributes: { 'gen_ai.tool.name': 'read_file' }, startTimeUnixNano: 2000000000000, status: { code: 'OK' } },
  { name: 'chat', attributes: { 'gen_ai.operation.name': 'chat', 'gen_ai.completion': 'done' }, startTimeUnixNano: 3000000000000, status: { code: 'OK' } },
], null, 2);

const SOURCES: TelemetrySource[] = ['otel', 'langfuse', 'braintrust'];

export default function Telemetry() {
  const [agentId, setAgentId] = useState('');
  const [agentKey, setAgentKey] = useState('');
  const [source, setSource] = useState<TelemetrySource>('otel');
  const [spans, setSpans] = useState(SAMPLE);
  const [apply, setApply] = useState(false);
  const [result, setResult] = useState<TelemetryIngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit() {
    setError(null);
    setResult(null);
    let parsed: unknown[];
    try {
      parsed = JSON.parse(spans);
      if (!Array.isArray(parsed)) throw new Error('spans must be a JSON array');
    } catch (e) {
      setError(`Invalid spans JSON: ${(e as Error).message}`);
      return;
    }
    setLoading(true);
    try {
      const res = await api.ingestTelemetry({ agent_id: agentId, agent_key: agentKey, source, spans: parsed, apply });
      setResult(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-4">
        <div>
          <h1 className="font-[Silkscreen] text-coral text-[18px] tracking-[0.14em]">TELEMETRY</h1>
          <p className="text-[11px] text-muted mt-1">
            Ingest agent traces (OpenTelemetry / Langfuse / Braintrust) to enrich the behavioral signature from real runtime patterns.
          </p>
        </div>
        <input className="w-full bg-paper2 border border-paper3 px-3 py-2 text-[12px] text-ink"
          placeholder="agent id" value={agentId} onChange={e => setAgentId(e.target.value)} />
        <input className="w-full bg-paper2 border border-paper3 px-3 py-2 text-[12px] text-ink"
          placeholder="agent key" value={agentKey} onChange={e => setAgentKey(e.target.value)} />
        <select className="w-full bg-paper2 border border-paper3 px-3 py-2 text-[12px] text-ink"
          value={source} onChange={e => setSource(e.target.value as TelemetrySource)}>
          {SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <textarea className="w-full h-56 bg-paper2 border border-paper3 px-3 py-2 text-[11px] text-ink font-mono"
          value={spans} onChange={e => setSpans(e.target.value)} />
        <label className="flex items-center gap-2 text-[11px] text-muted">
          <input type="checkbox" checked={apply} onChange={e => setApply(e.target.checked)} />
          apply to signature (unchecked = preview only)
        </label>
        <button onClick={submit} disabled={loading}
          className="w-full bg-coral text-paper py-2 text-[11px] font-bold tracking-[0.14em] disabled:opacity-50">
          {loading ? 'INGESTING…' : 'INGEST TELEMETRY'}
        </button>
      </div>

      <div>
        {error && <div className="border border-red/40 text-red text-[11px] p-3">{error}</div>}
        {result && (
          <TelemetryPanel
            summary={result.summary}
            source={result.source}
            ingestedSpans={result.ingested_spans}
            mappedSteps={result.mapped_steps}
            applied={result.applied}
          />
        )}
        {!error && !result && (
          <div className="text-[11px] text-dim border border-paper3 p-6 text-center">
            submit a trace to see the extracted behavioral patterns
          </div>
        )}
      </div>
    </div>
  );
}
