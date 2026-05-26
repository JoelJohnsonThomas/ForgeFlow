import {
  Outlet,
  RouterProvider,
  createRootRoute,
  createRoute,
  createRouter,
} from '@tanstack/react-router'
import { AppShell } from './components/AppShell'
import { OverviewView } from './views/OverviewView'
import { LiveRunsView } from './views/LiveRunsView'
import { ApprovalsView } from './views/ApprovalsView'
import { AgentsView } from './views/AgentsView'
import { CostView } from './views/CostView'
import { AuditView } from './views/AuditView'
import { MemoryView } from './views/MemoryView'
import { EvaluationsView } from './views/EvaluationsView'
import { WorkflowsView } from './views/WorkflowsView'
import { ClustersView } from './views/ClustersView'
import { ToolsView } from './views/ToolsView'
import { MarketplaceView } from './views/MarketplaceView'
import { RbacView } from './views/RbacView'

const rootRoute = createRootRoute({
  component: () => (
    <AppShell>
      <Outlet />
    </AppShell>
  ),
})

function route(path: string, Component: () => React.ReactElement) {
  return createRoute({ getParentRoute: () => rootRoute, path, component: Component })
}

const routeTree = rootRoute.addChildren([
  route('/', OverviewView),
  route('/runs', LiveRunsView),
  route('/approvals', ApprovalsView),
  route('/agents', AgentsView),
  route('/memory', MemoryView),
  route('/cost', CostView),
  route('/evals', EvaluationsView),
  route('/workflows', WorkflowsView),
  route('/tools', ToolsView),
  route('/marketplace', MarketplaceView),
  route('/audit', AuditView),
  route('/clusters', ClustersView),
  route('/rbac', RbacView),
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
