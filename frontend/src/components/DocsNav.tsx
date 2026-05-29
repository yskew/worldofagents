import { useState } from 'react';
import { Link } from 'react-router-dom';

const sections = [
  'TITLE', 'PROBLEM', 'INSIGHT', 'SIGNATURES',
  'ARCHITECTURE', 'SECURITY', 'LANDSCAPE', 'ROADMAP',
];

interface Props {
  activeSection: number;
  onNavigate: (index: number) => void;
}

export default function DocsNav({ activeSection, onNavigate }: Props) {
  const [hovered, setHovered] = useState<number | null>(null);

  return (
    <div className="fixed right-6 top-1/2 -translate-y-1/2 z-40 flex flex-col items-end gap-0">
      <Link to="/" className="text-[9px] text-dim tracking-[0.1em] hover:text-peach transition-colors mb-4">
        ← BACK
      </Link>

      <div className="relative flex flex-col items-center">
        {/* connecting line */}
        <div className="absolute top-0 bottom-0 w-px bg-paper3" style={{ right: 2.5 }} />

        {sections.map((label, i) => (
          <button
            key={i}
            onClick={() => onNavigate(i)}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}
            className="relative flex items-center gap-3 py-2 group"
          >
            {/* label on hover */}
            <span
              className={`text-[9px] tracking-[0.12em] whitespace-nowrap transition-all duration-200 ${
                hovered === i ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-2'
              } ${activeSection === i ? 'text-coral' : 'text-dim'}`}
            >
              {label}
            </span>

            {/* dot */}
            <div
              className={`w-[6px] h-[6px] relative z-10 transition-all duration-200 ${
                activeSection === i ? 'bg-coral' : 'bg-dim'
              }`}
              style={activeSection === i ? { boxShadow: '0 0 6px rgba(217,119,87,0.5)' } : {}}
            />
          </button>
        ))}
      </div>
    </div>
  );
}
