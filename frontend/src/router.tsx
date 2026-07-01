/* eslint-disable react-refresh/only-export-components --
   This is a router module: it intentionally exports route config (`router`)
   alongside the <Router/> component. Fast-refresh of a route file isn't
   meaningful, so the rule doesn't apply here. */
import { Suspense, lazy } from 'react'
import type { ComponentType, FunctionComponent } from 'react'
import {
  Outlet,
  RouterProvider,
  createRootRoute,
  createRoute,
  createRouter,
} from '@tanstack/react-router'
import { AppShell } from './components/AppShell'
// LandingPage is the first paint — keep it eager so it isn't behind a chunk fetch.
import { LandingPage } from './views/LandingPage'

// Everything below the landing page is code-split: each view ships as its own
// chunk and loads on navigation, keeping the initial bundle small. (Before this,
// every view was eagerly imported into one 547 kB chunk.)
const lazyView = (
  loader: () => Promise<Record<string, ComponentType>>,
  name: string,
): FunctionComponent =>
  lazy(async () => ({ default: (await loader())[name] })) as unknown as FunctionComponent

const ArchitecturePage = lazyView(() => import('./views/ArchitecturePage'), 'ArchitecturePage')
const DesignHubPage = lazyView(() => import('./views/DesignHubPage'), 'DesignHubPage')
const DesignSystemPage = lazyView(() => import('./views/DesignSystemPage'), 'DesignSystemPage')
const DocsIndexPage = lazyView(() => import('./views/DocsPage'), 'DocsIndexPage')
const DocsArticlePage = lazyView(() => import('./views/DocsPage'), 'DocsArticlePage')
const OverviewView = lazyView(() => import('./views/OverviewView'), 'OverviewView')
const LiveRunsView = lazyView(() => import('./views/LiveRunsView'), 'LiveRunsView')
const ApprovalsView = lazyView(() => import('./views/ApprovalsView'), 'ApprovalsView')
const AgentsView = lazyView(() => import('./views/AgentsView'), 'AgentsView')
const CostView = lazyView(() => import('./views/CostView'), 'CostView')
const AuditView = lazyView(() => import('./views/AuditView'), 'AuditView')
const MemoryView = lazyView(() => import('./views/MemoryView'), 'MemoryView')
const EvaluationsView = lazyView(() => import('./views/EvaluationsView'), 'EvaluationsView')
const WorkflowsView = lazyView(() => import('./views/WorkflowsView'), 'WorkflowsView')
const ClustersView = lazyView(() => import('./views/ClustersView'), 'ClustersView')
const ToolsView = lazyView(() => import('./views/ToolsView'), 'ToolsView')
const MarketplaceView = lazyView(() => import('./views/MarketplaceView'), 'MarketplaceView')
const RbacView = lazyView(() => import('./views/RbacView'), 'RbacView')

function RouteFallback() {
  return <div style={{ padding: 24, color: 'var(--fg-muted)', fontFamily: 'var(--font-mono)' }}>loading…</div>
}

// Root renders <Outlet/> under a single Suspense boundary — it catches every
// lazy child below (landing chrome stays eager).
const rootRoute = createRootRoute({
  component: () => (
    <Suspense fallback={<RouteFallback />}>
      <Outlet />
    </Suspense>
  ),
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

const designHubRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/design-hub',
  component: DesignHubPage,
})

const designSystemRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/design-system',
  component: DesignSystemPage,
})

const docsIndexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/docs',
  component: DocsIndexPage,
})

const docsArticleRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/docs/$slug',
  component: DocsArticlePage,
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

function child(path: string, Component: FunctionComponent) {
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
  designHubRoute,
  designSystemRoute,
  docsIndexRoute,
  docsArticleRoute,
  consoleLayoutRoute.addChildren(consoleChildren),
])

export const router = createRouter({ routeTree })

export function Router() {
  return <RouterProvider router={router} />
}
