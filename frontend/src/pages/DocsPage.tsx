import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import * as THREE from 'three';
import DocsNav from '../components/DocsNav';

const SECTIONS = [
  { label: 'TITLE', angle: 0, height: 0.5, radius: 0 },
  { label: 'PROBLEM', angle: 0, height: 0, radius: 8 },
  { label: 'INSIGHT', angle: Math.PI * 0.4, height: -0.3, radius: 8 },
  { label: 'SIGNATURES', angle: Math.PI * 0.8, height: -0.8, radius: 9 },
  { label: 'ARCHITECTURE', angle: Math.PI * 1.2, height: -0.2, radius: 8 },
  { label: 'SECURITY', angle: Math.PI * 1.55, height: 0.3, radius: 8 },
  { label: 'LANDSCAPE', angle: Math.PI * 1.85, height: 0.7, radius: 9 },
  { label: 'ROADMAP', angle: Math.PI * 2.2, height: 1.0, radius: 8 },
];

function getCameraPos(index: number, t: number = 0) {
  const s = SECTIONS[index];
  if (index === 0) {
    return { x: 0, y: 2 + Math.sin(t * 0.3) * 0.1, z: 12, lx: 0, ly: 0, lz: 0 };
  }
  const a = s.angle;
  const r = s.radius;
  const x = Math.sin(a) * r;
  const z = Math.cos(a) * r;
  const y = s.height * 3;
  return { x, y, z, lx: 0, ly: 0, lz: 0 };
}

function lerp(a: number, b: number, t: number) { return a + (b - a) * t; }

function easeInOut(t: number) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }

export default function DocsPage() {
  const mountRef = useRef<HTMLDivElement>(null);
  const [activeSection, setActiveSection] = useState(0);
  const [transitioning, setTransitioning] = useState(false);
  const sceneRef = useRef<{
    camera: THREE.PerspectiveCamera;
    targetIndex: number;
    currentPos: { x: number; y: number; z: number };
    progress: number;
  } | null>(null);

  const navigateTo = (index: number) => {
    if (transitioning || !sceneRef.current) return;
    setTransitioning(true);
    sceneRef.current.targetIndex = index;
    sceneRef.current.progress = 0;
  };

  useEffect(() => {
    const mount = mountRef.current!;
    const w = window.innerWidth;
    const h = window.innerHeight;

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x141210, 0.03);

    const camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 200);
    const initPos = getCameraPos(0, 0);
    camera.position.set(initPos.x, initPos.y, initPos.z);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: false, alpha: false });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setClearColor(0x141210);
    mount.appendChild(renderer.domElement);
    renderer.domElement.style.imageRendering = 'auto';

    const coral = 0xd97757;
    const peach = 0xe89b7d;
    const dim = 0x5e524a;
    const paper3 = 0x312d29;

    // --- central globe (same as GlobeCanvas but in the scene) ---
    const icoGeo = new THREE.IcosahedronGeometry(1.8, 3);
    const icoMat = new THREE.MeshBasicMaterial({ color: coral, wireframe: true, transparent: true, opacity: 0.15 });
    const ico = new THREE.Mesh(icoGeo, icoMat);
    scene.add(ico);

    const innerGeo = new THREE.IcosahedronGeometry(1.5, 2);
    const innerMat = new THREE.PointsMaterial({ color: peach, size: 0.05, transparent: true, opacity: 0.5 });
    scene.add(new THREE.Points(innerGeo, innerMat));

    // orbit rings
    for (let i = 0; i < 5; i++) {
      const r = 2.2 + i * 0.4;
      const ringGeo = new THREE.RingGeometry(r, r + 0.01, 96);
      const ringMat = new THREE.MeshBasicMaterial({ color: dim, transparent: true, opacity: 0.08 - i * 0.012, side: THREE.DoubleSide });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = Math.PI / 2 + (i - 2) * 0.2;
      ring.rotation.z = i * 0.15;
      scene.add(ring);
    }

    // --- floating particles throughout the space ---
    const pCount = 300;
    const pGeo = new THREE.BufferGeometry();
    const pPos = new Float32Array(pCount * 3);
    for (let i = 0; i < pCount; i++) {
      pPos[i * 3] = (Math.random() - 0.5) * 40;
      pPos[i * 3 + 1] = (Math.random() - 0.5) * 20;
      pPos[i * 3 + 2] = (Math.random() - 0.5) * 40;
    }
    pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
    const pMat = new THREE.PointsMaterial({ color: coral, size: 0.03, transparent: true, opacity: 0.3 });
    scene.add(new THREE.Points(pGeo, pMat));

    // --- section markers (glowing cubes at each stop) ---
    const markers: THREE.Mesh[] = [];
    for (let i = 1; i < SECTIONS.length; i++) {
      const s = SECTIONS[i];
      const a = s.angle;
      const markerR = s.radius * 0.6;
      const mx = Math.sin(a) * markerR;
      const mz = Math.cos(a) * markerR;
      const my = s.height * 3;

      const mGeo = new THREE.BoxGeometry(0.15, 0.15, 0.15);
      const mMat = new THREE.MeshBasicMaterial({ color: coral, transparent: true, opacity: 0.4 });
      const marker = new THREE.Mesh(mGeo, mMat);
      marker.position.set(mx, my, mz);
      scene.add(marker);
      markers.push(marker);

      // connection line from marker to center
      const lineGeo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(mx, my, mz),
        new THREE.Vector3(0, 0, 0),
      ]);
      const lineMat = new THREE.LineBasicMaterial({ color: paper3, transparent: true, opacity: 0.1 });
      scene.add(new THREE.Line(lineGeo, lineMat));
    }

    // --- data connector rings between sections ---
    for (let i = 1; i < SECTIONS.length - 1; i++) {
      const s1 = SECTIONS[i];
      const s2 = SECTIONS[i + 1];
      const points: THREE.Vector3[] = [];
      const steps = 20;
      for (let j = 0; j <= steps; j++) {
        const t = j / steps;
        const a = lerp(s1.angle, s2.angle, t);
        const r = lerp(s1.radius, s2.radius, t) * 0.6;
        const y = lerp(s1.height, s2.height, t) * 3;
        points.push(new THREE.Vector3(Math.sin(a) * r, y, Math.cos(a) * r));
      }
      const pathGeo = new THREE.BufferGeometry().setFromPoints(points);
      const pathMat = new THREE.LineBasicMaterial({ color: dim, transparent: true, opacity: 0.06 });
      scene.add(new THREE.Line(pathGeo, pathMat));
    }

    const state = {
      camera,
      targetIndex: 0,
      currentPos: { x: initPos.x, y: initPos.y, z: initPos.z },
      progress: 1,
    };
    sceneRef.current = state;

    let raf: number;
    const animate = () => {
      const t = performance.now() * 0.001;

      ico.rotation.y = t * 0.08;
      ico.rotation.x = Math.sin(t * 0.05) * 0.1;

      // marker pulse
      markers.forEach((m, i) => {
        const scale = 1 + Math.sin(t * 2 + i) * 0.3;
        m.scale.setScalar(scale);
        (m.material as THREE.MeshBasicMaterial).opacity = 0.3 + Math.sin(t * 2 + i) * 0.15;
      });

      // camera transition
      if (state.progress < 1) {
        state.progress = Math.min(1, state.progress + 0.012);
        const ease = easeInOut(state.progress);
        const target = getCameraPos(state.targetIndex, t);
        state.currentPos.x = lerp(camera.position.x, target.x, ease);
        state.currentPos.y = lerp(camera.position.y, target.y, ease);
        state.currentPos.z = lerp(camera.position.z, target.z, ease);
        camera.position.set(state.currentPos.x, state.currentPos.y, state.currentPos.z);
        camera.lookAt(0, 0, 0);

        if (state.progress >= 1) {
          setActiveSection(state.targetIndex);
          setTransitioning(false);
        }
      } else {
        // gentle hover at current position
        const pos = getCameraPos(state.targetIndex, t);
        camera.position.x = pos.x + Math.sin(t * 0.5) * 0.05;
        camera.position.y = pos.y + Math.cos(t * 0.4) * 0.05;
        camera.position.z = pos.z + Math.sin(t * 0.3) * 0.03;
        camera.lookAt(0, 0, 0);
      }

      renderer.render(scene, camera);
      raf = requestAnimationFrame(animate);
    };
    animate();

    const handleResize = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      if (transitioning) return;
      const dir = e.deltaY > 0 ? 1 : -1;
      const next = Math.max(0, Math.min(SECTIONS.length - 1, state.targetIndex + dir));
      if (next !== state.targetIndex) {
        state.targetIndex = next;
        state.progress = 0;
        setTransitioning(true);
      }
    };
    mount.addEventListener('wheel', handleWheel, { passive: false });

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
        e.preventDefault();
        const next = Math.min(SECTIONS.length - 1, state.targetIndex + 1);
        if (next !== state.targetIndex) {
          state.targetIndex = next;
          state.progress = 0;
          setTransitioning(true);
        }
      } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
        e.preventDefault();
        const prev = Math.max(0, state.targetIndex - 1);
        if (prev !== state.targetIndex) {
          state.targetIndex = prev;
          state.progress = 0;
          setTransitioning(true);
        }
      }
    };
    window.addEventListener('keydown', handleKey);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('keydown', handleKey);
      mount.removeEventListener('wheel', handleWheel);
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);

  return (
    <div className="h-screen overflow-hidden relative">
      {/* scanlines */}
      <div className="fixed inset-0 pointer-events-none z-50"
        style={{ background: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.06) 0 1px, transparent 1px 3px)', mixBlendMode: 'multiply' }} />

      {/* Three.js canvas */}
      <div ref={mountRef} className="absolute inset-0" />

      {/* nav */}
      <DocsNav activeSection={activeSection} onNavigate={navigateTo} />

      {/* HTML content overlay */}
      <div className="absolute inset-0 pointer-events-none z-10 flex items-center justify-center">
        <div className="pointer-events-auto max-w-[700px] max-h-[80vh] overflow-y-auto px-6" style={{ scrollbarWidth: 'thin' }}>
          <ContentPanel section={activeSection} />
        </div>
      </div>

      {/* bottom hint */}
      {activeSection === 0 && !transitioning && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20 text-center animate-pulse">
          <p className="text-[10px] text-dim tracking-[0.2em] font-[Silkscreen]">SCROLL OR PRESS ▼ TO EXPLORE</p>
        </div>
      )}
    </div>
  );
}


function ContentPanel({ section }: { section: number }) {
  const [expanded, setExpanded] = useState<number | null>(null);

  const panelClass = "bg-paper/85 backdrop-blur-sm border border-paper3 p-6 space-y-4";

  if (section === 0) return (
    <div className="text-center py-8">
      <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-3">// RESEARCH THESIS</p>
      <h1 className="font-[Silkscreen] text-coral text-4xl leading-tight mb-4" style={{ textShadow: '0 0 30px rgba(217,119,87,0.3)' }}>
        WORLD OF<br/>AGENTS
      </h1>
      <p className="font-[Silkscreen] text-dim text-[11px] tracking-[0.14em] mb-6">THE MISSING IDENTITY LAYER FOR AI AGENTS</p>
      <p className="text-[13px] text-muted leading-relaxed max-w-md mx-auto">
        An interactive journey through the thesis, architecture, and research behind the agent identity platform.
      </p>
    </div>
  );

  if (section === 1) return (
    <div className={panelClass}>
      <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em]">// 01 — THE PROBLEM</p>
      <h2 className="font-[Silkscreen] text-ink text-xl">AGENTS HAVE NO IDENTITY</h2>
      <p className="text-[13px] text-muted leading-relaxed">
        Every AI agent acting in the world today does so with either no identity at all, or a stolen one — typically the personal session token of the human who deployed it.
      </p>
      <div className="border-l-2 border-coral pl-4 py-1">
        <p className="text-[11px] text-coral tracking-[0.1em] mb-1">OPTION A: NO IDENTITY</p>
        <p className="text-[12px] text-muted">The agent operates with no authentication, inheriting the host machine's permissions.</p>
      </div>
      <div className="border-l-2 border-red pl-4 py-1">
        <p className="text-[11px] text-red tracking-[0.1em] mb-1">OPTION B: STOLEN IDENTITY</p>
        <p className="text-[12px] text-muted">A developer copies their OAuth token into the agent's environment. Full, indistinguishable access.</p>
      </div>
      <p className="font-[Silkscreen] text-[10px] text-peach tracking-[0.14em] mt-4">THREE UNANSWERABLE QUESTIONS</p>
      {['"Which human is responsible for this action?"', '"Is this the same agent that was authorized?"', '"Is this agent behaving normally?"'].map((q, i) => (
        <div key={i} className="flex gap-3 items-start">
          <span className="text-coral font-[Silkscreen] text-[10px]">{String(i + 1).padStart(2, '0')}</span>
          <p className="text-[12px] text-peach">{q}</p>
        </div>
      ))}
      <p className="font-[Silkscreen] text-[10px] text-peach tracking-[0.14em] mt-4">WHY NOW</p>
      <p className="text-[12px] text-muted leading-relaxed">MCP and A2A protocols are exploding with no identity story. Enterprise adoption is accelerating. NIST, IETF, and CSA are building standards — the window to influence them is now.</p>
    </div>
  );

  if (section === 2) return (
    <div className={panelClass}>
      <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em]">// 02 — THE INSIGHT</p>
      <h2 className="font-[Silkscreen] text-ink text-xl">FOUR LAYERS, TWO MISSING</h2>
      <div className="space-y-1">
        {[
          { label: 'HUMAN IDENTITY', desc: 'Okta, Google, Azure AD', s: 'EXISTS', c: 'text-green' },
          { label: 'BINDING', desc: 'Provable link: human ↔ agent', s: 'NEW', c: 'text-coral' },
          { label: 'AGENT RUNTIME', desc: 'Crypto key + behavioral signature', s: 'NEW', c: 'text-coral' },
          { label: 'AUTHORIZATION', desc: 'OAuth 2.0 / OIDC / RFC 8693', s: 'EXISTS', c: 'text-green' },
        ].map((l, i) => (
          <div key={i} className="flex justify-between items-center bg-paper2/80 px-3 py-2">
            <div><p className="text-[11px] text-ink font-bold">{l.label}</p><p className="text-[10px] text-dim">{l.desc}</p></div>
            <span className={`text-[9px] tracking-[0.14em] font-bold ${l.c}`}>{l.s}</span>
          </div>
        ))}
      </div>
      <p className="text-[12px] text-muted leading-relaxed">
        The agent does not get its own credentials. It gets the <span className="text-peach">human's credentials, with attribution</span> via an
        <code className="text-coral bg-paper3 px-1 text-[10px] mx-1">act.sub</code> claim in the JWT.
      </p>
      <div className="bg-paper2 border border-paper3 p-3">
        <pre className="text-[10px] text-ink font-mono leading-relaxed">{`{ "sub": "alice@co.com",
  "act": { "sub": "agt_xyz" },
  "similarity_score": 0.94 }`}</pre>
      </div>
    </div>
  );

  if (section === 3) return (
    <div className={panelClass}>
      <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em]">// 03 — CORE IP</p>
      <h2 className="font-[Silkscreen] text-ink text-xl">BEHAVIORAL SIGNATURES</h2>
      <p className="text-[12px] text-muted leading-relaxed">
        Every AI agent has a behavioral fingerprint. We extract 7 feature types from trajectories and compare using a weighted ensemble.
      </p>
      <div className="space-y-1">
        {[
          { n: '01', t: 'TOOL CALL HISTOGRAM', d: 'Normalized frequency distribution of tools/actions' },
          { n: '02', t: 'BIGRAM TRANSITIONS', d: 'Markov model of sequential tool-call transitions' },
          { n: '03', t: 'TRIGRAM TRANSITIONS', d: 'Three-step sequence probabilities' },
          { n: '04', t: 'RESPONSE LENGTH STATS', d: 'Mean, variance, skewness of message lengths' },
          { n: '05', t: 'VOCABULARY STATS', d: 'Token diversity, type-token ratio, top-20 tokens' },
          { n: '06', t: 'TIMING STATS', d: 'Inter-action intervals when timestamps available' },
          { n: '07', t: 'STRUCTURAL FEATURES', d: 'Sequence length, action diversity, error rate' },
        ].map((f, i) => (
          <button key={i} onClick={() => setExpanded(expanded === i ? null : i)} className="w-full text-left bg-paper2/60 px-3 py-2 hover:bg-paper2 transition-colors">
            <div className="flex gap-2 items-center"><span className="text-coral font-[Silkscreen] text-[9px]">{f.n}</span><span className="text-[11px] text-ink font-bold">{f.t}</span></div>
            {expanded === i && <p className="text-[10px] text-muted mt-1 ml-6">{f.d}</p>}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-4 gap-1 text-[10px] mt-2">
        {[['JSD', '25%'], ['Cosine', '30%'], ['Markov', '25%'], ['Stats', '20%']].map(([m, w], i) => (
          <div key={i} className="bg-paper2/80 p-2 text-center"><p className="text-dim">{m}</p><p className="text-coral font-bold">{w}</p></div>
        ))}
      </div>
      <div className="border-l-2 border-amber pl-3 py-1 mt-2">
        <p className="text-[10px] text-amber">Behavioral signatures are anomaly detection, not authentication. The cryptographic hardness is in the key + IdP token.</p>
      </div>
    </div>
  );

  if (section === 4) return (
    <div className={panelClass}>
      <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em]">// 04 — ARCHITECTURE</p>
      <h2 className="font-[Silkscreen] text-ink text-xl">HOW IT'S BUILT</h2>
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-paper2/80 p-3">
          <p className="font-[Silkscreen] text-[9px] text-coral mb-2">REGISTRATION</p>
          {['Authenticate via Clerk', 'Submit trajectory sample', 'Compute signature', 'Generate bcrypt key', 'Return key once'].map((s, i) => (
            <p key={i} className="text-[10px] text-muted"><span className="text-coral mr-1">{i + 1}.</span>{s}</p>
          ))}
        </div>
        <div className="bg-paper2/80 p-3">
          <p className="font-[Silkscreen] text-[9px] text-green mb-2">VERIFICATION</p>
          {['Present ID + key + trajectory', 'Crypto check: bcrypt hash', 'Behavioral check: signature match', 'Issue RS256 JWT with act.sub'].map((s, i) => (
            <p key={i} className="text-[10px] text-muted"><span className="text-green mr-1">{i + 1}.</span>{s}</p>
          ))}
        </div>
      </div>
      <p className="font-[Silkscreen] text-[9px] text-peach tracking-[0.14em] mt-3">12 API ENDPOINTS</p>
      <div className="grid grid-cols-2 gap-2 text-[10px]">
        <div className="bg-paper2/80 p-2">
          <p className="text-coral text-[9px] mb-1">AUTHENTICATED</p>
          {['POST /agents/register', 'GET /agents', 'DELETE /agents/{id}', 'POST /refine', 'POST /rotate-key'].map((e, i) => (
            <p key={i} className="font-mono text-dim">{e}</p>
          ))}
        </div>
        <div className="bg-paper2/80 p-2">
          <p className="text-green text-[9px] mb-1">OPEN</p>
          {['POST /verify', 'POST /compare', 'GET /public', 'GET /.well-known/jwks.json'].map((e, i) => (
            <p key={i} className="font-mono text-dim">{e}</p>
          ))}
        </div>
      </div>
    </div>
  );

  if (section === 5) return (
    <div className={panelClass}>
      <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em]">// 05 — SECURITY</p>
      <h2 className="font-[Silkscreen] text-ink text-xl">THREAT MODEL</h2>
      <div className="space-y-2">
        {[
          { t: 'Random attacker without key', d: 'Agent key (bcrypt, 48-byte)', s: 'STRONG', c: 'text-green' },
          { t: 'Key stolen, behavior unknown', d: 'Behavioral signature mismatch', s: 'SOFT', c: 'text-amber' },
          { t: 'Agent silently swapped', d: 'Trajectory drift detection', s: 'SOFT', c: 'text-amber' },
          { t: 'Human account compromised', d: 'Clerk revocation → keys invalidated', s: 'STRONG', c: 'text-green' },
          { t: 'Key compromise detected', d: 'Key rotation (old key dies)', s: 'STRONG', c: 'text-green' },
        ].map((r, i) => (
          <div key={i} className="flex justify-between items-start bg-paper2/60 px-3 py-2">
            <div><p className="text-[11px] text-red">{r.t}</p><p className="text-[10px] text-muted">{r.d}</p></div>
            <span className={`text-[9px] tracking-[0.14em] font-bold ${r.c} shrink-0`}>{r.s}</span>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-muted leading-relaxed mt-2">
        The cryptographic hardness is in the key and the IdP. Behavioral signatures are anomaly detection — honest about what's strong vs. soft.
      </p>
    </div>
  );

  if (section === 6) return (
    <div className={panelClass}>
      <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em]">// 06 — LANDSCAPE</p>
      <h2 className="font-[Silkscreen] text-ink text-xl">COMPETITIVE LANDSCAPE</h2>
      <div className="space-y-3">
        <div>
          <p className="text-[10px] text-amber tracking-[0.12em] mb-1">STANDARDS</p>
          <p className="text-[11px] text-muted">IETF WIMSE · NVIDIA AIP · OIDC-A 1.0 · NIST CAISI</p>
        </div>
        <div>
          <p className="text-[10px] text-green tracking-[0.12em] mb-1">OPEN SOURCE</p>
          <p className="text-[11px] text-muted">ZeroID (RFC 8693, no behavioral) · AIP (Ed25519) · Microsoft AGT</p>
        </div>
        <div>
          <p className="text-[10px] text-red tracking-[0.12em] mb-1">PLATFORM (VENDOR-LOCKED)</p>
          <p className="text-[11px] text-muted">Microsoft Entra · Google Vertex · Okta/Auth0</p>
        </div>
      </div>
      <div className="border border-coral/30 bg-coral/5 p-3 mt-2">
        <p className="text-[11px] text-coral font-bold">No production system implements behavioral verification.</p>
        <p className="text-[10px] text-muted mt-0.5">This is our unique contribution.</p>
      </div>
    </div>
  );

  if (section === 7) return (
    <div className={panelClass}>
      <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em]">// 07 — ROADMAP</p>
      <h2 className="font-[Silkscreen] text-ink text-xl">WHAT'S NEXT</h2>
      <div className="grid grid-cols-3 gap-2">
        {[
          { phase: '90D', color: 'text-coral', items: ['IP/CIDR posture', 'Risk scoring', 'World ID', 'Drift alerts'] },
          { phase: '180D', color: 'text-peach', items: ['OIDC login', 'Token exchange', 'Verifier SDK', 'MCP reference'] },
          { phase: '365D', color: 'text-ink', items: ['Webhooks', 'Cross-org', 'A2A verifier', 'IETF submission'] },
        ].map((p, i) => (
          <div key={i} className="bg-paper2/80 p-3">
            <p className={`font-[Silkscreen] text-[9px] ${p.color} mb-2`}>{p.phase}</p>
            {p.items.map((item, j) => (
              <p key={j} className="text-[10px] text-muted">· {item}</p>
            ))}
          </div>
        ))}
      </div>
      <div className="text-center mt-4">
        <p className="font-[Silkscreen] text-coral text-[14px] mb-4" style={{ textShadow: '0 0 15px rgba(217,119,87,0.2)' }}>
          WE DO NOT REINVENT THE IDENTITY WHEEL. WE FINISH IT.
        </p>
        <div className="flex gap-3 justify-center">
          <Link to="/" className="pointer-events-auto px-5 py-2 bg-coral text-paper text-[10px] font-bold tracking-[0.14em] hover:bg-coral-deep transition-colors"
            style={{ boxShadow: '0 0 16px rgba(217,119,87,0.25)' }}>
            ENTER PLATFORM
          </Link>
          <a href="https://github.com/yskew/worldofagents" target="_blank" rel="noopener"
            className="pointer-events-auto px-5 py-2 border border-paper4 text-[10px] text-muted tracking-[0.14em] hover:border-coral/40 hover:text-peach transition-colors">
            GITHUB
          </a>
        </div>
      </div>
    </div>
  );

  return null;
}
