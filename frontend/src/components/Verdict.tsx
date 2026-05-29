const styles: Record<string, string> = {
  pass: 'text-green border-green/30 bg-green/8',
  fail: 'text-red border-red/30 bg-red/8',
  warning: 'text-amber border-amber/30 bg-amber/8',
};

const glows: Record<string, string> = {
  pass: '0 0 10px rgba(125,204,138,0.25)',
  fail: '0 0 10px rgba(204,95,95,0.25)',
  warning: '0 0 10px rgba(204,170,68,0.25)',
};

const labels: Record<string, string> = {
  pass: 'VERIFIED',
  fail: 'FAILED',
  warning: 'WARNING',
};

export default function Verdict({ verdict }: { verdict: string }) {
  return (
    <span
      className={`inline-flex items-center gap-2 px-3 py-1 border text-[11px] tracking-[0.14em] font-bold ${styles[verdict] || ''}`}
      style={{ boxShadow: glows[verdict] || '' }}
    >
      <span
        className="w-1.5 h-1.5 bg-current"
        style={{ boxShadow: `0 0 4px currentColor` }}
      />
      {labels[verdict] || verdict}
    </span>
  );
}
