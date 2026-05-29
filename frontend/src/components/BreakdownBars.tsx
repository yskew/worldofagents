import { useEffect, useState } from 'react';

interface Props {
  breakdown: {
    jsd_score: number;
    cosine_score: number;
    markov_score: number;
    stats_score: number;
  };
}

const metrics = [
  { key: 'jsd_score' as const, label: 'TOOL DIST', weight: 0.25 },
  { key: 'cosine_score' as const, label: 'FEATURES', weight: 0.30 },
  { key: 'markov_score' as const, label: 'SEQUENCE', weight: 0.25 },
  { key: 'stats_score' as const, label: 'STATS', weight: 0.20 },
];

export default function BreakdownBars({ breakdown }: Props) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { requestAnimationFrame(() => setMounted(true)); }, []);

  return (
    <div className="space-y-3">
      {metrics.map(m => {
        const val = breakdown[m.key];
        const color = val >= 0.7 ? 'bg-green' : val >= 0.4 ? 'bg-amber' : 'bg-red';
        const glow = val >= 0.7
          ? '0 0 8px rgba(125,204,138,0.3)'
          : val >= 0.4
            ? '0 0 8px rgba(204,170,68,0.3)'
            : '0 0 8px rgba(204,95,95,0.3)';
        return (
          <div key={m.key}>
            <div className="flex justify-between mb-1">
              <span className="text-[10px] text-muted tracking-[0.12em]">{m.label}</span>
              <span className="text-[11px] font-bold text-ink tabular-nums">{(val * 100).toFixed(1)}</span>
            </div>
            <div className="h-1 bg-paper3 overflow-hidden">
              <div
                className={`h-full ${color} transition-all duration-1000 ease-out`}
                style={{
                  width: mounted ? `${val * 100}%` : '0%',
                  boxShadow: glow,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
