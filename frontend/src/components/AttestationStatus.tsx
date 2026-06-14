import type { AttestStep } from '../lib/api';

interface Props {
  history: AttestStep[];
}

const STATUS = {
  ok: { text: 'OK', color: 'text-green', bar: 'bg-green' },
  warning: { text: 'WARNING', color: 'text-amber', bar: 'bg-amber' },
  alarm: { text: 'ALARM', color: 'text-red', bar: 'bg-red' },
} as const;

export default function AttestationStatus({ history }: Props) {
  if (history.length === 0) {
    return (
      <div className="text-[11px] text-dim border border-paper3 p-6 text-center" data-testid="attest-idle">
        start a session and feed behavior windows to monitor drift
      </div>
    );
  }
  const current = history[history.length - 1];
  const s = STATUS[current.status];
  return (
    <div className="space-y-4" data-testid="attest-status">
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-muted tracking-[0.14em]">SESSION STATUS</span>
        <span className={`text-[13px] font-bold tracking-[0.14em] ${s.color}`} data-testid="attest-current">{s.text}</span>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <div className="border border-paper3 p-3">
          <div className="text-[10px] text-dim tracking-[0.12em] mb-1">WINDOWS</div>
          <div className="text-[15px] font-bold text-ink tabular-nums">{current.windows}</div>
        </div>
        <div className="border border-paper3 p-3">
          <div className="text-[10px] text-dim tracking-[0.12em] mb-1">CUSUM DRIFT</div>
          <div className={`text-[15px] font-bold tabular-nums ${s.color}`}>{current.cusum.toFixed(2)}</div>
        </div>
        <div className="border border-paper3 p-3">
          <div className="text-[10px] text-dim tracking-[0.12em] mb-1">LAST SIM</div>
          <div className="text-[15px] font-bold text-ink tabular-nums">{(current.window_similarity * 100).toFixed(0)}%</div>
        </div>
      </div>
      <div>
        <div className="text-[10px] text-muted tracking-[0.12em] mb-2">WINDOW TIMELINE</div>
        <div className="flex items-end gap-1 h-16">
          {history.map((h, i) => (
            <div key={i} className="flex-1 bg-paper3 relative" title={`sim ${h.window_similarity}`}>
              <div className={`absolute bottom-0 left-0 right-0 ${STATUS[h.status].bar}`}
                style={{ height: `${Math.max(h.window_similarity * 100, 4)}%` }} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
