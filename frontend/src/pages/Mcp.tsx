import { useState, useEffect, useCallback } from 'react';
import { api, type McpTool, type McpCallResult } from '../lib/api';
import McpResult from '../components/McpResult';

export default function Mcp() {
  const [tools, setTools] = useState<McpTool[]>([]);
  const [token, setToken] = useState('');
  const [tool, setTool] = useState('');
  const [args, setArgs] = useState('{}');
  const [result, setResult] = useState<McpCallResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.mcpTools().then((r) => {
      setTools(r.tools);
      if (r.tools[0]) setTool(r.tools[0].name);
    }).catch(() => {});
  }, []);

  const call = useCallback(async () => {
    setError(null);
    setResult(null);
    let parsedArgs: Record<string, unknown>;
    try {
      parsedArgs = JSON.parse(args);
    } catch (e) {
      setError(`Invalid arguments JSON: ${(e as Error).message}`);
      return;
    }
    setLoading(true);
    try {
      setResult(await api.mcpCall(token, tool, parsedArgs));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [token, tool, args]);

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-4">
        <div>
          <h1 className="font-[Silkscreen] text-coral text-[18px] tracking-[0.14em]">MCP SERVER</h1>
          <p className="text-[11px] text-muted mt-1">
            Reference MCP authorization server. Tool calls require a valid attestation token and a per-agent tool allowlist.
          </p>
        </div>
        <textarea className="w-full h-24 bg-paper2 border border-paper3 px-3 py-2 text-[11px] text-ink font-mono"
          placeholder="attestation token (from /verify)" value={token} onChange={e => setToken(e.target.value)} />
        <select className="w-full bg-paper2 border border-paper3 px-3 py-2 text-[12px] text-ink"
          value={tool} onChange={e => setTool(e.target.value)}>
          {tools.map(t => <option key={t.name} value={t.name}>{t.name} — {t.description}</option>)}
        </select>
        <textarea className="w-full h-20 bg-paper2 border border-paper3 px-3 py-2 text-[11px] text-ink font-mono"
          value={args} onChange={e => setArgs(e.target.value)} />
        <button onClick={call} disabled={loading || !token}
          className="w-full bg-coral text-paper py-2 text-[11px] font-bold tracking-[0.14em] disabled:opacity-50">
          {loading ? 'CALLING…' : 'CALL TOOL'}
        </button>
      </div>
      <div>
        <McpResult result={result} error={error} />
      </div>
    </div>
  );
}
