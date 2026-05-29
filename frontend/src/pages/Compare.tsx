import { useState } from 'react';
import { api, type CompareResponse } from '../lib/api';
import ScoreArc from '../components/ScoreArc';
import BreakdownBars from '../components/BreakdownBars';
import Verdict from '../components/Verdict';
import PixelRobotFight from '../components/PixelRobotFight';
import PixelLoader from '../components/PixelLoader';

const EX_A = `[
  {"type":"tool_call","name":"search"},
  {"type":"tool_call","name":"read_file"},
  {"type":"message","name":"assistant","content":"Here is the file content."},
  {"type":"tool_call","name":"write_file"}
]`;

const EX_B = `[
  {"type":"tool_call","name":"search"},
  {"type":"tool_call","name":"read_file"},
  {"type":"message","name":"assistant","content":"Found the relevant data."},
  {"type":"tool_call","name":"write_file"}
]`;

export default function Compare() {
  const [a, setA] = useState(EX_A);
  const [b, setB] = useState(EX_B);
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  const compare = async () => {
    setErr(''); setResult(null); setBusy(true);
    try {
      const res = await api.compare(JSON.parse(a), JSON.parse(b));
      setResult(res);
    } catch (e: any) { setErr(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-1">// BEHAVIORAL ANALYSIS</p>
      <h1 className="font-[Silkscreen] text-ink text-xl mb-1">COMPARE</h1>
      <p className="text-[11px] text-muted mb-6">Analyze behavioral similarity between two agent trajectories. No auth required.</p>

      {/* robot fight hero */}
      <div className="border border-paper3 mb-6 overflow-hidden">
        <PixelRobotFight width={1400} height={120} />
      </div>

      {/* dual editors */}
      <div className="grid grid-cols-2 gap-px bg-paper3 mb-4 border border-paper3">
        <div className="bg-paper p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-muted tracking-[0.14em]">TRAJECTORY A</span>
            <span className="text-[9px] text-green tracking-[0.1em]">● AGENT 1</span>
          </div>
          <textarea value={a} onChange={e => setA(e.target.value)} rows={10}
            className="w-full px-3 py-2 bg-paper2 border border-paper3 text-[11px] font-mono text-ink focus:outline-none focus:border-coral/40 resize-none" />
        </div>
        <div className="bg-paper p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-muted tracking-[0.14em]">TRAJECTORY B</span>
            <span className="text-[9px] text-red tracking-[0.1em]">● AGENT 2</span>
          </div>
          <textarea value={b} onChange={e => setB(e.target.value)} rows={10}
            className="w-full px-3 py-2 bg-paper2 border border-paper3 text-[11px] font-mono text-ink focus:outline-none focus:border-coral/40 resize-none" />
        </div>
      </div>

      {err && <p className="text-[11px] text-red mb-3">{err}</p>}

      <button onClick={compare} disabled={busy}
        className="w-full px-4 py-2.5 bg-coral text-paper text-[11px] font-bold tracking-[0.14em] hover:bg-coral-deep transition-colors disabled:opacity-30 disabled:cursor-not-allowed mb-6"
        style={{ boxShadow: '0 0 12px rgba(217,119,87,0.15)' }}>
        {busy ? 'ANALYZING...' : 'COMPARE TRAJECTORIES'}
      </button>

      {busy && (
        <div className="border border-paper3 bg-paper/60 py-12 flex items-center justify-center">
          <PixelLoader text="COMPARING SIGNATURES" />
        </div>
      )}

      {result && !busy && (
        <div className="border border-paper3 bg-paper/60 p-6">
          <div className="flex items-start gap-8">
            <div className="shrink-0">
              <ScoreArc score={result.similarity_score} size={160} label="similarity" />
            </div>

            <div className="flex-1 space-y-5">
              <div className="flex items-center gap-3">
                <Verdict verdict={result.verdict} />
                <span className="text-[12px] text-muted">
                  {result.verdict === 'pass' && 'These trajectories appear to originate from the same agent.'}
                  {result.verdict === 'warning' && 'Partial behavioral overlap. Some metrics diverge significantly.'}
                  {result.verdict === 'fail' && 'These trajectories appear to originate from different agents.'}
                </span>
              </div>

              <div>
                <p className="text-[10px] text-muted tracking-[0.14em] mb-3">METRIC BREAKDOWN</p>
                <BreakdownBars breakdown={result.breakdown} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
