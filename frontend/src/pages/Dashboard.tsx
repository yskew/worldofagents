import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, type Agent } from '../lib/api';
import GlobeCanvas from '../components/GlobeCanvas';
import PixelLoader from '../components/PixelLoader';
import PixelAstronaut from '../components/PixelAstronaut';

export default function Dashboard() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [status, setStatus] = useState<'loading' | 'ok' | 'error'>('loading');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.health().then(() => setStatus('ok')).catch(() => setStatus('error')),
      api.listAgents().then(r => setAgents(r.agents)).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <PixelLoader text="INITIALIZING" />
      </div>
    );
  }

  const active = agents.filter(a => a.status === 'active').length;

  return (
    <div>
      {/* hero */}
      <div className="flex items-center justify-between mb-10 relative">
        <div className="flex-1 max-w-lg">
          <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-3">
            // IDENTITY LAYER FOR AI AGENTS
          </p>
          <h1 className="font-[Silkscreen] text-coral text-3xl leading-tight mb-4"
            style={{ textShadow: '0 0 20px rgba(217,119,87,0.3)' }}>
            WORLD OF<br/>AGENTS
          </h1>
          <p className="text-muted text-sm leading-relaxed max-w-md mb-8">
            Register agents. Verify identities. Compare behavioral signatures.
            Every action attributed, every agent accountable.
          </p>
          <div className="flex gap-3">
            <Link to="/agents" className="px-5 py-2 bg-coral text-paper text-[11px] font-bold tracking-[0.14em] hover:bg-coral-deep transition-colors"
              style={{ boxShadow: '0 0 16px rgba(217,119,87,0.25)' }}>
              REGISTER AGENT
            </Link>
            <Link to="/verify" className="px-5 py-2 border border-paper4 text-[11px] text-muted tracking-[0.14em] hover:border-coral/40 hover:text-peach transition-colors">
              VERIFY
            </Link>
          </div>
        </div>

        <div className="relative" style={{ filter: 'drop-shadow(0 0 40px rgba(217,119,87,0.15))' }}>
          <GlobeCanvas size={320} />
          <div className="absolute inset-0 pointer-events-none"
            style={{ background: 'radial-gradient(circle, rgba(217,119,87,0.08) 0%, transparent 70%)' }} />
        </div>
      </div>

      {/* stats strip */}
      <div className="grid grid-cols-4 gap-px bg-paper3 mb-8 border border-paper3">
        <Stat label="TOTAL AGENTS" value={agents.length} />
        <Stat label="ACTIVE" value={active} highlight />
        <Stat label="REVOKED" value={agents.length - active} warn={agents.length - active > 0} />
        <Stat label="SYSTEM"
          value={status === 'ok' ? 'ONLINE' : 'ERROR'}
          highlight={status === 'ok'}
          warn={status === 'error'}
        />
      </div>

      {/* two column grid */}
      <div className="grid grid-cols-5 gap-6">
        <div className="col-span-3 border border-paper3 bg-paper/60">
          <div className="px-5 py-3 border-b border-paper3 flex justify-between items-center">
            <span className="text-[10px] text-muted tracking-[0.14em]">REGISTERED AGENTS</span>
            <Link to="/agents" className="text-[10px] text-coral tracking-[0.1em] hover:text-peach transition-colors">
              VIEW ALL →
            </Link>
          </div>
          {agents.length === 0 ? (
            <div className="px-5 py-8 flex flex-col items-center">
              <PixelAstronaut width={140} height={120} text="NO AGENTS YET" />
              <Link to="/agents" className="text-coral text-[11px] tracking-[0.1em] hover:text-peach mt-3">
                Register your first agent →
              </Link>
            </div>
          ) : (
            <div>
              {agents.slice(0, 6).map((a, i) => (
                <div key={a.agent_id}
                  className={`px-5 py-3 flex items-center justify-between ${i < Math.min(agents.length, 6) - 1 ? 'border-b border-paper3/50' : ''} hover:bg-paper2/50 transition-colors`}>
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 border border-paper4 flex items-center justify-center text-[9px] text-dim">
                      {(i + 1).toString().padStart(2, '0')}
                    </div>
                    <div>
                      <p className="text-sm text-ink">{a.name}</p>
                      <p className="text-[10px] text-dim font-mono mt-0.5">{a.agent_id.slice(0, 16)}…</p>
                    </div>
                  </div>
                  <span className={`text-[9px] tracking-[0.14em] font-bold px-2 py-0.5 border ${
                    a.status === 'active' ? 'text-green border-green/25' : 'text-red border-red/25'
                  }`}>{a.status.toUpperCase()}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="col-span-2 space-y-3">
          <ActionCard to="/agents" title="REGISTER" desc="Bind a new agent to your identity" num="01" />
          <ActionCard to="/verify" title="VERIFY" desc="Authenticate and receive a signed JWT" num="02" />
          <ActionCard to="/compare" title="COMPARE" desc="Analyze behavioral similarity" num="03" />
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, highlight, warn }: {
  label: string; value: string | number; highlight?: boolean; warn?: boolean;
}) {
  const color = warn ? 'text-red' : highlight ? 'text-coral' : 'text-ink';
  return (
    <div className="bg-paper px-5 py-4">
      <p className="text-[9px] text-dim tracking-[0.14em] mb-1">{label}</p>
      <p className={`text-xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function ActionCard({ to, title, desc, num }: {
  to: string; title: string; desc: string; num: string;
}) {
  return (
    <Link to={to}
      className="block border border-paper3 bg-paper/60 p-5 hover:border-coral/30 transition-all group relative overflow-hidden">
      <span className="absolute top-3 right-4 text-[32px] font-bold text-paper3 group-hover:text-paper4 transition-colors font-[Silkscreen]">
        {num}
      </span>
      <p className="font-[Silkscreen] text-[12px] text-coral tracking-[0.14em] mb-2 group-hover:text-peach transition-colors">
        {title}
      </p>
      <p className="text-[11px] text-muted leading-relaxed max-w-[220px]">{desc}</p>
    </Link>
  );
}
