import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from './api';

describe('api.ingestTelemetry', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('POSTs the telemetry payload and returns the parsed response', async () => {
    const body = {
      source: 'otel',
      ingested_spans: 2,
      mapped_steps: 2,
      summary: { tool_histogram: { search: 1 }, unique_tools: 1, sequence_length: 2, tool_call_ratio: 1, error_rate: 0, mean_interval_s: null },
      applied: true,
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => body,
    });
    vi.stubGlobal('fetch', fetchMock);

    const res = await api.ingestTelemetry({
      agent_id: 'a1', agent_key: 'k1', source: 'otel', spans: [{}, {}], apply: true,
    });

    expect(res.applied).toBe(true);
    expect(res.summary.tool_histogram.search).toBe(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain('/telemetry/ingest');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body).agent_id).toBe('a1');
  });

  it('throws with the API detail on error responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: async () => ({ detail: 'Invalid agent key' }),
    }));
    await expect(
      api.ingestTelemetry({ agent_id: 'a1', agent_key: 'bad', source: 'otel', spans: [{}] }),
    ).rejects.toThrow('Invalid agent key');
  });
});
