import { Link } from 'react-router-dom';
import GlobeCanvas from '../components/GlobeCanvas';
import PixelShield from '../components/PixelShield';
import PixelRobotFight from '../components/PixelRobotFight';
import PixelAstronaut from '../components/PixelAstronaut';
import PixelDivider from '../components/PixelDivider';

interface Props {
  onEnter: () => void;
}

export default function Landing({ onEnter }: Props) {
  return (
    <div className="min-h-screen relative overflow-x-hidden">
      {/* scanlines */}
      <div className="fixed inset-0 pointer-events-none z-50"
        style={{
          background: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.06) 0 1px, transparent 1px 3px)',
          mixBlendMode: 'multiply',
        }}
      />

      {/* hero — same as dashboard */}
      <section className="max-w-[1100px] mx-auto px-8 pt-20 pb-16">
        <div className="flex items-center justify-between">
          <div className="flex-1 max-w-lg">
            <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-4">
              // IDENTITY LAYER FOR AI AGENTS
            </p>
            <h1 className="font-[Silkscreen] text-coral text-4xl leading-tight mb-5"
              style={{ textShadow: '0 0 30px rgba(217,119,87,0.3)' }}>
              WORLD OF<br/>AGENTS
            </h1>
            <p className="text-muted text-sm leading-relaxed max-w-md mb-8">
              Every AI agent acting in the world today does so with either no identity at all,
              or a stolen one. We're building the missing identity layer — open, free, and
              standards-based.
            </p>
            <div className="flex gap-3">
              <button onClick={onEnter}
                className="px-6 py-2.5 bg-coral text-paper text-[11px] font-bold tracking-[0.14em] hover:bg-coral-deep transition-colors"
                style={{ boxShadow: '0 0 20px rgba(217,119,87,0.3)' }}>
                ENTER PLATFORM
              </button>
              <Link to="/docs"
                className="px-6 py-2.5 border border-paper4 text-[11px] text-muted tracking-[0.14em] hover:border-coral/40 hover:text-peach transition-colors">
                READ THESIS
              </Link>
            </div>
          </div>

          <div className="relative" style={{ filter: 'drop-shadow(0 0 40px rgba(217,119,87,0.15))' }}>
            <GlobeCanvas size={340} />
            <div className="absolute inset-0 pointer-events-none"
              style={{ background: 'radial-gradient(circle, rgba(217,119,87,0.08) 0%, transparent 70%)' }} />
          </div>
        </div>
      </section>

      <PixelDivider direction="right" />

      {/* the problem */}
      <section id="thesis" className="max-w-[1100px] mx-auto px-8 py-20">
        <div className="grid grid-cols-2 gap-16 items-center">
          <div>
            <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-3">// THE PROBLEM</p>
            <h2 className="font-[Silkscreen] text-ink text-xl mb-4">AGENTS HAVE<br/>NO IDENTITY</h2>
            <div className="space-y-3 text-[13px] text-muted leading-relaxed">
              <p>
                A developer pastes their OAuth token into an agent's environment variables.
                The agent now has full, indistinguishable access to everything the human can do.
              </p>
              <p>
                No audit trail differentiates human action from agent action.
                No system can answer: <span className="text-peach">"Which human is responsible for this?"</span>
              </p>
              <p>
                Service accounts don't fit — they're static and assume non-autonomous workloads.
                Agents are autonomous and probabilistic.
              </p>
            </div>
          </div>
          <div className="flex justify-center">
            <PixelShield width={220} height={220} />
          </div>
        </div>
      </section>

      <PixelDivider direction="left" />

      {/* the insight */}
      <section className="max-w-[1100px] mx-auto px-8 py-20">
        <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-3">// THE INSIGHT</p>
        <h2 className="font-[Silkscreen] text-ink text-xl mb-8">FOUR LAYERS,<br/>TWO ARE MISSING</h2>

        <div className="grid grid-cols-4 gap-px bg-paper3 border border-paper3 mb-8">
          <LayerCard
            label="HUMAN ID"
            desc="Okta, Google, Azure AD"
            status="EXISTS"
            statusColor="text-green"
          />
          <LayerCard
            label="BINDING"
            desc="Provable link between human and agent"
            status="NEW"
            statusColor="text-coral"
          />
          <LayerCard
            label="AGENT RUNTIME"
            desc="Crypto key, behavioral signature, risk score"
            status="NEW"
            statusColor="text-coral"
          />
          <LayerCard
            label="AUTHORIZATION"
            desc="OAuth 2.0 / OIDC / RFC 8693"
            status="EXISTS"
            statusColor="text-green"
          />
        </div>

        <p className="text-[13px] text-muted leading-relaxed max-w-2xl">
          We don't reinvent human identity. We delegate to it. What we build is the
          <span className="text-peach"> missing two layers</span> that no existing IdP provides:
          a provable binding between a human and their agents, and a runtime identity
          for the agent itself.
        </p>
      </section>

      <PixelDivider direction="right" />

      {/* how it works */}
      <section className="max-w-[1100px] mx-auto px-8 py-20">
        <div className="grid grid-cols-2 gap-16 items-center">
          <div className="flex justify-center">
            <PixelRobotFight width={420} height={160} />
          </div>
          <div>
            <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-3">// HOW IT WORKS</p>
            <h2 className="font-[Silkscreen] text-ink text-xl mb-4">BEHAVIORAL<br/>SIGNATURES</h2>
            <div className="space-y-3 text-[13px] text-muted leading-relaxed">
              <p>
                When you register an agent, we compute a behavioral signature from its trajectory —
                tool-call distributions, sequence patterns, statistical features.
              </p>
              <p>
                At verification time, we compare the agent's current behavior against
                its stored signature using an ensemble of metrics:
              </p>
              <div className="space-y-1.5 mt-3">
                <Metric label="Tool Distribution" desc="Jensen-Shannon divergence" />
                <Metric label="Feature Vectors" desc="Cosine similarity on 256-dim embeddings" />
                <Metric label="Sequence Patterns" desc="Markov chain transition analysis" />
                <Metric label="Statistical Profile" desc="Response length, vocabulary, timing" />
              </div>
            </div>
          </div>
        </div>
      </section>

      <PixelDivider direction="left" />

      {/* the token */}
      <section className="max-w-[1100px] mx-auto px-8 py-20">
        <div className="grid grid-cols-2 gap-16 items-center">
          <div>
            <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-3">// THE TOKEN</p>
            <h2 className="font-[Silkscreen] text-ink text-xl mb-4">DELEGATION,<br/>NOT IMPERSONATION</h2>
            <div className="space-y-3 text-[13px] text-muted leading-relaxed">
              <p>
                The agent does not get its own credentials.
                It gets the <span className="text-peach">human's credentials, with attribution.</span>
              </p>
              <p>
                The resulting JWT carries an <code className="text-coral bg-paper3 px-1.5 py-0.5 text-[11px]">act.sub</code> claim
                — the downstream system sees Alice as the principal,
                with the agent as the declared actor.
              </p>
            </div>

            <div className="mt-6 border border-paper3 bg-paper2 p-4">
              <p className="text-[9px] text-dim tracking-[0.14em] mb-2">JWT PAYLOAD</p>
              <pre className="text-[11px] text-ink font-mono leading-relaxed">
{`{
  "iss": "worldofagents",
  "sub": "alice@company.com",
  "act": { "sub": "agt_xyz" },
  "similarity_score": 0.94,
  "exp": 1717003600
}`}
              </pre>
            </div>
          </div>
          <div className="flex justify-center">
            <PixelAstronaut width={220} height={200} text="" />
          </div>
        </div>
      </section>

      <PixelDivider direction="right" />

      {/* CTA */}
      <section className="max-w-[1100px] mx-auto px-8 py-24 text-center">
        <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-3">// OPEN SOURCE · FREE · STANDARDS-BASED</p>
        <h2 className="font-[Silkscreen] text-ink text-2xl mb-4">
          THE MISSING IDENTITY<br/>LAYER FOR AI AGENTS
        </h2>
        <p className="text-muted text-sm max-w-lg mx-auto mb-8 leading-relaxed">
          We do not reinvent the identity wheel. We finish it.
          Register your first agent and see what your agents are doing in your name.
        </p>
        <button onClick={onEnter}
          className="px-8 py-3 bg-coral text-paper text-[12px] font-bold tracking-[0.14em] hover:bg-coral-deep transition-colors"
          style={{ boxShadow: '0 0 24px rgba(217,119,87,0.3)' }}>
          ENTER PLATFORM
        </button>
      </section>

      {/* footer */}
      <footer className="border-t border-paper3 py-6">
        <div className="max-w-[1100px] mx-auto px-8 flex justify-between items-center">
          <span className="text-[10px] text-dim tracking-[0.1em]">WORLD OF AGENTS · v0.1</span>
          <span className="text-[10px] text-dim tracking-[0.1em]">RESEARCH MVP</span>
        </div>
      </footer>
    </div>
  );
}

function LayerCard({ label, desc, status, statusColor }: {
  label: string; desc: string; status: string; statusColor: string;
}) {
  return (
    <div className="bg-paper p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="font-[Silkscreen] text-[10px] text-ink tracking-[0.1em]">{label}</span>
        <span className={`text-[9px] tracking-[0.14em] font-bold ${statusColor}`}>{status}</span>
      </div>
      <p className="text-[11px] text-dim leading-relaxed">{desc}</p>
    </div>
  );
}

function Metric({ label, desc }: { label: string; desc: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="w-1.5 h-1.5 bg-coral shrink-0" style={{ boxShadow: '0 0 4px rgba(217,119,87,0.4)' }} />
      <span className="text-[12px] text-ink">{label}</span>
      <span className="text-[10px] text-dim">— {desc}</span>
    </div>
  );
}
