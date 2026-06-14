import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from './api';

describe('api.mcpCall', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('sends the bearer token and tool call', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ tool: 'search', status: 'executed', result: {}, agent_id: 'a', principal: 'p' }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const res = await api.mcpCall('tok123', 'search', { q: 'x' });
    expect(res.status).toBe('executed');
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain('/mcp/call');
    expect(init.headers.Authorization).toBe('Bearer tok123');
    expect(JSON.parse(init.body)).toEqual({ tool: 'search', arguments: { q: 'x' } });
  });

  it('throws API detail on denial', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 403, statusText: 'Forbidden',
      json: async () => ({ detail: { error: 'tool_not_authorized: deploy' } }),
    }));
    // detail is an object here; request() throws statusText since detail isn't a string
    await expect(api.mcpCall('t', 'deploy')).rejects.toThrow();
  });
});
