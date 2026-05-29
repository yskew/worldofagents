import { useEffect, useState } from 'react';
import { api, type Agent, type RegisterResponse } from '../lib/api';
import PixelLoader from '../components/PixelLoader';
import PixelAstronaut from '../components/PixelAstronaut';

const EXAMPLE = `[
  {"type":"tool_call","name":"search"},
  {"type":"tool_call","name":"read_file"},
  {"type":"message","name":"assistant","content":"Here is the result."},
  {"type":"tool_call","name":"write_file"}
]`;

export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [traj, setTraj] = useState(EXAMPLE);
  const [result, setResult] = useState<RegisterResponse | null>(null);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = () => api.listAgents().then(r => setAgents(r.agents)).catch(() => {}).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const register = async () => {
    setErr(''); setBusy(true);
    try {
      const res = await api.registerAgent({ name, description: desc || undefined, sample_trajectory: JSON.parse(traj) });
      setResult(res);
      setOpen(false);
      setName(''); setDesc(''); setTraj(EXAMPLE);
      load();
    } catch (e: any) { setErr(e.message); }
    finally { setBusy(false); }
  };

  if (loading) return <div className="flex items-center justify-center h-[60vh]"><PixelLoader text="LOADING AGENTS" /></div>;

  return (
    <div>
      <div className="flex justify-between items-start mb-6">
        <div>
          <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-1">// AGENT REGISTRY</p>
          <h1 className="font-[Silkscreen] text-ink text-xl">AGENTS</h1>
        </div>
        <button
          onClick={() => { setOpen(!open); setResult(null); }}
          className={`px-4 py-2 text-[11px] font-bold tracking-[0.14em] transition-all ${
            open ? 'border border-paper4 text-muted hover:text-ink' : 'bg-coral text-paper hover:bg-coral-deep'
          }`}
          style={open ? {} : { boxShadow: '0 0 12px rgba(217,119,87,0.2)' }}
        >
          {open ? 'CANCEL' : '+ REGISTER'}
        </button>
      </div>

      {result && (
        <div className="mb-6 border border-coral/30 bg-coral/5 p-5">
          <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-3">// AGENT CREATED</p>
          <div className="space-y-2 text-sm">
            <Row label="ID" value={result.agent_id} mono />
            <Row label="KEY" value={result.agent_key} mono accent />
          </div>
          <p className="text-[10px] text-amber mt-3 tracking-[0.1em]">
            ⚠ SAVE THIS KEY — IT WILL NOT BE SHOWN AGAIN
          </p>
        </div>
      )}

      {open && (
        <div className="mb-6 border border-paper3 bg-paper2/60 p-5 space-y-4">
          <Field label="AGENT NAME" value={name} onChange={setName} placeholder="my-agent" />
          <Field label="DESCRIPTION" value={desc} onChange={setDesc} placeholder="What this agent does..." />
          <div>
            <label className="block text-[10px] text-muted tracking-[0.12em] mb-1.5">SAMPLE TRAJECTORY</label>
            <textarea value={traj} onChange={e => setTraj(e.target.value)} rows={8}
              className="w-full px-3 py-2 bg-paper border border-paper3 text-[11px] font-mono text-ink focus:outline-none focus:border-coral/40 resize-none" />
          </div>
          {err && <p className="text-[11px] text-red">{err}</p>}
          <button onClick={register} disabled={!name || busy}
            className="px-5 py-2 bg-coral text-paper text-[11px] font-bold tracking-[0.14em] hover:bg-coral-deep transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
            {busy ? 'REGISTERING...' : 'REGISTER'}
          </button>
        </div>
      )}

      {agents.length === 0 && !open ? (
        <div className="border border-paper3 bg-paper/60 py-12 flex flex-col items-center">
          <PixelAstronaut width={160} height={140} text="NO AGENTS REGISTERED" />
          <button onClick={() => setOpen(true)} className="mt-4 text-coral text-[11px] tracking-[0.1em] hover:text-peach">
            Register your first agent →
          </button>
        </div>
      ) : agents.length > 0 && (
        <div className="border border-paper3 bg-paper/60 overflow-hidden">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-paper3 bg-paper2/50 text-left">
                <Th>#</Th><Th>NAME</Th><Th>AGENT ID</Th><Th>STATUS</Th><Th>SIGNATURE</Th><Th>CREATED</Th><Th></Th>
              </tr>
            </thead>
            <tbody>
              {agents.map((a, i) => (
                <tr key={a.agent_id} className="border-b border-paper3/40 hover:bg-paper2/40 transition-colors">
                  <td className="px-4 py-3 text-dim">{(i + 1).toString().padStart(2, '0')}</td>
                  <td className="px-4 py-3 text-ink font-bold">{a.name}</td>
                  <td className="px-4 py-3 font-mono text-[11px] text-muted">{a.agent_id.slice(0, 18)}…</td>
                  <td className="px-4 py-3">
                    <span className={`text-[9px] tracking-[0.14em] font-bold px-2 py-0.5 border ${
                      a.status === 'active' ? 'text-green border-green/25' : 'text-red border-red/25'
                    }`}>{a.status.toUpperCase()}</span>
                  </td>
                  <td className="px-4 py-3 text-[11px] text-dim">
                    {a.signature_summary
                      ? `${a.signature_summary.tool_count} tools · ${a.signature_summary.sequence_length} steps`
                      : '—'}
                  </td>
                  <td className="px-4 py-3 text-[11px] text-dim">{new Date(a.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3 text-right">
                    {a.status === 'active' && (
                      <button onClick={async () => {
                        if (!confirm('Revoke this agent?')) return;
                        await api.deleteAgent(a.agent_id);
                        load();
                      }} className="text-[10px] text-red/70 hover:text-red tracking-[0.1em] transition-colors">
                        REVOKE
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Th({ children }: { children?: React.ReactNode }) {
  return <th className="px-4 py-2.5 text-[9px] text-dim tracking-[0.14em] font-normal">{children}</th>;
}

function Field({ label, value, onChange, placeholder }: {
  label: string; value: string; onChange: (v: string) => void; placeholder: string;
}) {
  return (
    <div>
      <label className="block text-[10px] text-muted tracking-[0.12em] mb-1.5">{label}</label>
      <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className="w-full px-3 py-2 bg-paper border border-paper3 text-sm text-ink placeholder:text-dim focus:outline-none focus:border-coral/40" />
    </div>
  );
}

function Row({ label, value, mono, accent }: {
  label: string; value: string; mono?: boolean; accent?: boolean;
}) {
  return (
    <div className="flex gap-3 items-start">
      <span className="text-[10px] text-dim tracking-[0.12em] w-8 shrink-0 pt-0.5">{label}</span>
      <code className={`text-[11px] ${mono ? 'font-mono' : ''} ${accent ? 'text-coral' : 'text-ink'} break-all bg-paper px-2 py-1 border border-paper3 flex-1`}>
        {value}
      </code>
    </div>
  );
}
