import type { TelemetrySummary } from '../lib/api';

interface Props {
  summary: TelemetrySummary;
  source: string;
  ingestedSpans: number;
  mappedSteps: number;
  applied: boolean;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-paper3 p-3">
      <div className="text-[10px] text-dim tracking-[0.12em] mb-1">{label}</div>
      <div className="text-[15px] font-bold text-ink tabular-nums">{value}</div>
    </div>
  );
}

export default function TelemetryPanel({ summary, source, ingestedSpans, mappedSteps, applied }: Props) {
  const tools = Object.entries(summary.tool_histogram).sort((a, b) => b[1] - a[1]);
  const errorPct = (summary.error_rate * 100).toFixed(1);
  const errorColor = summary.error_rate >= 0.3 ? 'text-red' : summary.error_rate > 0 ? 'text-amber' : 'text-green';

  return (
    <div className="space-y-4" data-testid="telemetry-panel">
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-muted tracking-[0.14em]">
          PATTERNS // {source.toUpperCase()}
        </span>
        <span className={`text-[10px] tracking-[0.12em] ${applied ? 'text-green' : 'text-dim'}`}>
          {applied ? 'SIGNATURE ENRICHED' : 'PREVIEW ONLY'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="SPANS IN" value={String(ingestedSpans)} />
        <Stat label="STEPS MAPPED" value={String(mappedSteps)} />
        <Stat label="UNIQUE TOOLS" value={String(summary.unique_tools)} />
        <Stat label="MEAN INTERVAL" value={summary.mean_interval_s != null ? `${summary.mean_interval_s}s` : 'n/a'} />
      </div>

      <div>
        <div className="flex justify-between mb-1">
          <span className="text-[10px] text-muted tracking-[0.12em]">ERROR RATE</span>
          <span className={`text-[11px] font-bold tabular-nums ${errorColor}`}>{errorPct}%</span>
        </div>
        <div className="h-1 bg-paper3 overflow-hidden">
          <div className="h-full bg-red" style={{ width: `${Math.min(summary.error_rate * 100, 100)}%` }} />
        </div>
      </div>

      <div>
        <div className="text-[10px] text-muted tracking-[0.12em] mb-2">TOOL DISTRIBUTION</div>
        {tools.length === 0 && <div className="text-[11px] text-dim">no tool calls in trace</div>}
        <div className="space-y-2">
          {tools.map(([name, freq]) => (
            <div key={name}>
              <div className="flex justify-between mb-1">
                <span className="text-[11px] text-ink">{name}</span>
                <span className="text-[10px] text-dim tabular-nums">{(freq * 100).toFixed(0)}%</span>
              </div>
              <div className="h-1 bg-paper3 overflow-hidden">
                <div className="h-full bg-coral" style={{ width: `${freq * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
