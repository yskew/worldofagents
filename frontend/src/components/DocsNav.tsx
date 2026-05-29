import { Link } from 'react-router-dom';

const sections = [
  { label: 'OVERVIEW', icon: '◆' },
  { label: 'PROBLEM', icon: '⚠' },
  { label: 'INSIGHT', icon: '◧' },
  { label: 'SIGNATURES', icon: '◎' },
  { label: 'ARCHITECTURE', icon: '⬡' },
  { label: 'SECURITY', icon: '◈' },
  { label: 'LANDSCAPE', icon: '▦' },
  { label: 'ROADMAP', icon: '▸' },
];

interface Props {
  activeSection: number;
  onNavigate: (index: number) => void;
}

export default function DocsNav({ activeSection, onNavigate }: Props) {
  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-paper/90 backdrop-blur-sm border-t border-paper3">
      <div className="max-w-[1200px] mx-auto px-4 h-12 flex items-center justify-between">
        <Link to="/" className="text-[10px] text-dim tracking-[0.1em] hover:text-peach transition-colors shrink-0">
          ← EXIT
        </Link>

        <div className="flex items-center gap-1 overflow-x-auto">
          {sections.map((s, i) => (
            <button
              key={i}
              onClick={() => onNavigate(i)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-[10px] tracking-[0.1em] whitespace-nowrap transition-all ${
                activeSection === i
                  ? 'text-coral bg-coral/10 border border-coral/25'
                  : 'text-dim hover:text-peach border border-transparent'
              }`}
            >
              <span className="text-[9px]">{s.icon}</span>
              {s.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[9px] text-dim tracking-[0.1em]">
            {String(activeSection + 1).padStart(2, '0')}/{String(sections.length).padStart(2, '0')}
          </span>
        </div>
      </div>
    </div>
  );
}
