import type { SignalEvent } from '../lib/api';

interface Props {
  events: SignalEvent[];
}

const LABELS: Record<string, { text: string; color: string }> = {
  'behavioral-anomaly': { text: 'BEHAVIORAL ANOMALY', color: 'text-red' },
  'session-revoked': { text: 'SESSION REVOKED', color: 'text-amber' },
};

export default function SignalsFeed({ events }: Props) {
  if (events.length === 0) {
    return (
      <div className="text-[11px] text-dim border border-paper3 p-6 text-center" data-testid="signals-empty">
        no risk signals emitted yet
      </div>
    );
  }
  return (
    <div className="space-y-2" data-testid="signals-feed">
      {events.map((e) => {
        const label = LABELS[e.type] || { text: e.type.toUpperCase(), color: 'text-muted' };
        return (
          <div key={e.jti} className="border border-paper3 p-3">
            <div className="flex items-center justify-between mb-1">
              <span className={`text-[11px] font-bold tracking-[0.12em] ${label.color}`}>{label.text}</span>
              {e.score != null && (
                <span className="text-[10px] text-dim tabular-nums">score {e.score}</span>
              )}
            </div>
            <div className="text-[11px] text-ink">
              {e.agentName || 'agent'} <span className="text-dim">acting for</span> {e.subject}
            </div>
            {e.reason && <div className="text-[10px] text-dim mt-0.5">reason: {e.reason}</div>}
          </div>
        );
      })}
    </div>
  );
}
