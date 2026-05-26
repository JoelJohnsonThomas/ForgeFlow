import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'

export function useMetricsSummary() {
  return useQuery({
    queryKey: ['metrics', 'summary'],
    queryFn: api.metricsSummary,
    refetchInterval: 15_000,
  })
}

export function useEvaluationSummary() {
  return useQuery({
    queryKey: ['metrics', 'evaluation'],
    queryFn: api.evaluationSummary,
    refetchInterval: 60_000,
  })
}

export function useRecentRuns(limit = 20) {
  return useQuery({
    queryKey: ['metrics', 'runs', limit],
    queryFn: () => api.recentRuns(limit),
    refetchInterval: 10_000,
  })
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    refetchInterval: 30_000,
  })
}

export function useApprovalsPending() {
  return useQuery({
    queryKey: ['approvals', 'pending'],
    queryFn: api.approvalsPending,
    refetchInterval: 10_000,
  })
}

export function useApproveMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ token, note }: { token: string; note?: string }) =>
      api.approveApproval(token, note ?? ''),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['approvals'] }),
  })
}

export function useRejectMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ token, note }: { token: string; note?: string }) =>
      api.rejectApproval(token, note ?? ''),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['approvals'] }),
  })
}

export function useAgents() {
  return useQuery({
    queryKey: ['agents'],
    queryFn: api.agents,
    refetchInterval: 30_000,
  })
}

export function useMemorySearch(q: string, namespace?: string) {
  return useQuery({
    queryKey: ['memory', 'search', q, namespace ?? null],
    queryFn: () => api.memorySearch(q, 8, namespace),
    enabled: q.trim().length > 0,
  })
}

export function useAuditSearch(action?: string) {
  return useQuery({
    queryKey: ['audit', 'search', action ?? null],
    queryFn: () => api.auditSearch({ limit: 50, action }),
    refetchInterval: 20_000,
  })
}

export function useAuditStats(days = 7) {
  return useQuery({
    queryKey: ['audit', 'stats', days],
    queryFn: () => api.auditStats(days),
    refetchInterval: 60_000,
  })
}

export function useCostByAgent(days = 7) {
  return useQuery({
    queryKey: ['cost', 'by_agent', days],
    queryFn: () => api.costByAgent(days),
    refetchInterval: 60_000,
  })
}

export function useCostByWorkflow(days = 7) {
  return useQuery({
    queryKey: ['cost', 'by_workflow', days],
    queryFn: () => api.costByWorkflow(days),
    refetchInterval: 60_000,
  })
}

export function useTopRuns(days = 7, limit = 10) {
  return useQuery({
    queryKey: ['cost', 'top_runs', days, limit],
    queryFn: () => api.topRuns(days, limit),
    refetchInterval: 60_000,
  })
}
