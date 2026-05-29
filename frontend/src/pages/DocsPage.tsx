import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import * as THREE from 'three';
import DocsNav from '../components/DocsNav';

interface Exhibit {
  group: THREE.Group;
  orbitRadius: number;
  orbitSpeed: number;
  orbitTiltX: number;
  orbitTiltZ: number;
  orbitPhase: number;
  index: number;
  label: string;
}

function lerp(a: number, b: number, t: number) { return a + (b - a) * t; }
function easeOut(t: number) { return 1 - Math.pow(1 - t, 3); }

// ---- build terminal screen objects ----

function buildSatellite(color: number, icon: number[][]) {
  const g = new THREE.Group();
  // body
  const body = new THREE.Mesh(
    new THREE.BoxGeometry(0.25, 0.2, 0.15),
    new THREE.MeshBasicMaterial({ color, wireframe: true, transparent: true, opacity: 0.5 })
  );
  g.add(body);
  const bodyFill = new THREE.Mesh(
    new THREE.BoxGeometry(0.24, 0.19, 0.14),
    new THREE.MeshBasicMaterial({ color: 0x1c1916, transparent: true, opacity: 0.7 })
  );
  g.add(bodyFill);
  // solar panel left
  const panelL = new THREE.Mesh(
    new THREE.PlaneGeometry(0.35, 0.15),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.25, side: THREE.DoubleSide })
  );
  panelL.position.x = -0.3;
  g.add(panelL);
  const panelLFrame = new THREE.Mesh(
    new THREE.PlaneGeometry(0.36, 0.16),
    new THREE.MeshBasicMaterial({ color, wireframe: true, transparent: true, opacity: 0.4, side: THREE.DoubleSide })
  );
  panelLFrame.position.x = -0.3;
  g.add(panelLFrame);
  // solar panel struts
  const strutL = new THREE.Mesh(
    new THREE.BoxGeometry(0.18, 0.01, 0.01),
    new THREE.MeshBasicMaterial({ color: 0x5e524a, transparent: true, opacity: 0.5 })
  );
  strutL.position.x = -0.17;
  g.add(strutL);
  // solar panel right
  const panelR = panelL.clone(); panelR.position.x = 0.3; g.add(panelR);
  const panelRFrame = panelLFrame.clone(); panelRFrame.position.x = 0.3; g.add(panelRFrame);
  const strutR = strutL.clone(); strutR.position.x = 0.17; g.add(strutR);
  // antenna
  const antenna = new THREE.Mesh(
    new THREE.CylinderGeometry(0.008, 0.008, 0.18, 4),
    new THREE.MeshBasicMaterial({ color: 0x8a7a6f, transparent: true, opacity: 0.5 })
  );
  antenna.position.y = 0.19;
  g.add(antenna);
  const dish = new THREE.Mesh(
    new THREE.SphereGeometry(0.04, 4, 4, 0, Math.PI * 2, 0, Math.PI / 2),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.4 })
  );
  dish.position.y = 0.28;
  dish.rotation.x = Math.PI;
  g.add(dish);
  // pixel icon on the body face
  icon.forEach(([x, y]) => {
    const px = new THREE.Mesh(
      new THREE.BoxGeometry(0.015, 0.015, 0.005),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.9 })
    );
    px.position.set(x * 0.02, y * 0.02, 0.076);
    g.add(px);
  });
  // glow sphere
  const glow = new THREE.Mesh(
    new THREE.SphereGeometry(0.4, 6, 6),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.03 })
  );
  g.add(glow);
  return g;
}

// pixel icon patterns (centered around 0,0)
const ICONS = {
  // lock shape
  problem: [[-1,2],[0,2],[1,2],[-2,1],[-2,0],[-2,-1],[-2,-2],[2,1],[2,0],[2,-1],[2,-2],[-2,-2],[-1,-2],[0,-2],[1,-2],[2,-2],[0,0]],
  // stacked bars
  insight: [[-3,2],[-2,2],[-1,2],[0,2],[1,2],[2,2],[3,2],[-3,0],[-2,0],[-1,0],[0,0],[1,0],[2,0],[3,0],[-3,-2],[-2,-2],[-1,-2],[0,-2],[1,-2],[2,-2],[3,-2]],
  // wave/fingerprint
  signatures: [[-3,1],[-2,2],[-1,2],[0,1],[1,0],[2,-1],[3,-2],[-3,-1],[-2,0],[-1,0],[0,-1],[1,-2],[2,-2],[3,-1]],
  // nodes connected
  architecture: [[0,2],[-2,0],[2,0],[0,-2],[-1,1],[1,1],[-1,-1],[1,-1],[0,0]],
  // shield
  security: [[0,3],[-1,2],[1,2],[-2,1],[2,1],[-2,0],[2,0],[-1,-1],[1,-1],[0,-2]],
  // grid dots
  landscape: [[-2,2],[0,2],[2,2],[-2,0],[0,0],[2,0],[-2,-2],[0,-2],[2,-2]],
  // arrow right
  roadmap: [[-3,0],[-2,0],[-1,0],[0,0],[1,0],[2,0],[3,0],[1,2],[2,1],[1,-2],[2,-1]],
};

const ORBIT_COLORS = [0xcc5f5f, 0xccaa44, 0xd97757, 0xe89b7d, 0x7dcc8a, 0xccaa44, 0xd97757];

// ---- orbit configs: true 3D electron shells ----
// each orbit is defined by axis of rotation (tiltX, tiltZ) so they cross all planes
// radii tight (2.5-3.8), phases spread evenly (π/3.5 apart), tilts on different planes to avoid collision
const ORBITS = [
  { radius: 2.8, speed: 0.14, tiltX: 0.0,  tiltZ: 0.0,  phase: 0.0,  icon: ICONS.problem,      label: 'PROBLEM' },
  { radius: 3.0, speed:-0.12, tiltX: 1.57, tiltZ: 0.0,  phase: 0.9,  icon: ICONS.insight,      label: 'INSIGHT' },
  { radius: 3.2, speed: 0.10, tiltX: 0.0,  tiltZ: 1.57, phase: 1.8,  icon: ICONS.signatures,   label: 'SIGNATURES' },
  { radius: 3.4, speed:-0.11, tiltX: 0.78, tiltZ: 0.78, phase: 2.7,  icon: ICONS.architecture, label: 'ARCHITECTURE' },
  { radius: 3.1, speed: 0.13, tiltX: 1.57, tiltZ: 1.57, phase: 3.6,  icon: ICONS.security,     label: 'SECURITY' },
  { radius: 3.6, speed:-0.09, tiltX: 0.4,  tiltZ: 2.35, phase: 4.5,  icon: ICONS.landscape,    label: 'LANDSCAPE' },
  { radius: 2.6, speed: 0.15, tiltX: 2.35, tiltZ: 0.4,  phase: 5.4,  icon: ICONS.roadmap,      label: 'ROADMAP' },
];

export default function DocsPage() {
  const mountRef = useRef<HTMLDivElement>(null);
  const [activeSection, setActiveSection] = useState(0);
  const [hovered, setHovered] = useState<string | null>(null);
  const stateRef = useRef({
    camera: null as THREE.PerspectiveCamera | null,
    target: 0,
    progress: 1,
    fromPos: new THREE.Vector3(0, 1.5, 7),
    toPos: new THREE.Vector3(0, 1.5, 7),
    fromLook: new THREE.Vector3(0, 0, 0),
    toLook: new THREE.Vector3(0, 0, 0),
    exhibits: [] as Exhibit[],
    raycaster: new THREE.Raycaster(),
    mouse: new THREE.Vector2(),
    hoveredIdx: -1,
    time: 0,
  });

  const navigateTo = (index: number) => {
    const s = stateRef.current;
    if (!s.camera || s.progress < 1) return;
    s.fromPos.copy(s.camera.position);
    s.fromLook.copy(s.toLook);
    s.target = index;
    s.progress = 0;

    if (index === 0) {
      const t = performance.now() * 0.001;
      const a = t * 0.08;
      s.toPos.set(Math.sin(a) * 7, 1.5, Math.cos(a) * 7);
      s.toLook.set(0, 0, 0);
    }
    // for exhibit targets, toPos/toLook are computed dynamically in animate
  };

  useEffect(() => {
    const mount = mountRef.current!;
    const s = stateRef.current;

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x141210, 0.018);

    const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 200);
    camera.position.set(0, 1.5, 7);
    s.camera = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setClearColor(0x141210);
    mount.appendChild(renderer.domElement);

    // --- central globe (nucleus) ---
    const nucleus = new THREE.Group();
    const coreGeo = new THREE.IcosahedronGeometry(1.5, 3);
    const coreMat = new THREE.MeshBasicMaterial({ color: 0xd97757, wireframe: true, transparent: true, opacity: 0.1 });
    nucleus.add(new THREE.Mesh(coreGeo, coreMat));

    const innerPts = new THREE.Points(
      new THREE.IcosahedronGeometry(1.2, 2),
      new THREE.PointsMaterial({ color: 0xe89b7d, size: 0.04, transparent: true, opacity: 0.35 })
    );
    nucleus.add(innerPts);

    // orbital tracks (visible rings on tilted planes like electron shells)
    ORBITS.forEach((o, i) => {
      const trackGeo = new THREE.RingGeometry(o.radius - 0.01, o.radius + 0.01, 80);
      const trackMat = new THREE.MeshBasicMaterial({ color: ORBIT_COLORS[i], transparent: true, opacity: 0.05, side: THREE.DoubleSide });
      const track = new THREE.Mesh(trackGeo, trackMat);
      track.rotation.x = o.tiltX;
      track.rotation.z = o.tiltZ;
      nucleus.add(track);
    });
    scene.add(nucleus);

    // --- particles ---
    const pCount = 500;
    const pGeo = new THREE.BufferGeometry();
    const pPos = new Float32Array(pCount * 3);
    for (let i = 0; i < pCount; i++) {
      pPos[i * 3] = (Math.random() - 0.5) * 40;
      pPos[i * 3 + 1] = (Math.random() - 0.5) * 20;
      pPos[i * 3 + 2] = (Math.random() - 0.5) * 40;
    }
    pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
    scene.add(new THREE.Points(pGeo, new THREE.PointsMaterial({ color: 0xd97757, size: 0.02, transparent: true, opacity: 0.15 })));

    // --- build orbiting terminal exhibits ---
    const exhibits: Exhibit[] = [];
    ORBITS.forEach((o, i) => {
      const group = buildSatellite(ORBIT_COLORS[i], o.icon);
      group.scale.setScalar(0.8);
      scene.add(group);
      exhibits.push({
        group,
        orbitRadius: o.radius,
        orbitSpeed: o.speed,
        orbitTiltX: o.tiltX,
        orbitTiltZ: o.tiltZ,
        orbitPhase: o.phase,
        index: i + 1,
        label: o.label,
      });
    });
    s.exhibits = exhibits;

    // --- animate ---
    let raf: number;
    const currentLook = new THREE.Vector3(0, 0, 0);

    const animate = () => {
      const t = performance.now() * 0.001;
      s.time = t;

      nucleus.rotation.y = t * 0.03;

      // orbit each exhibit on tilted 3D planes
      exhibits.forEach((ex) => {
        const angle = t * ex.orbitSpeed + ex.orbitPhase;
        // start on XZ plane, then rotate by tiltX (around X) and tiltZ (around Z)
        let px = Math.cos(angle) * ex.orbitRadius;
        let py = 0;
        let pz = Math.sin(angle) * ex.orbitRadius;
        // rotate around X axis
        const cx = Math.cos(ex.orbitTiltX), sx = Math.sin(ex.orbitTiltX);
        const ry = py * cx - pz * sx;
        const rz = py * sx + pz * cx;
        py = ry; pz = rz;
        // rotate around Z axis
        const cz = Math.cos(ex.orbitTiltZ), sz = Math.sin(ex.orbitTiltZ);
        const rx = px * cz - py * sz;
        const ry2 = px * sz + py * cz;
        px = rx; py = ry2;
        ex.group.position.set(px, py, pz);

        // face the camera
        ex.group.lookAt(camera.position);

        // scale pulse on hover
        const isHovered = s.hoveredIdx === ex.index - 1;
        const isActive = s.target === ex.index;
        const targetScale = isHovered ? 1.2 : isActive ? 1.1 : 0.8;
        const curScale = ex.group.scale.x;
        ex.group.scale.setScalar(lerp(curScale, targetScale, 0.08));
      });

      // camera
      if (s.progress < 1) {
        s.progress = Math.min(1, s.progress + 0.012);
        const ease = easeOut(s.progress);

        if (s.target > 0) {
          // track the orbiting object
          const ex = exhibits[s.target - 1];
          const dir = ex.group.position.clone().normalize();
          const camPos = ex.group.position.clone().add(dir.multiplyScalar(1.8));
          camPos.y += 0.8;
          s.toPos.copy(camPos);
          s.toLook.copy(ex.group.position);
        }

        camera.position.x = lerp(s.fromPos.x, s.toPos.x, ease);
        camera.position.y = lerp(s.fromPos.y, s.toPos.y, ease);
        camera.position.z = lerp(s.fromPos.z, s.toPos.z, ease);
        currentLook.x = lerp(s.fromLook.x, s.toLook.x, ease);
        currentLook.y = lerp(s.fromLook.y, s.toLook.y, ease);
        currentLook.z = lerp(s.fromLook.z, s.toLook.z, ease);
        camera.lookAt(currentLook);

        if (s.progress >= 1) setActiveSection(s.target);
      } else if (s.target > 0) {
        // track the orbiting object continuously
        const ex = exhibits[s.target - 1];
        const dir = ex.group.position.clone().normalize();
        const camPos = ex.group.position.clone().add(dir.multiplyScalar(1.8));
        camPos.y += 0.8;
        camera.position.lerp(camPos, 0.03);
        camera.lookAt(ex.group.position);
      } else {
        // overview: slowly orbit around the world
        const orbitAngle = t * 0.08;
        const camR = 7;
        camera.position.x = Math.sin(orbitAngle) * camR;
        camera.position.y = 1.5 + Math.sin(t * 0.12) * 0.5;
        camera.position.z = Math.cos(orbitAngle) * camR;
        camera.lookAt(0, 0, 0);
      }

      renderer.render(scene, camera);
      raf = requestAnimationFrame(animate);
    };
    animate();

    // --- interaction ---
    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', onResize);

    const onMouseMove = (e: MouseEvent) => {
      s.mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
      s.mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
      s.raycaster.setFromCamera(s.mouse, camera);

      let found = -1;
      for (let i = 0; i < exhibits.length; i++) {
        if (s.raycaster.intersectObject(exhibits[i].group, true).length > 0) {
          found = i; break;
        }
      }
      s.hoveredIdx = found;
      renderer.domElement.style.cursor = found >= 0 ? 'pointer' : 'default';
      setHovered(found >= 0 ? exhibits[found].label : null);
    };
    mount.addEventListener('mousemove', onMouseMove);

    const onClick = () => {
      if (s.hoveredIdx >= 0) navigateTo(s.hoveredIdx + 1);
    };
    mount.addEventListener('click', onClick);

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') navigateTo(0);
      if (e.key === 'ArrowRight') navigateTo(Math.min(7, s.target + 1));
      if (e.key === 'ArrowLeft') navigateTo(Math.max(0, s.target - 1));
    };
    window.addEventListener('keydown', onKey);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', onResize);
      window.removeEventListener('keydown', onKey);
      mount.removeEventListener('mousemove', onMouseMove);
      mount.removeEventListener('click', onClick);
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);

  return (
    <div className="h-screen overflow-hidden relative">
      <div className="fixed inset-0 pointer-events-none z-50" style={{ background: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.04) 0 1px, transparent 1px 3px)', mixBlendMode: 'multiply' }} />

      <div ref={mountRef} className="absolute inset-0" />

      {/* hover tooltip */}
      {hovered && activeSection === 0 && (
        <div className="fixed top-6 left-1/2 -translate-x-1/2 z-40">
          <span className="font-[Silkscreen] text-[11px] text-coral tracking-[0.18em] bg-paper/80 backdrop-blur-sm border border-paper3 px-4 py-2">
            CLICK: {hovered}
          </span>
        </div>
      )}

      {/* overview title */}
      {activeSection === 0 && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20 text-center pointer-events-none">
          <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em] mb-2">// RESEARCH THESIS</p>
          <h1 className="font-[Silkscreen] text-coral text-3xl leading-tight mb-3" style={{ textShadow: '0 0 30px rgba(217,119,87,0.3)' }}>
            WORLD OF AGENTS
          </h1>
          <p className="text-[11px] text-dim tracking-[0.14em]">CLICK AN ORBITING OBJECT TO EXPLORE</p>
        </div>
      )}

      {/* content panel */}
      {activeSection > 0 && (
        <div className="absolute top-0 right-0 w-[420px] h-full z-30 flex flex-col">
          <div className="flex-1 overflow-y-auto p-6 bg-paper/90 backdrop-blur-sm border-l border-paper3">
            <button onClick={() => navigateTo(0)} className="text-[10px] text-dim tracking-[0.1em] hover:text-peach transition-colors mb-4 block">
              ← BACK TO OVERVIEW
            </button>
            <ContentPanel section={activeSection} />
          </div>
        </div>
      )}

      <DocsNav activeSection={activeSection} onNavigate={navigateTo} />
    </div>
  );
}


function Collapse({ title, children, defaultOpen = false }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-paper3 bg-paper2/40">
      <button onClick={() => setOpen(!open)} className="w-full text-left px-3 py-2 flex justify-between items-center hover:bg-paper2/80 transition-colors">
        <span className="text-[10px] text-ink font-bold">{title}</span>
        <span className="text-[10px] text-dim">{open ? '−' : '+'}</span>
      </button>
      {open && <div className="px-3 pb-3 pt-1">{children}</div>}
    </div>
  );
}

function Bar({ label, value, color = 'bg-coral' }: { label: string; value: number; color?: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[9px] text-dim w-16 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-paper3 overflow-hidden">
        <div className={`h-full ${color} transition-all duration-1000`} style={{ width: `${value}%` }} />
      </div>
      <span className="text-[9px] text-ink font-mono w-8 text-right">{value}%</span>
    </div>
  );
}

function ContentPanel({ section }: { section: number }) {
  const [showJwt, setShowJwt] = useState(false);
  const [activeTab, setActiveTab] = useState(0);

  if (section === 1) return (
    <div className="space-y-4">
      <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em]">// 01 — THE PROBLEM</p>
      <h2 className="font-[Silkscreen] text-ink text-lg">AGENTS HAVE NO IDENTITY</h2>
      <p className="text-[12px] text-muted leading-relaxed">
        AI agents are autonomous software programs that act on behalf of humans — they write code, deploy infrastructure,
        send emails, query databases, and interact with APIs. The number deployed in production is growing exponentially.
        Every single one has an identity problem.
      </p>

      <Collapse title="OPTION A: NO IDENTITY" defaultOpen>
        <p className="text-[11px] text-muted leading-relaxed">
          The agent operates with no authentication, relying on the assumption it's running in a trusted environment.
          Common in local setups where agents inherit the host machine's permissions via stdio. A Knostic scan of ~2,000
          MCP servers found every single one lacked authentication.
        </p>
      </Collapse>

      <Collapse title="OPTION B: STOLEN IDENTITY" defaultOpen>
        <p className="text-[11px] text-muted leading-relaxed">
          A developer copies their personal OAuth token, API key, or session cookie into the agent's environment variables.
          The agent now has full, indistinguishable access to everything the human can do. No audit trail differentiates
          whether an action was taken by the human or by the agent.
        </p>
      </Collapse>

      <Collapse title="WHY SERVICE ACCOUNTS DON'T FIT">
        <p className="text-[11px] text-muted leading-relaxed">
          Service accounts are static, long-lived, and designed for predictable, non-autonomous workloads. Agents are
          autonomous and probabilistic — their behavior changes with every prompt. A leaked service-account key is
          undetectable until it's exploited at scale.
        </p>
      </Collapse>

      <p className="font-[Silkscreen] text-[9px] text-peach tracking-[0.14em] mt-4">THREE UNANSWERABLE QUESTIONS</p>
      {[
        { q: '"Which human is responsible for this action?"', d: 'The question that underlies all of human IAM is unanswerable for agent actions.' },
        { q: '"Is this the same agent that was authorized?"', d: 'If an agent\'s model is swapped or prompt changed, credentials remain valid.' },
        { q: '"Is this agent behaving normally?"', d: 'No baseline exists to compare against. Anomalous access looks identical to normal.' },
      ].map((item, i) => (
        <Collapse key={i} title={item.q}>
          <p className="text-[10px] text-muted leading-relaxed">{item.d}</p>
        </Collapse>
      ))}

      <p className="font-[Silkscreen] text-[9px] text-peach tracking-[0.14em] mt-4">CONVERGENCE FORCES</p>
      <div className="space-y-2">
        <div className="flex gap-2 items-start"><div className="w-1.5 h-1.5 bg-coral mt-1 shrink-0" /><p className="text-[10px] text-muted"><span className="text-ink">MCP explosion:</span> Anthropic's MCP, Google's A2A, and similar protocols are creating an ecosystem where agents call agents. Zero auth standard exists.</p></div>
        <div className="flex gap-2 items-start"><div className="w-1.5 h-1.5 bg-amber mt-1 shrink-0" /><p className="text-[10px] text-muted"><span className="text-ink">Enterprise adoption:</span> Companies deploying agents for code review, incident response, data pipelines. Each credential is a liability.</p></div>
        <div className="flex gap-2 items-start"><div className="w-1.5 h-1.5 bg-green mt-1 shrink-0" /><p className="text-[10px] text-muted"><span className="text-ink">Regulatory pressure:</span> NIST CAISI launched Feb 2026. IETF has 4 active drafts. CSA published an Agentic IAM Framework.</p></div>
      </div>
    </div>
  );

  if (section === 2) return (
    <div className="space-y-4">
      <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em]">// 02 — THE INSIGHT</p>
      <h2 className="font-[Silkscreen] text-ink text-lg">FOUR LAYERS, TWO MISSING</h2>
      <p className="text-[11px] text-muted leading-relaxed">
        Identity for agents has four layers. The mistake every prior attempt has made is trying to build all four, or building
        them in the wrong order. We build only the two missing layers and delegate everything else.
      </p>

      <div className="space-y-1">
        {[
          { l: 'HUMAN IDENTITY', d: 'Okta, Google Workspace, Azure AD, Auth0, World ID', s: 'DELEGATED', c: 'text-green', detail: 'Mature, battle-tested systems. We authenticate humans via Clerk which federates to these providers.' },
          { l: 'BINDING', d: 'Provable link between human and agent', s: 'WE BUILD THIS', c: 'text-coral', detail: 'Registration flow where a human proves ownership of an agent by submitting a behavioral sample. Stored as a triple: agent_id ↔ human_id ↔ key_hash ↔ signature.' },
          { l: 'AGENT RUNTIME', d: 'Crypto key + behavioral signature + risk score', s: 'WE BUILD THIS', c: 'text-coral', detail: 'The agent gets a cryptographic key (bcrypt, 48-byte random) and a behavioral profile computed from its trajectory. Both are required for verification.' },
          { l: 'AUTHORIZATION', d: 'Scoped, short-lived credentials at runtime', s: 'DELEGATED', c: 'text-green', detail: 'OAuth 2.0 Token Exchange (RFC 8693) with actor claims. We issue JWTs where sub=human, act.sub=agent. Standards-compliant.' },
        ].map((x, i) => (
          <Collapse key={i} title={`${x.l} — ${x.s}`}>
            <p className="text-[9px] text-dim mb-1">{x.d}</p>
            <p className="text-[10px] text-muted leading-relaxed">{x.detail}</p>
          </Collapse>
        ))}
      </div>

      <p className="font-[Silkscreen] text-[9px] text-peach tracking-[0.14em] mt-4">DELEGATION MODEL</p>
      <p className="text-[11px] text-muted leading-relaxed mb-2">
        The agent does not get its own credentials. It acts <span className="text-peach">as the human, with attribution.</span> The
        downstream system sees Alice as the principal. The <code className="text-coral bg-paper3 px-1 text-[9px]">act</code> claim
        provides full attribution of which agent wielded the token.
      </p>

      <div className="border border-paper3 bg-paper2 p-3">
        <div className="flex justify-between items-center mb-2">
          <span className="text-[9px] text-dim tracking-[0.14em]">JWT PAYLOAD</span>
          <button onClick={() => setShowJwt(!showJwt)} className="text-[8px] text-coral hover:text-peach transition-colors">
            {showJwt ? 'COLLAPSE' : 'EXPAND'}
          </button>
        </div>
        <pre className="text-[10px] text-ink font-mono leading-relaxed">{showJwt ? `{
  "iss": "worldofagents",
  "sub": "alice@company.com",
  "act": { "sub": "agt_abc123" },
  "agent_name": "code-assistant",
  "similarity_score": 0.94,
  "iat": 1717000000,
  "exp": 1717003600,
  "jti": "unique-per-issuance"
}` : `{ "sub": "alice@co.com",
  "act": { "sub": "agt_xyz" },
  "similarity_score": 0.94 }`}</pre>
      </div>

      <p className="text-[10px] text-muted leading-relaxed mt-2">
        No new principal in any IdP. No fragmented audit log. No new auth model. The agent is invisible to systems that
        don't care, and fully attributed for systems that do.
      </p>
    </div>
  );

  if (section === 3) return (
    <div className="space-y-4">
      <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em]">// 03 — CORE IP</p>
      <h2 className="font-[Silkscreen] text-ink text-lg">BEHAVIORAL SIGNATURES</h2>
      <p className="text-[11px] text-muted leading-relaxed">
        Every AI agent has a behavioral fingerprint. A coding agent calls search → read_file → edit_file → run_tests
        in predictable patterns. These patterns are as distinctive as a human's keystroke dynamics.
      </p>

      <p className="font-[Silkscreen] text-[9px] text-peach tracking-[0.14em]">SEVEN FEATURE TYPES</p>
      <div className="space-y-1">
        {[
          { n: '01', t: 'TOOL CALL HISTOGRAM', d: 'Normalized frequency distribution of which tools the agent calls. e.g., {search: 0.2, read_file: 0.3, edit_file: 0.2, run_tests: 0.15}. Compared using Jensen-Shannon divergence.' },
          { n: '02', t: 'BIGRAM TRANSITIONS', d: 'Markov model of sequential transitions. "After search, the agent calls read_file 60% of the time." Captures behavioral flow — not just what tools, but the order.' },
          { n: '03', t: 'TRIGRAM TRANSITIONS', d: 'Three-step sequences. "After search → read_file, the agent calls edit_file 80% of the time." Captures complex patterns bigrams miss.' },
          { n: '04', t: 'RESPONSE LENGTH STATS', d: 'Mean, variance, and skewness of message content character lengths. A verbose agent produces different statistics than a terse one. Consistent across sessions.' },
          { n: '05', t: 'VOCABULARY STATS', d: 'Unique token count, total tokens, type-token ratio (lexical diversity), top-20 most frequent tokens. Different models and prompts produce measurably different vocabularies.' },
          { n: '06', t: 'TIMING STATS', d: 'Inter-action intervals when timestamps are provided: mean, std deviation, max interval. An agent taking 2s between actions differs from one taking 30s.' },
          { n: '07', t: 'STRUCTURAL FEATURES', d: 'Total sequence length, unique action types, ratio of tool calls to messages, error/retry ratio. Captures the overall shape of agent behavior.' },
        ].map((f, i) => (
          <Collapse key={i} title={`${f.n} — ${f.t}`}>
            <p className="text-[10px] text-muted leading-relaxed">{f.d}</p>
          </Collapse>
        ))}
      </div>

      <p className="font-[Silkscreen] text-[9px] text-peach tracking-[0.14em] mt-4">COMPARISON ENSEMBLE</p>
      <p className="text-[10px] text-muted mb-2">Four metrics, weighted and combined into a single 0.0–1.0 score:</p>
      <div className="space-y-1.5">
        <Bar label="COSINE" value={30} />
        <Bar label="JSD" value={25} color="bg-amber" />
        <Bar label="MARKOV" value={25} color="bg-peach" />
        <Bar label="STATS" value={20} color="bg-green" />
      </div>

      <div className="grid grid-cols-3 gap-1 mt-3">
        <div className="bg-green/10 border border-green/20 p-2 text-center"><p className="text-[9px] text-green font-bold">≥ 0.7</p><p className="text-[8px] text-dim">PASS</p></div>
        <div className="bg-amber/10 border border-amber/20 p-2 text-center"><p className="text-[9px] text-amber font-bold">0.4–0.7</p><p className="text-[8px] text-dim">WARNING</p></div>
        <div className="bg-red/10 border border-red/20 p-2 text-center"><p className="text-[9px] text-red font-bold">≤ 0.4</p><p className="text-[8px] text-dim">FAIL</p></div>
      </div>

      <div className="border-l-2 border-amber pl-3 py-1 mt-3">
        <p className="text-[10px] text-amber font-bold">HONEST ASSESSMENT</p>
        <p className="text-[9px] text-muted leading-relaxed mt-1">Behavioral signatures are anomaly detection, not authentication. The cryptographic hardness is in the agent key and the IdP-issued token. The behavioral signature detects drift, impersonation, and model swaps — it does not prove identity. We will never claim otherwise.</p>
      </div>

      <p className="font-[Silkscreen] text-[9px] text-peach tracking-[0.14em] mt-4">ACADEMIC BACKING</p>
      {[
        { t: 'LLMmap', v: 'USENIX Security 2025', s: '>95% accuracy across 42 LLM versions', d: '8 carefully crafted probing queries, transformer-based architecture with contrastive learning, 384-dim embeddings.' },
        { t: 'GitHub Agent Fingerprinting', v: 'arXiv Jan 2026', s: '97.2% F1 identifying 5 coding agents', d: '33,580 PRs from Codex, Copilot, Devin, Cursor, Claude Code. 41 features. Key: multiline commit ratio (44.7% importance).' },
        { t: 'Stylometric Ensemble', v: '2025', s: '0.9988 precision, 0.0004 FPR', d: 'Trained on Claude, Gemini, Llama, OpenAI. Unanimous voting across 3 classifiers. Function words and punctuation patterns are strongest signals.' },
      ].map((r, i) => (
        <Collapse key={i} title={`${r.t} — ${r.s}`}>
          <p className="text-[9px] text-dim mb-1">{r.v}</p>
          <p className="text-[10px] text-muted leading-relaxed">{r.d}</p>
        </Collapse>
      ))}
    </div>
  );

  if (section === 4) return (
    <div className="space-y-4">
      <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em]">// 04 — ARCHITECTURE</p>
      <h2 className="font-[Silkscreen] text-ink text-lg">HOW IT'S BUILT</h2>

      {/* tabs */}
      <div className="flex gap-1 border-b border-paper3 mb-3">
        {['FLOWS', 'API', 'DATA', 'STACK'].map((tab, i) => (
          <button key={i} onClick={() => setActiveTab(i)}
            className={`px-3 py-1.5 text-[9px] tracking-[0.12em] transition-colors ${activeTab === i ? 'text-coral border-b border-coral' : 'text-dim hover:text-muted'}`}>
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 0 && <>
        <Collapse title="REGISTRATION FLOW" defaultOpen>
          {['Human authenticates via Clerk (email, Google, GitHub)', 'Submits agent name, description, and sample trajectory (JSON array of tool calls, messages, actions)', 'System extracts 7-category behavioral signature and computes 256-dim pgvector embedding', 'Cryptographic agent key generated (secrets.token_urlsafe(48), bcrypt-hashed)', 'Plain-text key returned exactly once — never stored or retrievable again'].map((s, i) =>
            <p key={i} className="text-[10px] text-muted mb-1"><span className="text-coral font-[Silkscreen] text-[8px] mr-1">{i + 1}.</span>{s}</p>
          )}
        </Collapse>
        <Collapse title="VERIFICATION FLOW" defaultOpen>
          {['Agent presents agent_id + agent_key + current trajectory to POST /verify', 'Cryptographic check: agent_key matches stored bcrypt hash (binary pass/fail)', 'Behavioral check: trajectory compared against stored signature using 4-metric ensemble (returns 0.0–1.0)', 'If both pass (key matches AND score ≥ 0.7): RS256 JWT issued with sub=human, act.sub=agent', 'Verification logged: agent_id, score, pass/fail, IP address, timestamp'].map((s, i) =>
            <p key={i} className="text-[10px] text-muted mb-1"><span className="text-green font-[Silkscreen] text-[8px] mr-1">{i + 1}.</span>{s}</p>
          )}
        </Collapse>
        <Collapse title="REFINEMENT FLOW">
          <p className="text-[10px] text-muted leading-relaxed">Agents evolve. POST /refine accepts additional trajectory data and merges it into the stored signature using exponential weighted averaging (70% existing, 30% new). Prevents a single submission from overwriting the profile while allowing gradual adaptation.</p>
        </Collapse>
      </>}

      {activeTab === 1 && <>
        <p className="text-[9px] text-coral tracking-[0.12em] mb-2">AUTHENTICATED (CLERK SESSION)</p>
        {['POST /agents/register — Register new agent', 'GET /agents — List your agents', 'GET /agents/{id} — Agent details', 'DELETE /agents/{id} — Revoke (soft delete)', 'POST /agents/{id}/refine — Improve signature', 'POST /agents/{id}/rotate-key — New key, old dies'].map((e, i) =>
          <p key={i} className="text-[9px] font-mono text-dim py-0.5">{e}</p>
        )}
        <p className="text-[9px] text-green tracking-[0.12em] mt-3 mb-2">OPEN (NO AUTH)</p>
        {['POST /verify — Verify identity, get JWT', 'POST /compare — Compare two trajectories', 'GET /agents/{id}/public — Public profile + stats', 'GET /.well-known/jwks.json — JWT verification keys', 'GET /health — System health'].map((e, i) =>
          <p key={i} className="text-[9px] font-mono text-dim py-0.5">{e}</p>
        )}
      </>}

      {activeTab === 2 && <>
        <Collapse title="HUMANS TABLE" defaultOpen>
          <div className="space-y-0.5 text-[9px] font-mono text-dim">
            <p>id <span className="text-coral">UUID PK</span></p><p>clerk_id <span className="text-coral">UNIQUE INDEX</span></p>
            <p>display_name, email</p><p>created_at</p>
          </div>
        </Collapse>
        <Collapse title="AGENTS TABLE" defaultOpen>
          <div className="space-y-0.5 text-[9px] font-mono text-dim">
            <p>id <span className="text-coral">UUID PK</span></p><p>human_id <span className="text-coral">FK → humans</span></p>
            <p>name, description</p><p>key_hash <span className="text-amber">(bcrypt)</span>, key_salt</p>
            <p>signature <span className="text-amber">(JSONB)</span></p><p>signature_vector <span className="text-amber">(Vector(256))</span></p>
            <p>status (active/revoked)</p><p>created_at, updated_at</p>
          </div>
        </Collapse>
        <Collapse title="VERIFICATION_LOG TABLE">
          <div className="space-y-0.5 text-[9px] font-mono text-dim">
            <p>id <span className="text-coral">UUID PK</span></p><p>agent_id <span className="text-coral">FK → agents</span></p>
            <p>similarity_score <span className="text-amber">(float)</span></p><p>passed <span className="text-amber">(bool)</span></p>
            <p>ip_address, requested_at</p>
          </div>
        </Collapse>
      </>}

      {activeTab === 3 && <>
        <div className="space-y-1">
          {[
            { l: 'Backend', v: 'FastAPI (Python)', c: 'text-coral' },
            { l: 'ORM', v: 'SQLAlchemy 2.0 (async)', c: 'text-muted' },
            { l: 'Database', v: 'PostgreSQL 17 + pgvector', c: 'text-coral' },
            { l: 'Migrations', v: 'Alembic', c: 'text-muted' },
            { l: 'Key hashing', v: 'bcrypt', c: 'text-muted' },
            { l: 'JWT', v: 'PyJWT + cryptography (RS256)', c: 'text-coral' },
            { l: 'Stats', v: 'scipy + numpy', c: 'text-muted' },
            { l: 'Auth', v: 'Clerk', c: 'text-coral' },
            { l: 'Frontend', v: 'React 19 + TypeScript + Vite', c: 'text-coral' },
            { l: 'Styling', v: 'Tailwind CSS 4', c: 'text-muted' },
            { l: '3D', v: 'Three.js', c: 'text-muted' },
            { l: 'Deploy', v: 'Docker Compose / Railway', c: 'text-coral' },
          ].map((s, i) => (
            <div key={i} className="flex justify-between bg-paper2/40 px-3 py-1.5">
              <span className="text-[9px] text-dim">{s.l}</span>
              <span className={`text-[9px] ${s.c}`}>{s.v}</span>
            </div>
          ))}
        </div>
      </>}
    </div>
  );

  if (section === 5) return (
    <div className="space-y-4">
      <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em]">// 05 — SECURITY</p>
      <h2 className="font-[Silkscreen] text-ink text-lg">THREAT MODEL</h2>
      <p className="text-[11px] text-muted leading-relaxed mb-2">We are explicit about what each layer protects against. Soft signals oversold are worse than soft signals not used at all.</p>

      {[
        { t: 'Random attacker without key', d: 'Agent key: cryptographically random 48-byte, bcrypt-hashed. Brute-force infeasible.', s: 'CRYPTOGRAPHIC', c: 'text-green', icon: '●' },
        { t: 'Attacker steals key but doesn\'t know agent\'s behavior', d: 'Behavioral signature mismatch + IP posture anomaly. Probabilistic — detects but does not prove.', s: 'PROBABILISTIC', c: 'text-amber', icon: '◐' },
        { t: 'Agent silently swapped for different model', d: 'Trajectory drift exceeds threshold. Owner notified, forced re-verification with consent.', s: 'OPERATIONAL', c: 'text-amber', icon: '◐' },
        { t: 'Human account compromised', d: 'Inherited revocation: Clerk deprovisioning event → webhook → all agent keys revoked immediately.', s: 'STRONG', c: 'text-green', icon: '●' },
        { t: 'Key compromise detected', d: 'Key rotation endpoint: new key generated, old key invalidated atomically. Zero-downtime rotation.', s: 'CRYPTOGRAPHIC', c: 'text-green', icon: '●' },
      ].map((r, i) => (
        <Collapse key={i} title={`${r.icon} ${r.t}`}>
          <p className="text-[10px] text-muted leading-relaxed">{r.d}</p>
          <span className={`text-[8px] tracking-[0.14em] font-bold ${r.c} mt-1 block`}>{r.s}</span>
        </Collapse>
      ))}

      <p className="font-[Silkscreen] text-[9px] text-peach tracking-[0.14em] mt-4">WHAT WE INTEGRATE, NOT BUILD</p>
      <div className="space-y-1">
        {[
          { what: 'Human auth, MFA, sessions', how: 'Clerk (cloud)' },
          { what: 'Agent key hashing', how: 'bcrypt (standard)' },
          { what: 'JWT signing + JWKS', how: 'PyJWT + cryptography' },
          { what: 'Vector similarity', how: 'pgvector extension' },
          { what: 'Statistical analysis', how: 'scipy + numpy' },
        ].map((r, i) => (
          <div key={i} className="flex justify-between bg-paper2/40 px-3 py-1.5">
            <span className="text-[9px] text-muted">{r.what}</span>
            <span className="text-[9px] text-green">{r.how}</span>
          </div>
        ))}
      </div>
    </div>
  );

  if (section === 6) return (
    <div className="space-y-4">
      <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em]">// 06 — LANDSCAPE</p>
      <h2 className="font-[Silkscreen] text-ink text-lg">COMPETITIVE LANDSCAPE</h2>
      <p className="text-[11px] text-muted leading-relaxed">The agent identity space is active but fragmented. No standard has won. Here's who's working on it:</p>

      <Collapse title="STANDARDS BODIES (ALL DRAFTS)" defaultOpen>
        <div className="space-y-1.5">
          {[
            { n: 'IETF WIMSE', d: 'Workload Identity in Multi-System Environments. Foundational standard. Participants: AWS, Google, Microsoft, HashiCorp, Okta.' },
            { n: 'IETF draft-klrc-aiagent-auth', d: '9-component Agent Identity Management System (AIMS). Mandates WIMSE identifiers. Authors from AWS, Zscaler, Ping Identity.' },
            { n: 'NVIDIA AIP', d: 'Ed25519 keypairs, Agent Authentication Tokens per tool call. Targets MCP integration. Also an IETF draft.' },
            { n: 'OIDC-A 1.0', d: 'Extends OpenID Connect with delegation chain validation and attestation for LLM agents.' },
            { n: 'NIST CAISI', d: 'Launched Feb 2026. AI Agent Interoperability Profile planned for Q4 2026.' },
          ].map((s, i) => <div key={i}><p className="text-[10px] text-amber font-bold">{s.n}</p><p className="text-[9px] text-muted">{s.d}</p></div>)}
        </div>
      </Collapse>

      <Collapse title="OPEN SOURCE PROJECTS">
        <div className="space-y-1.5">
          {[
            { n: 'ZeroID (Highflame)', d: 'Closest competitor. RFC 8693 token exchange, Python/TS/Rust SDKs, PostgreSQL. Apache 2.0. Does NOT do behavioral verification.' },
            { n: 'AIP', d: 'Ed25519 keys, auth tokens per tool call, MCP proxy. Reference implementations in Python/Go/Rust.' },
            { n: 'Microsoft AGT', d: '7-package governance toolkit (Python/TS/Rust/Go/.NET). Credential injection, policy engine. MIT license.' },
          ].map((s, i) => <div key={i}><p className="text-[10px] text-green font-bold">{s.n}</p><p className="text-[9px] text-muted">{s.d}</p></div>)}
        </div>
      </Collapse>

      <Collapse title="PLATFORM (VENDOR-LOCKED)">
        <div className="space-y-1.5">
          {[
            { n: 'Microsoft Entra Agent ID', d: 'Most complete. GA March 2026. Every agent gets Entra identity with Federated Identity Credentials. Microsoft-only.' },
            { n: 'Google Vertex AI', d: 'Agents get cryptographic IDs as IAM principals. Google-ecosystem-only.' },
            { n: 'Okta/Auth0', d: '"For AI Agents" GA 2025-2026. Proprietary. Token management, async approvals.' },
          ].map((s, i) => <div key={i}><p className="text-[10px] text-red font-bold">{s.n}</p><p className="text-[9px] text-muted">{s.d}</p></div>)}
        </div>
      </Collapse>

      <p className="font-[Silkscreen] text-[9px] text-peach tracking-[0.14em] mt-4">DIFFERENTIATION</p>
      <div className="space-y-1">
        {[
          { cap: 'Behavioral verification', us: true, zero: false, aip: false, entra: false },
          { cap: 'Open source', us: true, zero: true, aip: true, entra: false },
          { cap: 'Vendor-neutral', us: true, zero: true, aip: true, entra: false },
          { cap: 'Self-hosted', us: true, zero: true, aip: true, entra: false },
          { cap: 'RFC 8693 delegation', us: true, zero: true, aip: false, entra: false },
          { cap: 'Signature refinement', us: true, zero: false, aip: false, entra: false },
        ].map((r, i) => (
          <div key={i} className="grid grid-cols-5 gap-1 text-[8px] items-center">
            <span className="text-muted col-span-1">{r.cap}</span>
            <span className={`text-center ${r.us ? 'text-coral' : 'text-dim'}`}>{r.us ? '●' : '○'}</span>
            <span className={`text-center ${r.zero ? 'text-green' : 'text-dim'}`}>{r.zero ? '●' : '○'}</span>
            <span className={`text-center ${r.aip ? 'text-amber' : 'text-dim'}`}>{r.aip ? '●' : '○'}</span>
            <span className={`text-center ${r.entra ? 'text-red' : 'text-dim'}`}>{r.entra ? '●' : '○'}</span>
          </div>
        ))}
        <div className="grid grid-cols-5 gap-1 text-[7px] text-dim mt-1">
          <span></span><span className="text-center">WoA</span><span className="text-center">ZeroID</span><span className="text-center">AIP</span><span className="text-center">Entra</span>
        </div>
      </div>

      <div className="border border-coral/30 bg-coral/5 p-3 mt-3">
        <p className="text-[10px] text-coral font-bold">No production system implements behavioral verification.</p>
        <p className="text-[9px] text-muted mt-1">This is our unique contribution.</p>
      </div>
    </div>
  );

  if (section === 7) return (
    <div className="space-y-4">
      <p className="font-[Silkscreen] text-[10px] text-coral tracking-[0.2em]">// 07 — ROADMAP</p>
      <h2 className="font-[Silkscreen] text-ink text-lg">WHAT'S NEXT</h2>

      {[
        { p: 'NEXT 90 DAYS', c: 'text-coral', bc: 'border-coral/20', items: [
          { t: 'IP/CIDR posture checking', d: 'Allowed IP ranges per agent. Requests from unknown IPs trigger step-up verification.' },
          { t: 'Per-action risk scoring', d: 'Combine signature similarity, IP posture, and scope pattern into a real-time risk score.' },
          { t: 'World ID integration', d: 'Proof-of-unique-personhood via Tools for Humanity. Sybil resistance for agent registration.' },
          { t: 'Agent versioning + drift alerts', d: 'Detect when an agent\'s behavior drifts beyond owner-defined thresholds. Force re-verification with consent.' },
        ]},
        { p: '90–180 DAYS', c: 'text-peach', bc: 'border-peach/20', items: [
          { t: 'OIDC login (Okta, Google, Auth0)', d: 'Direct IdP integration at registration for enterprise users.' },
          { t: 'OAuth 2.0 Token Exchange broker', d: 'ZITADEL integration for true RFC 8693 token exchange with external IdPs.' },
          { t: 'Scope pre-authorization UX', d: 'Agent can only request specific scopes. Human approves at registration or via out-of-band flow.' },
          { t: 'Verifier SDK (TypeScript, Python)', d: 'Drop-in libraries for downstream services to verify AgentVerify JWTs.' },
          { t: 'MCP server reference integration', d: 'Reference implementation showing how an MCP server requires AgentVerify-signed tokens.' },
        ]},
        { p: '180–365 DAYS', c: 'text-ink', bc: 'border-paper4', items: [
          { t: 'Lifecycle webhooks', d: 'Deprovisioning, key rotation, ownership transfer events pushed to integrators.' },
          { t: 'Cross-org delegation', d: 'Alice\'s agent acts on behalf of Bob\'s organization. Delegation chains with cryptographic proof.' },
          { t: 'A2A reference verifier', d: 'Agent-to-agent identity verification in the Google A2A protocol.' },
          { t: 'IETF submission', d: 'Submit behavioral signature specification to relevant agent-identity working groups.' },
        ]},
      ].map((phase, i) => (
        <div key={i} className={`border ${phase.bc} p-3`}>
          <p className={`font-[Silkscreen] text-[9px] ${phase.c} tracking-[0.14em] mb-2`}>{phase.p}</p>
          {phase.items.map((item, j) => (
            <Collapse key={j} title={item.t}>
              <p className="text-[9px] text-muted leading-relaxed">{item.d}</p>
            </Collapse>
          ))}
        </div>
      ))}

      <p className="font-[Silkscreen] text-[9px] text-peach tracking-[0.14em] mt-4">TEST COVERAGE</p>
      <div className="space-y-1.5">
        <Bar label="TOTAL" value={86} color="bg-green" />
        <p className="text-[9px] text-muted">116 automated tests across 9 suites. Registration, agent management, verification, JWT, compare, public profiles, multi-user isolation, full lifecycle, impersonation detection.</p>
      </div>

      <div className="text-center pt-6 border-t border-paper3 mt-4">
        <p className="font-[Silkscreen] text-coral text-[13px] mb-2 leading-relaxed" style={{ textShadow: '0 0 12px rgba(217,119,87,0.2)' }}>
          THE MISSING IDENTITY LAYER<br/>FOR AI AGENTS
        </p>
        <p className="text-[10px] text-muted mb-4">We do not reinvent the identity wheel. We finish it.</p>
        <div className="flex gap-2 justify-center">
          <Link to="/" className="px-4 py-2 bg-coral text-paper text-[9px] font-bold tracking-[0.14em] hover:bg-coral-deep transition-colors" style={{ boxShadow: '0 0 12px rgba(217,119,87,0.2)' }}>ENTER PLATFORM</Link>
          <a href="https://github.com/yskew/worldofagents" target="_blank" rel="noopener" className="px-4 py-2 border border-paper4 text-[9px] text-muted tracking-[0.14em] hover:text-peach transition-colors">GITHUB</a>
        </div>
      </div>
    </div>
  );

  return null;
}
