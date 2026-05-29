import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useScrollScene } from '../hooks/useScrollScene';
import DocsNav from '../components/DocsNav';
import GlobeCanvas from '../components/GlobeCanvas';
import PixelDivider from '../components/PixelDivider';
import PixelShield from '../components/PixelShield';
import PixelKeyTheft from '../components/docs/PixelKeyTheft';
import PixelLayerStack from '../components/docs/PixelLayerStack';
import PixelSignatureViz from '../components/docs/PixelSignatureViz';
import PixelDataFlow from '../components/docs/PixelDataFlow';
import PixelCompetitorGrid from '../components/docs/PixelCompetitorGrid';
import PixelTimeline from '../components/docs/PixelTimeline';

function Fade({ progress, delay = 0, children }: { progress: number; delay?: number; children: React.ReactNode }) {
  const p = Math.max(0, Math.min(1, (progress - delay) * 3));
  return (
    <div style={{ opacity: p, transform: `translateY(${(1 - p) * 15}px)`, transition: 'opacity 0.1s, transform 0.1s' }}>
      {children}
    </div>
  );
}

export default function DocsPage() {
  const { activeSection, sectionProgress, scrollToSection, containerRef, setSectionRef } = useScrollScene();

  return (
    <div ref={containerRef} className="h-screen overflow-y-auto overflow-x-hidden" style={{ scrollSnapType: 'y proximity' }}>
      {/* scanlines */}
      <div className="fixed inset-0 pointer-events-none z-50"
        style={{ background: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.06) 0 1px, transparent 1px 3px)', mixBlendMode: 'multiply' }} />

      <DocsNav activeSection={activeSection} onNavigate={scrollToSection} />

      {/* ========== SCENE 0: TITLE ========== */}
      <section ref={setSectionRef(0)} className="h-screen flex items-center justify-center snap-start relative">
        <div className="flex flex-col items-center text-center">
          <div className="mb-8" style={{ filter: 'drop-shadow(0 0 40px rgba(217,119,87,0.15))' }}>
            <GlobeCanvas size={360} />
          </div>
          <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-3">// RESEARCH THESIS</p>
          <h1 className="font-[Silkscreen] text-coral text-4xl leading-tight mb-4" style={{ textShadow: '0 0 30px rgba(217,119,87,0.3)' }}>
            WORLD OF AGENTS
          </h1>
          <p className="font-[Silkscreen] text-dim text-[12px] tracking-[0.14em] mb-12">THE MISSING IDENTITY LAYER FOR AI AGENTS</p>
          <div className="animate-bounce text-dim text-[10px] tracking-[0.2em] font-[Silkscreen]">
            SCROLL TO BEGIN<br />
            <span className="text-coral">▼</span>
          </div>
        </div>
      </section>

      <PixelDivider direction="right" />

      {/* ========== SCENE 1: THE PROBLEM ========== */}
      <section ref={setSectionRef(1)} className="min-h-screen snap-start py-20">
        <div className="max-w-[1100px] mx-auto px-8">
          <Fade progress={sectionProgress.get(1) ?? 0}>
            <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-3">// 01 — THE PROBLEM</p>
            <h2 className="font-[Silkscreen] text-ink text-2xl mb-10">AGENTS HAVE NO IDENTITY</h2>
          </Fade>

          <div className="grid grid-cols-2 gap-16 items-start">
            <div className="space-y-6">
              <Fade progress={sectionProgress.get(1) ?? 0} delay={0.1}>
                <p className="text-[13px] text-muted leading-relaxed">
                  AI agents are autonomous software programs that act on behalf of humans — they write code, deploy infrastructure,
                  send emails, query databases, and interact with APIs. Every single one has an identity problem.
                </p>
              </Fade>

              <Fade progress={sectionProgress.get(1) ?? 0} delay={0.15}>
                <div className="border-l-2 border-coral pl-4 py-2">
                  <p className="text-[11px] text-coral tracking-[0.1em] mb-1">OPTION A: NO IDENTITY</p>
                  <p className="text-[12px] text-muted leading-relaxed">
                    The agent operates with no authentication, relying on the assumption that it's running in a trusted environment.
                  </p>
                </div>
              </Fade>

              <Fade progress={sectionProgress.get(1) ?? 0} delay={0.2}>
                <div className="border-l-2 border-red pl-4 py-2">
                  <p className="text-[11px] text-red tracking-[0.1em] mb-1">OPTION B: STOLEN IDENTITY</p>
                  <p className="text-[12px] text-muted leading-relaxed">
                    A developer copies their personal OAuth token into the agent's environment variables. The agent now has full,
                    indistinguishable access to everything the human can do.
                  </p>
                </div>
              </Fade>

              <Fade progress={sectionProgress.get(1) ?? 0} delay={0.25}>
                <p className="font-[Silkscreen] text-[10px] text-peach tracking-[0.14em] mt-6 mb-3">THREE UNANSWERABLE QUESTIONS</p>
                <div className="space-y-2">
                  {[
                    '"Which human is responsible for this action?"',
                    '"Is this the same agent that was authorized?"',
                    '"Is this agent behaving normally?"',
                  ].map((q, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <span className="text-coral font-[Silkscreen] text-[10px] mt-0.5">{String(i + 1).padStart(2, '0')}</span>
                      <p className="text-[12px] text-peach leading-relaxed">{q}</p>
                    </div>
                  ))}
                </div>
              </Fade>

              <Fade progress={sectionProgress.get(1) ?? 0} delay={0.3}>
                <p className="font-[Silkscreen] text-[10px] text-peach tracking-[0.14em] mt-6 mb-3">WHY NOW</p>
                <div className="space-y-2">
                  {[
                    { dot: 'bg-coral', text: 'MCP and agent-to-agent protocols are exploding with no agreed identity story.' },
                    { dot: 'bg-amber', text: 'Enterprise adoption is accelerating — each agent credential is a liability.' },
                    { dot: 'bg-green', text: 'NIST, IETF, and CSA are building standards. The window to influence them is now.' },
                  ].map((item, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <div className={`w-1.5 h-1.5 ${item.dot} mt-1.5 shrink-0`} />
                      <p className="text-[12px] text-muted leading-relaxed">{item.text}</p>
                    </div>
                  ))}
                </div>
              </Fade>
            </div>

            <Fade progress={sectionProgress.get(1) ?? 0} delay={0.1}>
              <div className="flex justify-center sticky top-[25vh]">
                <PixelKeyTheft active={Math.abs(activeSection - 1) <= 1} />
              </div>
            </Fade>
          </div>
        </div>
      </section>

      <PixelDivider direction="left" />

      {/* ========== SCENE 2: THE INSIGHT ========== */}
      <section ref={setSectionRef(2)} className="min-h-screen snap-start py-20">
        <div className="max-w-[1100px] mx-auto px-8">
          <Fade progress={sectionProgress.get(2) ?? 0}>
            <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-3">// 02 — THE INSIGHT</p>
            <h2 className="font-[Silkscreen] text-ink text-2xl mb-10">FOUR LAYERS, TWO ARE MISSING</h2>
          </Fade>

          <div className="grid grid-cols-2 gap-16 items-start">
            <Fade progress={sectionProgress.get(2) ?? 0} delay={0.1}>
              <div className="flex justify-center">
                <PixelLayerStack active={Math.abs(activeSection - 2) <= 1} progress={sectionProgress.get(2) ?? 0} />
              </div>
            </Fade>

            <div className="space-y-6">
              <Fade progress={sectionProgress.get(2) ?? 0} delay={0.15}>
                <div className="grid grid-cols-1 gap-px bg-paper3 border border-paper3">
                  {[
                    { label: 'HUMAN IDENTITY', desc: 'Okta, Google, Azure AD', status: 'EXISTS', color: 'text-green' },
                    { label: 'BINDING', desc: 'Provable link: human ↔ agent', status: 'NEW', color: 'text-coral' },
                    { label: 'AGENT RUNTIME', desc: 'Crypto key + behavioral signature', status: 'NEW', color: 'text-coral' },
                    { label: 'AUTHORIZATION', desc: 'OAuth 2.0 / OIDC / RFC 8693', status: 'EXISTS', color: 'text-green' },
                  ].map((l, i) => (
                    <div key={i} className="bg-paper px-4 py-3 flex justify-between items-center">
                      <div>
                        <p className="text-[11px] text-ink font-bold">{l.label}</p>
                        <p className="text-[10px] text-dim mt-0.5">{l.desc}</p>
                      </div>
                      <span className={`text-[9px] tracking-[0.14em] font-bold ${l.color}`}>{l.status}</span>
                    </div>
                  ))}
                </div>
              </Fade>

              <Fade progress={sectionProgress.get(2) ?? 0} delay={0.25}>
                <p className="font-[Silkscreen] text-[10px] text-peach tracking-[0.14em] mb-2">DELEGATION, NOT IMPERSONATION</p>
                <p className="text-[12px] text-muted leading-relaxed mb-4">
                  The agent does not get its own credentials. It gets the <span className="text-peach">human's credentials, with attribution.</span> The
                  resulting JWT carries an <code className="text-coral bg-paper3 px-1 text-[10px]">act.sub</code> claim — the downstream system
                  sees Alice as the principal, with the agent as the declared actor.
                </p>
                <div className="border border-paper3 bg-paper2 p-4">
                  <p className="text-[9px] text-dim tracking-[0.14em] mb-2">JWT PAYLOAD</p>
                  <pre className="text-[11px] text-ink font-mono leading-relaxed">{`{
  "iss": "worldofagents",
  "sub": "alice@company.com",
  "act": { "sub": "agt_xyz" },
  "similarity_score": 0.94
}`}</pre>
                </div>
              </Fade>
            </div>
          </div>
        </div>
      </section>

      <PixelDivider direction="right" />

      {/* ========== SCENE 3: BEHAVIORAL SIGNATURES ========== */}
      <section ref={setSectionRef(3)} className="min-h-screen snap-start py-20">
        <div className="max-w-[1100px] mx-auto px-8">
          <Fade progress={sectionProgress.get(3) ?? 0}>
            <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-3">// 03 — CORE IP</p>
            <h2 className="font-[Silkscreen] text-ink text-2xl mb-4">BEHAVIORAL SIGNATURES</h2>
            <p className="text-[13px] text-muted leading-relaxed max-w-2xl mb-10">
              Every AI agent has a behavioral fingerprint. A coding agent calls search, read_file, edit_file in predictable patterns.
              These patterns are as distinctive as a human's keystroke dynamics.
            </p>
          </Fade>

          <div className="grid grid-cols-5 gap-8 items-start">
            <div className="col-span-3 space-y-4">
              <Fade progress={sectionProgress.get(3) ?? 0} delay={0.1}>
                <FeatureCards />
              </Fade>

              <Fade progress={sectionProgress.get(3) ?? 0} delay={0.3}>
                <p className="font-[Silkscreen] text-[10px] text-peach tracking-[0.14em] mt-8 mb-3">COMPARISON ENSEMBLE</p>
                <div className="border border-paper3 bg-paper/60 overflow-hidden">
                  <table className="w-full text-[11px]">
                    <thead><tr className="border-b border-paper3 bg-paper2/50">
                      <th className="px-3 py-2 text-left text-[9px] text-dim tracking-[0.14em]">METRIC</th>
                      <th className="px-3 py-2 text-left text-[9px] text-dim tracking-[0.14em]">WEIGHT</th>
                      <th className="px-3 py-2 text-left text-[9px] text-dim tracking-[0.14em]">METHOD</th>
                    </tr></thead>
                    <tbody className="divide-y divide-paper3/50">
                      {[
                        ['Tool Distribution', '25%', 'Jensen-Shannon divergence'],
                        ['Feature Vector', '30%', 'Cosine similarity (256-dim)'],
                        ['Sequence Pattern', '25%', 'Per-state JSD on transitions'],
                        ['Statistical Profile', '20%', 'Response length + vocabulary'],
                      ].map(([m, w, method], i) => (
                        <tr key={i}><td className="px-3 py-2 text-ink">{m}</td><td className="px-3 py-2 text-coral font-mono">{w}</td><td className="px-3 py-2 text-dim">{method}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Fade>

              <Fade progress={sectionProgress.get(3) ?? 0} delay={0.35}>
                <p className="font-[Silkscreen] text-[10px] text-peach tracking-[0.14em] mt-8 mb-3">ACADEMIC BACKING</p>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { title: 'LLMmap', venue: 'USENIX Security 2025', stat: '>95% accuracy across 42 LLM versions' },
                    { title: 'GitHub Fingerprinting', venue: 'arXiv Jan 2026', stat: '97.2% F1 identifying 5 coding agents' },
                    { title: 'Stylometric Ensemble', venue: '2025', stat: '0.9988 precision, 0.0004 FPR' },
                  ].map((r, i) => (
                    <div key={i} className="border border-paper3 bg-paper/60 p-3">
                      <p className="text-[11px] text-coral font-bold">{r.title}</p>
                      <p className="text-[9px] text-dim mt-0.5">{r.venue}</p>
                      <p className="text-[10px] text-muted mt-1">{r.stat}</p>
                    </div>
                  ))}
                </div>
              </Fade>

              <Fade progress={sectionProgress.get(3) ?? 0} delay={0.4}>
                <div className="border-l-2 border-amber pl-4 py-2 mt-6">
                  <p className="text-[11px] text-amber tracking-[0.1em] mb-1">HONEST ASSESSMENT</p>
                  <p className="text-[12px] text-muted leading-relaxed">
                    Behavioral signatures are <span className="text-peach">anomaly detection, not authentication.</span> The cryptographic
                    hardness is in the agent key and the IdP-issued token. We will never claim otherwise.
                  </p>
                </div>
              </Fade>
            </div>

            <div className="col-span-2 sticky top-[15vh]">
              <Fade progress={sectionProgress.get(3) ?? 0} delay={0.1}>
                <PixelSignatureViz active={Math.abs(activeSection - 3) <= 1} />
              </Fade>
            </div>
          </div>
        </div>
      </section>

      <PixelDivider direction="left" />

      {/* ========== SCENE 4: ARCHITECTURE ========== */}
      <section ref={setSectionRef(4)} className="min-h-screen snap-start py-20">
        <div className="max-w-[1100px] mx-auto px-8">
          <Fade progress={sectionProgress.get(4) ?? 0}>
            <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-3">// 04 — ARCHITECTURE</p>
            <h2 className="font-[Silkscreen] text-ink text-2xl mb-10">HOW IT'S BUILT</h2>
          </Fade>

          <Fade progress={sectionProgress.get(4) ?? 0} delay={0.1}>
            <div className="flex justify-center mb-10">
              <PixelDataFlow active={Math.abs(activeSection - 4) <= 1} />
            </div>
          </Fade>

          <div className="grid grid-cols-2 gap-8">
            <Fade progress={sectionProgress.get(4) ?? 0} delay={0.15}>
              <div className="border border-paper3 bg-paper/60 p-5">
                <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.14em] mb-4">REGISTRATION FLOW</p>
                <div className="space-y-2">
                  {['Human authenticates via Clerk', 'Submits agent name + sample trajectory', 'System computes behavioral signature', 'Cryptographic agent key generated (bcrypt)', 'Key returned once — never stored in plaintext'].map((s, i) => (
                    <div key={i} className="flex gap-3"><span className="text-coral font-[Silkscreen] text-[9px]">{i + 1}.</span><span className="text-[12px] text-muted">{s}</span></div>
                  ))}
                </div>
              </div>
            </Fade>

            <Fade progress={sectionProgress.get(4) ?? 0} delay={0.2}>
              <div className="border border-paper3 bg-paper/60 p-5">
                <p className="font-[Silkscreen] text-[10px] text-green tracking-[0.14em] mb-4">VERIFICATION FLOW</p>
                <div className="space-y-2">
                  {['Agent presents agent_id + agent_key + trajectory', 'Cryptographic check: key matches bcrypt hash', 'Behavioral check: trajectory vs stored signature', 'If both pass → RS256 JWT issued with act.sub claim'].map((s, i) => (
                    <div key={i} className="flex gap-3"><span className="text-green font-[Silkscreen] text-[9px]">{i + 1}.</span><span className="text-[12px] text-muted">{s}</span></div>
                  ))}
                </div>
              </div>
            </Fade>
          </div>

          <Fade progress={sectionProgress.get(4) ?? 0} delay={0.25}>
            <p className="font-[Silkscreen] text-[10px] text-peach tracking-[0.14em] mt-10 mb-4">API ENDPOINTS</p>
            <div className="grid grid-cols-2 gap-4">
              <div className="border border-paper3 bg-paper/60 p-4">
                <p className="text-[10px] text-coral tracking-[0.12em] mb-3">AUTHENTICATED (CLERK)</p>
                {['/agents/register → POST', '/agents → GET', '/agents/{id} → GET', '/agents/{id} → DELETE', '/agents/{id}/refine → POST', '/agents/{id}/rotate-key → POST'].map((e, i) => (
                  <p key={i} className="text-[10px] font-mono text-dim py-0.5">{e}</p>
                ))}
              </div>
              <div className="border border-paper3 bg-paper/60 p-4">
                <p className="text-[10px] text-green tracking-[0.12em] mb-3">OPEN (NO AUTH)</p>
                {['/verify → POST', '/compare → POST', '/agents/{id}/public → GET', '/.well-known/jwks.json → GET', '/health → GET'].map((e, i) => (
                  <p key={i} className="text-[10px] font-mono text-dim py-0.5">{e}</p>
                ))}
              </div>
            </div>
          </Fade>
        </div>
      </section>

      <PixelDivider direction="right" />

      {/* ========== SCENE 5: SECURITY ========== */}
      <section ref={setSectionRef(5)} className="min-h-screen snap-start py-20">
        <div className="max-w-[1100px] mx-auto px-8">
          <Fade progress={sectionProgress.get(5) ?? 0}>
            <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-3">// 05 — SECURITY</p>
            <h2 className="font-[Silkscreen] text-ink text-2xl mb-10">THREAT MODEL</h2>
          </Fade>

          <div className="grid grid-cols-2 gap-16 items-start">
            <div>
              <Fade progress={sectionProgress.get(5) ?? 0} delay={0.1}>
                <div className="space-y-3">
                  {[
                    { threat: 'Random attacker without key', defense: 'Agent key (bcrypt, 48-byte random)', strength: 'STRONG', sColor: 'text-green' },
                    { threat: 'Key stolen, behavior unknown', defense: 'Behavioral signature mismatch', strength: 'SOFT', sColor: 'text-amber' },
                    { threat: 'Agent silently swapped', defense: 'Trajectory drift detection', strength: 'SOFT', sColor: 'text-amber' },
                    { threat: 'Human account compromised', defense: 'Clerk deprovisioning → key revocation', strength: 'STRONG', sColor: 'text-green' },
                    { threat: 'Key compromise detected', defense: 'Key rotation (old key invalidated)', strength: 'STRONG', sColor: 'text-green' },
                  ].map((row, i) => (
                    <div key={i} className="border border-paper3 bg-paper/60 p-4 flex justify-between items-start gap-4">
                      <div className="flex-1">
                        <p className="text-[11px] text-red mb-1">{row.threat}</p>
                        <p className="text-[11px] text-muted">{row.defense}</p>
                      </div>
                      <span className={`text-[9px] tracking-[0.14em] font-bold ${row.sColor} shrink-0`}>{row.strength}</span>
                    </div>
                  ))}
                </div>
              </Fade>
            </div>

            <Fade progress={sectionProgress.get(5) ?? 0} delay={0.15}>
              <div className="flex justify-center sticky top-[20vh]">
                <PixelShield width={260} height={260} />
              </div>
            </Fade>
          </div>
        </div>
      </section>

      <PixelDivider direction="left" />

      {/* ========== SCENE 6: COMPETITIVE LANDSCAPE ========== */}
      <section ref={setSectionRef(6)} className="min-h-screen snap-start py-20">
        <div className="max-w-[1100px] mx-auto px-8">
          <Fade progress={sectionProgress.get(6) ?? 0}>
            <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-3">// 06 — LANDSCAPE</p>
            <h2 className="font-[Silkscreen] text-ink text-2xl mb-10">COMPETITIVE LANDSCAPE</h2>
          </Fade>

          <div className="grid grid-cols-2 gap-16 items-start">
            <div className="space-y-6">
              <Fade progress={sectionProgress.get(6) ?? 0} delay={0.1}>
                <p className="font-[Silkscreen] text-[10px] text-amber tracking-[0.14em] mb-3">STANDARDS BODIES</p>
                <div className="space-y-2 text-[12px] text-muted">
                  <p><span className="text-ink">IETF WIMSE</span> — foundational workload identity standard</p>
                  <p><span className="text-ink">NVIDIA AIP</span> — Ed25519 keys, Agent Authentication Tokens</p>
                  <p><span className="text-ink">OIDC-A 1.0</span> — delegation chain validation for LLM agents</p>
                  <p><span className="text-ink">NIST CAISI</span> — AI Agent Interoperability Profile (Q4 2026)</p>
                </div>
              </Fade>

              <Fade progress={sectionProgress.get(6) ?? 0} delay={0.2}>
                <p className="font-[Silkscreen] text-[10px] text-green tracking-[0.14em] mb-3">OPEN SOURCE</p>
                <div className="space-y-2 text-[12px] text-muted">
                  <p><span className="text-ink">ZeroID</span> — RFC 8693 token exchange, Python/TS/Rust. No behavioral verification.</p>
                  <p><span className="text-ink">AIP</span> — Ed25519 per tool call, MCP proxy. Also an IETF draft.</p>
                  <p><span className="text-ink">Microsoft AGT</span> — 7-package governance toolkit. MIT license.</p>
                </div>
              </Fade>

              <Fade progress={sectionProgress.get(6) ?? 0} delay={0.3}>
                <p className="font-[Silkscreen] text-[10px] text-red tracking-[0.14em] mb-3">PLATFORM (VENDOR-LOCKED)</p>
                <div className="space-y-2 text-[12px] text-muted">
                  <p><span className="text-ink">Microsoft Entra Agent ID</span> — most complete, GA March 2026. Microsoft-only.</p>
                  <p><span className="text-ink">Google Vertex AI</span> — agents get IAM principals. Google-only.</p>
                  <p><span className="text-ink">Okta/Auth0</span> — "for AI Agents" GA 2025-2026. Proprietary.</p>
                </div>
              </Fade>

              <Fade progress={sectionProgress.get(6) ?? 0} delay={0.35}>
                <div className="border border-coral/30 bg-coral/5 p-4 mt-4">
                  <p className="text-[12px] text-coral font-bold">No production system implements behavioral verification.</p>
                  <p className="text-[11px] text-muted mt-1">This is the unique contribution of World of Agents.</p>
                </div>
              </Fade>
            </div>

            <Fade progress={sectionProgress.get(6) ?? 0} delay={0.1}>
              <div className="flex justify-center sticky top-[20vh]">
                <PixelCompetitorGrid active={Math.abs(activeSection - 6) <= 1} />
              </div>
            </Fade>
          </div>
        </div>
      </section>

      <PixelDivider direction="right" />

      {/* ========== SCENE 7: ROADMAP + CTA ========== */}
      <section ref={setSectionRef(7)} className="min-h-screen snap-start py-20">
        <div className="max-w-[1100px] mx-auto px-8">
          <Fade progress={sectionProgress.get(7) ?? 0}>
            <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-3">// 07 — ROADMAP</p>
            <h2 className="font-[Silkscreen] text-ink text-2xl mb-6">WHAT'S NEXT</h2>
          </Fade>

          <Fade progress={sectionProgress.get(7) ?? 0} delay={0.1}>
            <div className="flex justify-center mb-10">
              <PixelTimeline active={Math.abs(activeSection - 7) <= 1} />
            </div>
          </Fade>

          <Fade progress={sectionProgress.get(7) ?? 0} delay={0.15}>
            <div className="grid grid-cols-3 gap-4 mb-16">
              {[
                { phase: 'NEXT 90 DAYS', color: 'text-coral', items: ['IP/CIDR posture checking', 'Per-action risk scoring', 'World ID integration', 'Agent versioning + drift alerts'] },
                { phase: '90–180 DAYS', color: 'text-peach', items: ['OIDC login (Okta, Google, Auth0)', 'OAuth 2.0 Token Exchange broker', 'Scope pre-authorization UX', 'Verifier SDK (TypeScript, Python)', 'MCP server reference integration'] },
                { phase: '180–365 DAYS', color: 'text-ink', items: ['Lifecycle webhooks', 'Cross-org delegation', 'A2A reference verifier', 'IETF submission'] },
              ].map((p, i) => (
                <div key={i} className="border border-paper3 bg-paper/60 p-5">
                  <p className={`font-[Silkscreen] text-[10px] ${p.color} tracking-[0.14em] mb-3`}>{p.phase}</p>
                  <div className="space-y-1.5">
                    {p.items.map((item, j) => (
                      <div key={j} className="flex items-start gap-2">
                        <div className="w-1 h-1 bg-paper4 mt-1.5 shrink-0" />
                        <p className="text-[11px] text-muted">{item}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Fade>

          <Fade progress={sectionProgress.get(7) ?? 0} delay={0.25}>
            <div className="text-center py-12">
              <p className="font-[Silkscreen] text-coral text-xl leading-relaxed mb-8" style={{ textShadow: '0 0 20px rgba(217,119,87,0.2)' }}>
                THE MISSING IDENTITY LAYER<br/>FOR AI AGENTS
              </p>
              <p className="text-[13px] text-muted max-w-lg mx-auto mb-10 leading-relaxed">
                We do not reinvent the identity wheel. We finish it.
              </p>
              <div className="flex gap-4 justify-center">
                <Link to="/" className="px-6 py-2.5 bg-coral text-paper text-[11px] font-bold tracking-[0.14em] hover:bg-coral-deep transition-colors"
                  style={{ boxShadow: '0 0 20px rgba(217,119,87,0.25)' }}>
                  ENTER PLATFORM
                </Link>
                <a href="https://github.com/yskew/worldofagents" target="_blank" rel="noopener"
                  className="px-6 py-2.5 border border-paper4 text-[11px] text-muted tracking-[0.14em] hover:border-coral/40 hover:text-peach transition-colors">
                  VIEW ON GITHUB
                </a>
              </div>
            </div>
          </Fade>
        </div>

        <footer className="border-t border-paper3 py-6 mt-12">
          <div className="max-w-[1100px] mx-auto px-8 flex justify-between items-center">
            <span className="text-[10px] text-dim tracking-[0.1em]">WORLD OF AGENTS · v0.1</span>
            <span className="text-[10px] text-dim tracking-[0.1em]">RESEARCH MVP</span>
          </div>
        </footer>
      </section>
    </div>
  );
}


function FeatureCards() {
  const [expanded, setExpanded] = useState<number | null>(null);

  const features = [
    { num: '01', title: 'TOOL CALL HISTOGRAM', short: 'Normalized frequency distribution of tools/actions', detail: 'For a coding agent: {search: 0.2, read_file: 0.3, edit_file: 0.2, run_tests: 0.15, message: 0.15}. Two agents with similar distributions are likely the same type.' },
    { num: '02', title: 'BIGRAM TRANSITIONS', short: 'Markov model of sequential tool-call transitions', detail: '"After calling search, the agent calls read_file 60% of the time and edit_file 40%." Captures behavioral flow, not just which tools — the order matters.' },
    { num: '03', title: 'TRIGRAM TRANSITIONS', short: 'Three-step sequence probabilities', detail: '"After search → read_file, the agent calls edit_file 80% of the time." Captures complex behavioral patterns that bigrams miss.' },
    { num: '04', title: 'RESPONSE LENGTH STATS', short: 'Mean, variance, skewness of message content lengths', detail: 'A verbose agent produces different statistics than a terse one. Consistent across sessions for the same model + prompt combination.' },
    { num: '05', title: 'VOCABULARY STATS', short: 'Token diversity, frequency distribution, type-token ratio', detail: 'Different models and system prompts produce measurably different vocabularies. We track unique count, total count, TTR, and top-20 tokens.' },
    { num: '06', title: 'TIMING STATS', short: 'Inter-action intervals: mean, std, max', detail: 'An agent that takes 2 seconds between actions has a different timing profile than one that takes 30 seconds. Only computed when timestamps are provided.' },
    { num: '07', title: 'STRUCTURAL FEATURES', short: 'Sequence length, action diversity, tool-call ratio, error rate', detail: 'High-level trajectory shape. Captures overall behavioral patterns including how the agent handles errors and retries.' },
  ];

  return (
    <div className="space-y-2">
      {features.map((f, i) => (
        <button key={i} onClick={() => setExpanded(expanded === i ? null : i)} className="w-full text-left border border-paper3 bg-paper/60 p-3 hover:border-paper4 transition-colors">
          <div className="flex items-center gap-3">
            <span className="text-coral font-[Silkscreen] text-[10px]">{f.num}</span>
            <span className="text-[11px] text-ink font-bold flex-1">{f.title}</span>
            <span className="text-[10px] text-dim">{expanded === i ? '−' : '+'}</span>
          </div>
          <p className="text-[10px] text-dim mt-1 ml-8">{f.short}</p>
          {expanded === i && (
            <p className="text-[11px] text-muted mt-2 ml-8 leading-relaxed border-t border-paper3 pt-2">{f.detail}</p>
          )}
        </button>
      ))}
    </div>
  );
}
