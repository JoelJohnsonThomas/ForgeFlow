/**
 * Tiny typed fetch wrapper for the ForgeFlow FastAPI backend.
 * In dev, requests go through Vite's proxy (/api → http://localhost:8000).
 * In prod, nginx reverse-proxies /api → http://api:8000 inside docker-compose.
 */

const BASE = '/api'
const TOKEN_KEY = 'forgeflow.jwt'
const USER_KEY = 'forgeflow.user'
const ROLE_KEY = 'forgeflow.role'

/** Fired on window whenever the stored session changes (sign-in/out, 401). */
export const AUTH_CHANGED_EVENT = 'ff-auth-changed'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

// --- token storage ---------------------------------------------------------
// SECURITY_AUDIT.md C-2: nginx no longer injects an admin service token. The
// SPA stores the user's JWT in sessionStorage (cleared on tab close, not
// shared between tabs/origins) and attaches it as Authorization on every
// request. Migrate to HttpOnly+Secure cookies + CSRF token once a real
// session backend lands.

export type Session = { userId: string; role: string }

export function setToken(token: string | null): void {
  if (typeof window === 'undefined') return
  if (token) {
    window.sessionStorage.setItem(TOKEN_KEY, token)
  } else {
    window.sessionStorage.removeItem(TOKEN_KEY)
    window.sessionStorage.removeItem(USER_KEY)
    window.sessionStorage.removeItem(ROLE_KEY)
  }
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT))
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return window.sessionStorage.getItem(TOKEN_KEY)
}

/** Who is signed in (display only — authorization is enforced server-side). */
export function getSession(): Session | null {
  if (typeof window === 'undefined') return null
  if (!window.sessionStorage.getItem(TOKEN_KEY)) return null
  return {
    userId: window.sessionStorage.getItem(USER_KEY) ?? 'unknown',
    role: window.sessionStorage.getItem(ROLE_KEY) ?? 'unknown',
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'content-type': 'application/json',
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (token) headers['authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...init, headers })
  if (res.status === 401) {
    // Stale or revoked token — clear it so the next interaction re-prompts.
    setToken(null)
  }
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new ApiError(res.status, `${res.status} ${res.statusText}: ${body.slice(0, 200)}`)
  }
  return res.json() as Promise<T>
}

// --- auth helpers ----------------------------------------------------------

export type LoginPayload = {
  user_id: string
  password: string
  mfa_code?: string
  workspace_id?: string
  ttl_hours?: number
}

export async function login(payload: LoginPayload): Promise<{ access_token: string; role: string }> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new ApiError(res.status, `${res.status} ${res.statusText}: ${body.slice(0, 200)}`)
  }
  const data = (await res.json()) as { access_token: string; role: string }
  window.sessionStorage.setItem(USER_KEY, payload.user_id)
  window.sessionStorage.setItem(ROLE_KEY, data.role)
  setToken(data.access_token)
  return data
}

export async function logout(): Promise<void> {
  const token = getToken()
  setToken(null)
  if (!token) return
  await fetch(`${BASE}/auth/logout`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ token }),
  }).catch(() => undefined)
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
  // The API serialises the proposal under `payload`; `proposal` is the
  // normalised alias the UI reads (mapped in approvalsPending()).
  payload?: Record<string, unknown>
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
  total_cost_usd: number | null
  total_tokens: number | null
  created_at: string | null
}

// Raw per-day rows as the API returns them (metrics_store groups by date).
type RawCostByAgent = { agent: string | null; date?: string; total_cost_usd?: number | null; run_count?: number }
type RawCostByWorkflow = {
  workflow_type: string | null
  date?: string
  total_cost_usd?: number | null
  total_tokens?: number | null
  run_count?: number
}

// ---- Endpoints ------------------------------------------------------------

export const api = {
  health: () => request<Health>('/health'),
  metricsSummary: () => request<MetricsSummary>('/metrics/'),
  evaluationSummary: () => request<EvaluationSummary>('/metrics/evaluation'),
  recentRuns: (limit = 20) => request<RecentRun[]>(`/metrics/runs?limit=${limit}`),
  // The API returns one row per (agent|workflow, day); the console shows
  // window totals, so aggregate here and map run_count/total_cost_usd onto
  // the row shapes the views render.
  costByAgent: async (days = 7): Promise<CostByAgentRow[]> => {
    const rows = await request<RawCostByAgent[]>(`/metrics/cost?days=${days}`)
    const acc = new Map<string, CostByAgentRow>()
    for (const r of rows) {
      const agent = r.agent ?? 'unknown'
      const cur = acc.get(agent) ?? { agent, total_cost: 0, total_tokens: 0, runs: 0 }
      cur.total_cost += Number(r.total_cost_usd ?? 0)
      cur.runs += Number(r.run_count ?? 0)
      acc.set(agent, cur)
    }
    return [...acc.values()].sort((a, b) => b.total_cost - a.total_cost)
  },
  costByWorkflow: async (days = 7): Promise<CostByWorkflowRow[]> => {
    const rows = await request<RawCostByWorkflow[]>(`/metrics/cost/by_workflow_type?days=${days}`)
    const acc = new Map<string, CostByWorkflowRow>()
    for (const r of rows) {
      const wf = r.workflow_type ?? 'unknown'
      const cur = acc.get(wf) ?? { workflow_type: wf, total_cost: 0, total_tokens: 0, runs: 0 }
      cur.total_cost += Number(r.total_cost_usd ?? 0)
      cur.total_tokens += Number(r.total_tokens ?? 0)
      cur.runs += Number(r.run_count ?? 0)
      acc.set(wf, cur)
    }
    return [...acc.values()].sort((a, b) => b.total_cost - a.total_cost)
  },
  topRuns: (days = 7, limit = 10) =>
    request<TopRun[]>(`/metrics/cost/top_runs?days=${days}&limit=${limit}`),
  approvalsPending: async () => {
    const rows = await request<Approval[]>('/approvals/pending')
    // API sends the proposal under `payload`; normalise to `proposal` so the
    // Approvals view (which reads approval.proposal) renders the details.
    return rows.map((r) => ({ ...r, proposal: r.payload ?? r.proposal }))
  },
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
