import { useMatchRoute } from '@tanstack/react-router'
import { IconBell, IconChevronDown, IconHelp, IconSearch } from './icons'

// Map console routes → breadcrumb segments. The last entry is the
// "current page" (rendered with .cur styling). Keeps crumbs honest
// instead of lying with the hardcoded wf_8K42n placeholder.
const CRUMBS: { match: string; segments: string[] }[] = [
  { match: '/console/runs', segments: ['console', 'live runs'] },
  { match: '/console/approvals', segments: ['console', 'approvals'] },
  { match: '/console/agents', segments: ['console', 'agents'] },
  { match: '/console/memory', segments: ['console', 'memory'] },
  { match: '/console/cost', segments: ['console', 'cost'] },
  { match: '/console/audit', segments: ['console', 'audit log'] },
  { match: '/console/evals', segments: ['console', 'evaluations'] },
  { match: '/console/workflows', segments: ['console', 'workflows'] },
  { match: '/console/tools', segments: ['console', 'tools'] },
  { match: '/console/marketplace', segments: ['console', 'marketplace'] },
  { match: '/console/clusters', segments: ['console', 'clusters'] },
  { match: '/console/rbac', segments: ['console', 'rbac & secrets'] },
  { match: '/console', segments: ['console', 'overview'] },
]

function useCrumbs(): string[] {
  const match = useMatchRoute()
  for (const c of CRUMBS) {
    if (match({ to: c.match, fuzzy: false })) return c.segments
  }
  return ['console']
}

export function Topbar() {
  const crumbs = useCrumbs()
  return (
    <header className="topbar">
      <a href="/" className="brand" aria-label="ForgeFlow landing">
        <span className="brand-mark" />
        <span className="brand-name">ForgeFlow</span>
      </a>
      <div className="org-pill" title="Workspace switcher — wire to /workspaces when multi-tenant lands">
        <span className="logo" />
        <span>Acme · Sales Ops</span>
        <span className="env">prod-us-east-1</span>
        <IconChevronDown style={{ color: 'var(--fg-muted)', marginLeft: 2 }} />
      </div>
      <nav className="crumbs" aria-label="Breadcrumbs">
        {crumbs.map((seg, i) => {
          const isLast = i === crumbs.length - 1
          return (
            <span key={`${seg}-${i}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              {i > 0 && <span className="sep">/</span>}
              <span className={isLast ? 'cur' : undefined}>{seg}</span>
            </span>
          )
        })}
      </nav>
      <a
        href="/console/audit"
        className="search"
        title="Searches the audit log today; full ⌘K palette is on the roadmap"
        style={{ textDecoration: 'none' }}
      >
        <IconSearch />
        <span className="placeholder">Search runs, agents, audit, memory…</span>
        <span className="kbd">⌘K</span>
      </a>
      <div className="right">
        <a
          href="/api/health"
          target="_blank"
          rel="noopener noreferrer"
          className="status-bar"
          title="API health endpoint"
          style={{ textDecoration: 'none' }}
        >
          <span className="dot live" /> live · /api/health
        </a>
        <a href="/console/approvals" className="btn ghost icon-only" title="Pending approvals" aria-label="Pending approvals">
          <IconBell />
        </a>
        <a
          href="/docs"
          className="btn ghost icon-only"
          title="Documentation"
          aria-label="Open the documentation"
        >
          <IconHelp />
        </a>
        <span className="avatar" title="Signed in · session JWT" aria-label="Signed in via session JWT">JJ</span>
      </div>
    </header>
  )
}
