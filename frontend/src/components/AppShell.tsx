import type { ReactNode } from 'react'
import { useMatchRoute, useNavigate } from '@tanstack/react-router'
import { Topbar } from './Topbar'
import { Sidebar, type ViewId } from './Sidebar'

const VIEW_PATHS: Record<ViewId, string> = {
  overview: '/console',
  runs: '/console/runs',
  approvals: '/console/approvals',
  agents: '/console/agents',
  memory: '/console/memory',
  cost: '/console/cost',
  evals: '/console/evals',
  workflows: '/console/workflows',
  tools: '/console/tools',
  marketplace: '/console/marketplace',
  audit: '/console/audit',
  clusters: '/console/clusters',
  rbac: '/console/rbac',
}

function useActiveView(): ViewId {
  const match = useMatchRoute()
  for (const [view, path] of Object.entries(VIEW_PATHS) as [ViewId, string][]) {
    if (match({ to: path, fuzzy: false })) return view
  }
  return 'overview'
}

export function AppShell({ children }: { children: ReactNode }) {
  const active = useActiveView()
  const navigate = useNavigate()
  return (
    <div className="app">
      <Topbar />
      <Sidebar
        active={active}
        onSelect={(id) => navigate({ to: VIEW_PATHS[id] })}
      />
      <main className="main">{children}</main>
    </div>
  )
}
