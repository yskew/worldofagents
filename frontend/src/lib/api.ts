const BASE = import.meta.env.VITE_API_URL || '/api';

let _getToken: (() => Promise<string | null>) | null = null;

export function setTokenGetter(fn: () => Promise<string | null>) {
  _getToken = fn;
}

async function request<T>(path: string, opts?: RequestInit, auth = false): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((opts?.headers as Record<string, string>) || {}),
  };

  if (auth && _getToken) {
    const token = await _getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const res = await fetch(`${BASE}${path}`, { ...opts, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface Agent {
  agent_id: string;
  name: string;
  description: string | null;
  status: string;
  signature_summary: { tool_count: number; sequence_length: number } | null;
  created_at: string;
  updated_at: string;
}

export interface RegisterResponse {
  agent_id: string;
  agent_key: string;
  name: string;
  status: string;
}

export interface VerifyResponse {
  verified: boolean;
  similarity_score: number;
  verdict: 'pass' | 'fail' | 'warning';
  token: string | null;
  breakdown: {
    jsd_score: number;
    cosine_score: number;
    markov_score: number;
    stats_score: number;
  } | null;
}

export interface CompareResponse {
  similarity_score: number;
  verdict: 'pass' | 'fail' | 'warning';
  breakdown: {
    jsd_score: number;
    cosine_score: number;
    markov_score: number;
    stats_score: number;
  };
}

export interface PublicProfile {
  agent_id: string;
  name: string;
  description: string | null;
  status: string;
  owner_display_name: string;
  created_at: string;
  verification_count: number;
  avg_similarity_score: number | null;
}

export interface TrajectoryStep {
  type: 'tool_call' | 'message' | 'action';
  name?: string;
  content?: string;
  timestamp?: string;
  metadata?: Record<string, unknown>;
}

export const api = {
  // open endpoints — no auth
  health: () => request<{ status: string }>('/health'),
  verify: (data: { agent_id: string; agent_key: string; trajectory: TrajectoryStep[] }) =>
    request<VerifyResponse>('/verify', { method: 'POST', body: JSON.stringify(data) }),
  compare: (trajectory_a: TrajectoryStep[], trajectory_b: TrajectoryStep[]) =>
    request<CompareResponse>('/compare', { method: 'POST', body: JSON.stringify({ trajectory_a, trajectory_b }) }),
  publicProfile: (id: string) => request<PublicProfile>(`/agents/${id}/public`),
  jwks: () => request<{ keys: unknown[] }>('/.well-known/jwks.json'),

  // authenticated endpoints — send Clerk token
  listAgents: () => request<{ agents: Agent[] }>('/agents', undefined, true),
  getAgent: (id: string) => request<Agent>(`/agents/${id}`, undefined, true),
  registerAgent: (data: { name: string; description?: string; sample_trajectory: TrajectoryStep[] }) =>
    request<RegisterResponse>('/agents/register', { method: 'POST', body: JSON.stringify(data) }, true),
  deleteAgent: (id: string) => request<void>(`/agents/${id}`, { method: 'DELETE' }, true),
  refineAgent: (id: string, trajectory: TrajectoryStep[]) =>
    request<Agent>(`/agents/${id}/refine`, { method: 'POST', body: JSON.stringify({ trajectory }) }, true),
  rotateKey: (id: string) =>
    request<{ agent_key: string }>(`/agents/${id}/rotate-key`, { method: 'POST' }, true),
};
