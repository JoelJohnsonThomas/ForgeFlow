import type { ReactNode } from 'react'
import { useMatchRoute, useNavigate } from '@tanstack/react-router'
import { Topbar } from './Topbar'
import { AuthBanner } from './AuthControls'
import { Sidebar, type ViewId } from './Sidebar'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

const VIEW_TITLES: Record<ViewId, string> = {
  overview: 'Overview',
  runs: 'Live runs',
  approvals: 'Approvals',
  agents: 'Agents',
  memory: 'Memory',
  cost: 'Cost & spend',
  evals: 'Evaluations',
  workflows: 'Workflows',
  tools: 'Tools · MCP',
  marketplace: 'Marketplace',
  audit: 'Audit log',
  clusters: 'Clusters',
  rbac: 'RBAC & secrets',
}

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
  useDocumentTitle(`Console · ${VIEW_TITLES[active]}`)
  return (
    <div className="app">
      <a href="#main-content" className="skip-link">Skip to content</a>
      <Topbar />
      <Sidebar
        active={active}
        onSelect={(id) => navigate({ to: VIEW_PATHS[id] })}
      />
      <main className="main" id="main-content" tabIndex={-1}>
        <AuthBanner />
        {children}
      </main>
    </div>
  )
}
