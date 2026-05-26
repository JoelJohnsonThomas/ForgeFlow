import {
  Outlet,
  RouterProvider,
  createRootRoute,
  createRoute,
  createRouter,
} from '@tanstack/react-router'
import { AppShell } from './components/AppShell'
import { LandingPage } from './views/LandingPage'
import { ArchitecturePage } from './views/ArchitecturePage'
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

// Root just renders <Outlet/> — the landing page renders its own chrome,
// the console subtree wraps its routes in AppShell.
const rootRoute = createRootRoute({
  component: () => <Outlet />,
})

const landingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: LandingPage,
})

const architectureRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/architecture',
  component: ArchitecturePage,
})

// Console layout — every child gets the topbar + sidebar shell.
const consoleLayoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/console',
  component: () => (
    <AppShell>
      <Outlet />
    </AppShell>
  ),
})

function child(path: string, Component: () => React.ReactElement) {
  return createRoute({ getParentRoute: () => consoleLayoutRoute, path, component: Component })
}

const consoleChildren = [
  child('/', OverviewView),
  child('/runs', LiveRunsView),
  child('/approvals', ApprovalsView),
  child('/agents', AgentsView),
  child('/memory', MemoryView),
  child('/cost', CostView),
  child('/evals', EvaluationsView),
  child('/workflows', WorkflowsView),
  child('/tools', ToolsView),
  child('/marketplace', MarketplaceView),
  child('/audit', AuditView),
  child('/clusters', ClustersView),
  child('/rbac', RbacView),
]

const routeTree = rootRoute.addChildren([
  landingRoute,
  architectureRoute,
  consoleLayoutRoute.addChildren(consoleChildren),
])

export const router = createRouter({ routeTree })

export function Router() {
  return <RouterProvider router={router} />
}
