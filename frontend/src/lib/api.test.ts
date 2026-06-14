import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from './api';

describe('attestation api', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('attestStart posts agent credentials', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => ({ session_id: 'sess1' }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const res = await api.attestStart('agent1', 'key1');
    expect(res.session_id).toBe('sess1');
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain('/attest/start');
    expect(JSON.parse(init.body)).toEqual({ agent_id: 'agent1', agent_key: 'key1' });
  });

  it('attestStep posts a window and returns status', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ window_similarity: 0.2, cusum: 0.65, status: 'alarm', windows: 2 }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const res = await api.attestStep('sess1', [{ type: 'tool_call', name: 'x' }]);
    expect(res.status).toBe('alarm');
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain('/attest/step');
    expect(JSON.parse(init.body).session_id).toBe('sess1');
  });
});
