import { useState } from 'react';
import { api, type VerifyResponse } from '../lib/api';
import ScoreArc from '../components/ScoreArc';
import BreakdownBars from '../components/BreakdownBars';
import Verdict from '../components/Verdict';
import PixelShield from '../components/PixelShield';
import PixelLoader from '../components/PixelLoader';

const EXAMPLE = `[
  {"type":"tool_call","name":"search"},
  {"type":"tool_call","name":"read_file"},
  {"type":"message","name":"assistant","content":"Here is the result."},
  {"type":"tool_call","name":"write_file"}
]`;

export default function Verify() {
  const [agentId, setAgentId] = useState('');
  const [agentKey, setAgentKey] = useState('');
  const [traj, setTraj] = useState(EXAMPLE);
  const [result, setResult] = useState<VerifyResponse | null>(null);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  const verify = async () => {
    setErr(''); setResult(null); setBusy(true);
    try {
      const res = await api.verify({ agent_id: agentId, agent_key: agentKey, trajectory: JSON.parse(traj) });
      setResult(res);
    } catch (e: any) { setErr(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-1">// IDENTITY VERIFICATION</p>
      <h1 className="font-[Silkscreen] text-ink text-xl mb-6">VERIFY AGENT</h1>

      <div className="grid grid-cols-2 gap-6">
        <div className="border border-paper3 bg-paper/60 p-5 space-y-4">
          <div>
            <label className="block text-[10px] text-muted tracking-[0.12em] mb-1.5">AGENT ID</label>
            <input value={agentId} onChange={e => setAgentId(e.target.value)}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              className="w-full px-3 py-2 bg-paper border border-paper3 text-[12px] font-mono text-ink placeholder:text-dim focus:outline-none focus:border-coral/40" />
          </div>
          <div>
            <label className="block text-[10px] text-muted tracking-[0.12em] mb-1.5">AGENT KEY</label>
            <input value={agentKey} onChange={e => setAgentKey(e.target.value)}
              type="password" placeholder="••••••••••••••••"
              className="w-full px-3 py-2 bg-paper border border-paper3 text-[12px] font-mono text-ink placeholder:text-dim focus:outline-none focus:border-coral/40" />
          </div>
          <div>
            <label className="block text-[10px] text-muted tracking-[0.12em] mb-1.5">TRAJECTORY</label>
            <textarea value={traj} onChange={e => setTraj(e.target.value)} rows={10}
              className="w-full px-3 py-2 bg-paper border border-paper3 text-[11px] font-mono text-ink focus:outline-none focus:border-coral/40 resize-none" />
          </div>
          {err && <p className="text-[11px] text-red">{err}</p>}
          <button onClick={verify} disabled={!agentId || !agentKey || busy}
            className="w-full px-4 py-2.5 bg-coral text-paper text-[11px] font-bold tracking-[0.14em] hover:bg-coral-deep transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            style={{ boxShadow: '0 0 12px rgba(217,119,87,0.15)' }}>
            {busy ? 'VERIFYING...' : 'VERIFY IDENTITY'}
          </button>
        </div>

        <div>
          {busy && (
            <div className="border border-paper3 bg-paper/60 h-full flex items-center justify-center">
              <PixelLoader text="SCANNING IDENTITY" />
            </div>
          )}

          {!result && !busy && (
            <div className="border border-paper3 bg-paper/60 h-full flex items-center justify-center">
              <div className="flex flex-col items-center">
                <PixelShield width={160} height={160} />
                <p className="text-[10px] text-dim tracking-[0.14em] mt-2 font-[Silkscreen]">AWAITING REQUEST</p>
              </div>
            </div>
          )}

          {result && !busy && (
            <div className="space-y-4">
              <div className="border border-paper3 bg-paper/60 p-5">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-[10px] text-muted tracking-[0.14em]">RESULT</span>
                  <Verdict verdict={result.verdict} />
                </div>

                <div className="flex items-center gap-6 mb-6">
                  <ScoreArc score={result.similarity_score} size={130} label="score" />
                  <div className="flex-1">
                    <p className="text-sm text-ink leading-relaxed">
                      {result.verified
                        ? 'Behavioral signature matches registered profile. Agent identity confirmed.'
                        : 'Signature mismatch. The agent may have been modified or replaced.'}
                    </p>
                  </div>
                </div>

                {result.breakdown && <BreakdownBars breakdown={result.breakdown} />}
              </div>

              {result.token && (
                <div className="border border-paper3 bg-paper/60 p-5">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] text-muted tracking-[0.14em]">DELEGATION TOKEN</span>
                    <span className="text-[9px] text-dim tracking-[0.1em]">RS256 · JWT</span>
                  </div>
                  <p className="text-[10px] text-dim mb-3">Contains act.sub claim binding agent to owner identity</p>
                  <div className="bg-paper border border-paper3 p-3 overflow-x-auto">
                    <code className="text-[10px] font-mono text-coral break-all leading-relaxed">{result.token}</code>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
