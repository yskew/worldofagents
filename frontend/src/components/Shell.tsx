import { NavLink, Outlet } from 'react-router-dom';
import { UserButton } from '@clerk/react';

const links = [
  { to: '/', label: 'HOME' },
  { to: '/agents', label: 'AGENTS' },
  { to: '/verify', label: 'VERIFY' },
  { to: '/compare', label: 'COMPARE' },
];

export default function Shell() {
  return (
    <div className="h-full flex flex-col relative">
      {/* scanline overlay */}
      <div className="fixed inset-0 pointer-events-none z-50"
        style={{
          background: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.06) 0 1px, transparent 1px 3px)',
          mixBlendMode: 'multiply',
        }}
      />

      {/* top bar */}
      <header className="shrink-0 border-b border-paper3 bg-paper/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-[1400px] mx-auto px-6 h-14 flex items-center justify-between">
          <NavLink to="/" className="flex items-center gap-3 group">
            <div className="w-8 h-8 border-2 border-coral flex items-center justify-center relative">
              <div className="w-2 h-2 bg-coral" style={{ boxShadow: '0 0 8px rgba(217,119,87,0.6)' }} />
              <div className="absolute inset-0 border border-coral/20 scale-125" />
            </div>
            <div>
              <span className="font-[Silkscreen] text-coral text-[13px] tracking-[0.18em] leading-none">
                WORLD OF AGENTS
              </span>
              <span className="block text-[9px] text-dim tracking-[0.12em] mt-0.5">
                // identity layer
              </span>
            </div>
          </NavLink>

          <nav className="flex items-center gap-1">
            {links.map(l => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.to === '/'}
                className={({ isActive }) =>
                  `px-4 py-1.5 text-[11px] tracking-[0.14em] transition-all ${
                    isActive
                      ? 'text-coral bg-coral/10 border border-coral/25'
                      : 'text-muted hover:text-peach border border-transparent'
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 bg-green" style={{ boxShadow: '0 0 6px rgba(125,204,138,0.5)' }} />
              <span className="text-[10px] text-dim tracking-[0.1em]">ONLINE</span>
            </div>
            <UserButton
              appearance={{
                elements: {
                  avatarBox: { borderRadius: '0', width: '28px', height: '28px' },
                  userButtonPopoverCard: {
                    backgroundColor: '#1c1916',
                    border: '1px solid #312d29',
                    borderRadius: '0',
                  },
                },
              }}
            />
          </div>
        </div>
      </header>

      {/* content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-[1400px] mx-auto px-6 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
