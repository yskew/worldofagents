import { useState, useCallback } from 'react';
import { api, type AttestStep, type TrajectoryStep } from '../lib/api';
import AttestationStatus from '../components/AttestationStatus';

const SAMPLE_WINDOW = JSON.stringify(
  [
    { type: 'tool_call', name: 'search' },
    { type: 'tool_call', name: 'read_file' },
    { type: 'tool_call', name: 'edit_file' },
  ],
  null,
  2,
);

export default function Attestation() {
  const [agentId, setAgentId] = useState('');
  const [agentKey, setAgentKey] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [window, setWindow] = useState(SAMPLE_WINDOW);
  const [history, setHistory] = useState<AttestStep[]>([]);
  const [error, setError] = useState<string | null>(null);

  const start = useCallback(async () => {
    setError(null);
    setHistory([]);
    try {
      const { session_id } = await api.attestStart(agentId, agentKey);
      setSessionId(session_id);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [agentId, agentKey]);

  const step = useCallback(async () => {
    if (!sessionId) return;
    setError(null);
    let traj: TrajectoryStep[];
    try {
      traj = JSON.parse(window);
    } catch (e) {
      setError(`Invalid window JSON: ${(e as Error).message}`);
      return;
    }
    try {
      const res = await api.attestStep(sessionId, traj);
      setHistory((h) => [...h, res]);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [sessionId, window]);

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-4">
        <div>
          <h1 className="font-[Silkscreen] text-coral text-[18px] tracking-[0.14em]">ATTESTATION</h1>
          <p className="text-[11px] text-muted mt-1">
            Continuous mid-session attestation. Feed behavior windows; CUSUM drift detection flags a model swap or hijack.
          </p>
        </div>
        <input className="w-full bg-paper2 border border-paper3 px-3 py-2 text-[12px] text-ink"
          placeholder="agent id" value={agentId} onChange={(e) => setAgentId(e.target.value)} />
        <input className="w-full bg-paper2 border border-paper3 px-3 py-2 text-[12px] text-ink"
          placeholder="agent key" value={agentKey} onChange={(e) => setAgentKey(e.target.value)} />
        <button onClick={start} disabled={!agentId || !agentKey}
          className="w-full bg-coral text-paper py-2 text-[11px] font-bold tracking-[0.14em] disabled:opacity-50">
          {sessionId ? 'RESTART SESSION' : 'START SESSION'}
        </button>
        {sessionId && (
          <>
            <textarea className="w-full h-40 bg-paper2 border border-paper3 px-3 py-2 text-[11px] text-ink font-mono"
              value={window} onChange={(e) => setWindow(e.target.value)} />
            <button onClick={step}
              className="w-full border border-coral/40 text-coral py-2 text-[11px] font-bold tracking-[0.14em]">
              FEED WINDOW
            </button>
          </>
        )}
      </div>
      <div>
        {error && <div className="border border-red/40 text-red text-[11px] p-3 mb-3">{error}</div>}
        <AttestationStatus history={history} />
      </div>
    </div>
  );
}
