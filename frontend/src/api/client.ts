/**
 * Tiny typed fetch wrapper for the ForgeFlow FastAPI backend.
 * In dev, requests go through Vite's proxy (/api → http://localhost:8000).
 * In prod, nginx reverse-proxies /api → http://api:8000 inside docker-compose.
 */

const BASE = '/api'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'content-type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new ApiError(res.status, `${res.status} ${res.statusText}: ${body.slice(0, 200)}`)
  }
  return res.json() as Promise<T>
}

// ---- Types ----------------------------------------------------------------

export type MetricsSummary = {
  total_runs: number
  success_rate: number
  avg_latency_ms: number
  avg_cost_usd: number
  total_cost_usd: number
}

export type EvaluationSummary = {
  avg_faithfulness: number
  avg_relevance: number
  avg_coherence: number
  hallucination_rate: number
  sample_count: number
}

export type RecentRun = {
  run_id: string
  thread_id: string
  workflow_type: string
  status: string
  created_at: string | null
  completed_at: string | null
  total_tokens: number
  total_cost_usd: number
}

export type Health = {
  status: string
  database: string
  graph: string
}

export type Approval = {
  token: string
  run_id: string
  workflow_id: string
  proposal: Record<string, unknown>
  status: string
  requested_at: string
  resolved_at: string | null
  resolved_by: string | null
  resolution_note: string | null
  expires_at: string | null
}

export type Agent = {
  agent_id: string
  name: string
  endpoint: string
  capabilities?: string[]
  metadata?: Record<string, unknown>
}

export type MemoryResult = {
  id: string
  content: string
  similarity: number
  namespace: string
  metadata: Record<string, unknown>
}

export type AuditRow = {
  id: number
  timestamp: string | null
  user_id: string | null
  role: string | null
  action: string | null
  resource: string | null
  resource_id: string | null
  outcome: string | null
  request_id: string | null
  metadata: Record<string, unknown>
}

export type AuditSearchResponse = {
  total: number
  items: AuditRow[]
  limit: number
  offset: number
  error?: string
}

export type AuditStats = {
  window_days: number
  total: number
  denied: number
  errors: number
  distinct_users: number
  top_resources: { resource: string; hits: number }[]
  error?: string
}

export type CostByAgentRow = {
  agent: string
  total_cost: number
  total_tokens: number
  runs: number
}

export type CostByWorkflowRow = {
  workflow_type: string
  total_cost: number
  total_tokens: number
  runs: number
}

export type TopRun = {
  run_id: string
  workflow_type: string
  total_cost_usd: number
  total_tokens: number
  created_at: string | null
}

// ---- Endpoints ------------------------------------------------------------

export const api = {
  health: () => request<Health>('/health'),
  metricsSummary: () => request<MetricsSummary>('/metrics/'),
  evaluationSummary: () => request<EvaluationSummary>('/metrics/evaluation'),
  recentRuns: (limit = 20) => request<RecentRun[]>(`/metrics/runs?limit=${limit}`),
  costByAgent: (days = 7) => request<CostByAgentRow[]>(`/metrics/cost?days=${days}`),
  costByWorkflow: (days = 7) =>
    request<CostByWorkflowRow[]>(`/metrics/cost/by_workflow_type?days=${days}`),
  topRuns: (days = 7, limit = 10) =>
    request<TopRun[]>(`/metrics/cost/top_runs?days=${days}&limit=${limit}`),
  approvalsPending: () => request<Approval[]>('/approvals/pending'),
  approveApproval: (token: string, note = '') =>
    request<{ status: string; thread_id: string }>(`/approvals/${token}/approve`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),
  rejectApproval: (token: string, note = '') =>
    request<{ status: string }>(`/approvals/${token}/reject`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),
  agents: () => request<Agent[]>('/agents/'),
  agentsDispatch: () => request<unknown>('/agents/dispatch'),
  memorySearch: (q: string, k = 8, namespace?: string) => {
    const u = new URLSearchParams({ q, k: String(k) })
    if (namespace) u.set('namespace', namespace)
    return request<MemoryResult[]>(`/memory/search?${u}`)
  },
  auditSearch: (params: { limit?: number; offset?: number; action?: string } = {}) => {
    const u = new URLSearchParams()
    if (params.limit) u.set('limit', String(params.limit))
    if (params.offset) u.set('offset', String(params.offset))
    if (params.action) u.set('action', params.action)
    const qs = u.toString()
    return request<AuditSearchResponse>(`/audit/search${qs ? `?${qs}` : ''}`)
  },
  auditStats: (days = 7) => request<AuditStats>(`/audit/stats?days=${days}`),
}
