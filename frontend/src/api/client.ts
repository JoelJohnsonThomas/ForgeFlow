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

// ---- Endpoints ------------------------------------------------------------

export const api = {
  health: () => request<Health>('/health'),
  metricsSummary: () => request<MetricsSummary>('/metrics/'),
  evaluationSummary: () => request<EvaluationSummary>('/metrics/evaluation'),
  recentRuns: (limit = 20) => request<RecentRun[]>(`/metrics/runs?limit=${limit}`),
  costBreakdown: (days = 7) => request<unknown>(`/metrics/cost?days=${days}`),
  auditStats: (days = 7) => request<unknown>(`/audit/stats?days=${days}`),
}
