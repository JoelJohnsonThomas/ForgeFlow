import {
  Outlet,
  RouterProvider,
  createRootRoute,
  createRoute,
  createRouter,
} from '@tanstack/react-router'
import { AppShell } from './components/AppShell'
import { OverviewView } from './views/OverviewView'
import { PlaceholderView } from './views/PlaceholderView'

const rootRoute = createRootRoute({
  component: () => (
    <AppShell>
      <Outlet />
    </AppShell>
  ),
})

const overviewRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: OverviewView,
})

const placeholder = (path: string, title: string, sub?: string) =>
  createRoute({
    getParentRoute: () => rootRoute,
    path,
    component: () => <PlaceholderView title={title} sub={sub} />,
  })

const routeTree = rootRoute.addChildren([
  overviewRoute,
  placeholder('/runs', 'Live runs', '12 active · Gantt + event stream coming in Phase 3'),
  placeholder('/approvals', 'Approvals', '4 awaiting decision'),
  placeholder('/agents', 'Agents', 'Topology + per-agent metrics'),
  placeholder('/memory', 'Memory', 'pgvector recall · namespaces · TTL'),
  placeholder('/cost', 'Cost & spend', 'per-workflow burn · budget alerts'),
  placeholder('/evals', 'Evaluations', 'LLM-as-judge · regression checks'),
  placeholder('/workflows', 'Workflows', 'Builder · templates · versions'),
  placeholder('/tools', 'Tools · MCP', '14 registered tools · 4 providers'),
  placeholder('/marketplace', 'Marketplace', 'Community workflow templates'),
  placeholder('/audit', 'Audit log', 'Compliance · search · exports'),
  placeholder('/clusters', 'Clusters', 'Pod health across regions'),
  placeholder('/rbac', 'RBAC & secrets', 'Roles · policy bundles · secret rotation'),
])

export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

export function Router() {
  return <RouterProvider router={router} />
}
