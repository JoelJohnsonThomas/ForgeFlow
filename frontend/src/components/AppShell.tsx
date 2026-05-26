import type { ReactNode } from 'react'
import { useMatchRoute, useNavigate } from '@tanstack/react-router'
import { Topbar } from './Topbar'
import { Sidebar, type ViewId } from './Sidebar'

const VIEW_PATHS: Record<ViewId, string> = {
  overview: '/',
  runs: '/runs',
  approvals: '/approvals',
  agents: '/agents',
  memory: '/memory',
  cost: '/cost',
  evals: '/evals',
  workflows: '/workflows',
  tools: '/tools',
  marketplace: '/marketplace',
  audit: '/audit',
  clusters: '/clusters',
  rbac: '/rbac',
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
