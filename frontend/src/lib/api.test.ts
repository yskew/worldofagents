import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api, decodeSet } from './api';

function b64url(obj: unknown): string {
  return btoa(JSON.stringify(obj)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

describe('decodeSet', () => {
  it('decodes a CAEP SET into a display event', () => {
    const token = `h.${b64url({
      events: {
        'https://worldofagents.dev/caep/event-type/behavioral-anomaly': {
          subject: { format: 'email', email: 'alice@example.com' },
          agent_name: 'coder',
          reason: 'verification_failed',
          similarity_score: 0.3,
        },
      },
    })}.sig`;
    const ev = decodeSet('jti1', token);
    expect(ev.type).toBe('behavioral-anomaly');
    expect(ev.subject).toBe('alice@example.com');
    expect(ev.agentName).toBe('coder');
    expect(ev.score).toBe(0.3);
  });
});

describe('api.ssfPoll', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('POSTs poll request and returns sets', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => ({ sets: { jti1: 'a.b.c' } }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const res = await api.ssfPoll(10, ['old']);
    expect(res.sets.jti1).toBe('a.b.c');
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain('/ssf/poll');
    expect(JSON.parse(init.body)).toEqual({ maxEvents: 10, ack: ['old'] });
  });
});
