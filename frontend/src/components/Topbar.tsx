import { IconBell, IconChevronDown, IconHelp, IconSearch } from './icons'

export function Topbar() {
  return (
    <header className="topbar">
      <a className="brand" href="/" aria-label="ForgeFlow home">
        <span className="brand-mark" />
        <span className="brand-name">ForgeFlow</span>
      </a>
      <div className="org-pill" title="Switch workspace">
        <span className="logo" />
        <span>Acme · Sales Ops</span>
        <span className="env">prod-us-east-1</span>
        <IconChevronDown style={{ color: 'var(--fg-muted)', marginLeft: 2 }} />
      </div>
      <div className="crumbs">
        <span>workflows</span>
        <span className="sep">/</span>
        <span>sales_ops</span>
        <span className="sep">/</span>
        <span className="cur">wf_8K42n</span>
      </div>
      <div className="search">
        <IconSearch />
        <span className="placeholder">Search runs, agents, audit, memory…</span>
        <span className="kbd">⌘K</span>
      </div>
      <div className="right">
        <span className="status-bar">
          <span className="dot live" /> 12 runs · 1.8k events/s
        </span>
        <button className="btn ghost icon-only" title="Notifications">
          <IconBell />
        </button>
        <button className="btn ghost icon-only" title="Help">
          <IconHelp />
        </button>
        <span className="avatar">JJ</span>
      </div>
    </header>
  )
}
