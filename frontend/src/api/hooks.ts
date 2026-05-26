import { useQuery } from '@tanstack/react-query'
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
