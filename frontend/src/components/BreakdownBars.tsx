import { useEffect, useState } from 'react';
import type { ScoreBreakdown } from '../lib/api';

interface Props {
  breakdown: ScoreBreakdown;
}

const metrics = [
  { key: 'jsd_score' as const, weightKey: 'jsd' as const, label: 'TOOL DIST', weight: 0.25 },
  { key: 'cosine_score' as const, weightKey: 'cosine' as const, label: 'FEATURES', weight: 0.30 },
  { key: 'markov_score' as const, weightKey: 'markov' as const, label: 'SEQUENCE', weight: 0.25 },
  { key: 'stats_score' as const, weightKey: 'stats' as const, label: 'STATS', weight: 0.20 },
];

export default function BreakdownBars({ breakdown }: Props) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { requestAnimationFrame(() => setMounted(true)); }, []);

  const weights = breakdown.effective_weights;

  return (
    <div className="space-y-3">
      {metrics.map(m => {
        const val = breakdown[m.key];
        // Prefer the server's effective weight (V2); fall back to the static weight.
        const weight = weights ? weights[m.weightKey] : m.weight;
        const abstained = val === null || val === undefined;

        if (abstained) {
          return (
            <div key={m.key}>
              <div className="flex justify-between mb-1">
                <span className="text-[10px] text-dim tracking-[0.12em]">{m.label}</span>
                <span className="text-[10px] text-dim tracking-[0.12em]">N/A</span>
              </div>
              <div className="h-1 bg-paper3 overflow-hidden opacity-40">
                <div className="h-full w-full bg-paper3" style={{
                  backgroundImage:
                    'repeating-linear-gradient(90deg, transparent 0 3px, rgba(255,255,255,0.08) 3px 6px)',
                }} />
              </div>
            </div>
          );
        }

        const color = val >= 0.7 ? 'bg-green' : val >= 0.4 ? 'bg-amber' : 'bg-red';
        const glow = val >= 0.7
          ? '0 0 8px rgba(125,204,138,0.3)'
          : val >= 0.4
            ? '0 0 8px rgba(204,170,68,0.3)'
            : '0 0 8px rgba(204,95,95,0.3)';
        return (
          <div key={m.key}>
            <div className="flex justify-between mb-1">
              <span className="text-[10px] text-muted tracking-[0.12em]">
                {m.label}
                <span className="text-dim ml-1">{(weight * 100).toFixed(0)}%</span>
              </span>
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
