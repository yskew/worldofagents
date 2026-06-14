import type { McpCallResult } from '../lib/api';

interface Props {
  result?: McpCallResult | null;
  error?: string | null;
}

export default function McpResult({ result, error }: Props) {
  if (error) {
    return (
      <div className="border border-red/40 p-3" data-testid="mcp-denied">
        <div className="text-[11px] font-bold text-red tracking-[0.12em]">DENIED</div>
        <div className="text-[11px] text-ink mt-1">{error}</div>
      </div>
    );
  }
  if (!result) {
    return (
      <div className="text-[11px] text-dim border border-paper3 p-6 text-center">
        call a tool to see the authorization decision
      </div>
    );
  }
  return (
    <div className="border border-green/40 p-3 space-y-1" data-testid="mcp-allowed">
      <div className="text-[11px] font-bold text-green tracking-[0.12em]">
        {result.status.toUpperCase()}: {result.tool}
      </div>
      <div className="text-[10px] text-dim">
        agent {result.agent_id?.slice(0, 8)} acting for {result.principal}
      </div>
      <pre className="text-[10px] text-muted overflow-x-auto">{JSON.stringify(result.result, null, 2)}</pre>
    </div>
  );
}
