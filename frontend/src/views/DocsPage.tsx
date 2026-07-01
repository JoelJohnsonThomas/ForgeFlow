import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from '@tanstack/react-router'
import { DOCS, DOC_GROUPS, DOCS_BY_SLUG, prevNext } from '../docs/manifest'
import { getDocSource } from '../docs/content'
import { DocMarkdown } from '../components/DocMarkdown'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import '../styles/docs.css'

function DocsTopbar({ navOpen, onMenuToggle }: { navOpen: boolean; onMenuToggle: () => void }) {
  return (
    <header className="docs-topbar">
      <button
        type="button"
        className="docs-menu-btn"
        aria-label={navOpen ? 'Close navigation' : 'Open navigation'}
        aria-expanded={navOpen}
        aria-controls="docs-sidebar"
        onClick={onMenuToggle}
      >
        <span aria-hidden="true">{navOpen ? '✕' : '☰'}</span>
      </button>
      <Link to="/" className="brand" aria-label="ForgeFlow home">
        <span className="brand-mark" />
        <span className="brand-name">ForgeFlow</span>
        <span className="docs-tag">docs</span>
      </Link>
      <nav aria-label="Site">
        <a href="/">Landing</a>
        <a href="/console">Console</a>
        <Link to="/architecture">Architecture</Link>
        <a href="https://github.com/JoelJohnsonThomas/forgeflow" target="_blank" rel="noopener noreferrer">GitHub ↗</a>
      </nav>
    </header>
  )
}

function DocsSidebar({
  active,
  open,
  onNavigate,
}: {
  active?: string
  open?: boolean
  onNavigate?: () => void
}) {
  const [q, setQ] = useState('')
  const query = q.trim().toLowerCase()
  const groups = useMemo(
    () =>
      DOC_GROUPS.map((g) => ({
        group: g,
        items: DOCS.filter(
          (d) =>
            d.group === g &&
            (query === '' ||
              d.title.toLowerCase().includes(query) ||
              (d.summary ?? '').toLowerCase().includes(query)),
        ),
      })).filter((x) => x.items.length > 0),
    [query],
  )

  return (
    <aside id="docs-sidebar" className={`docs-sidebar${open ? ' open' : ''}`} aria-label="Documentation">
      <label className="docs-search">
        <span className="sr-only">Search documentation</span>
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search docs…"
          aria-label="Search documentation"
        />
      </label>
      {groups.length === 0 && <p className="docs-empty">No pages match “{q}”.</p>}
      {groups.map(({ group, items }) => (
        <div className="docs-nav-group" key={group}>
          <div className="docs-nav-title">{group}</div>
          {items.map((d) => (
            <Link
              key={d.slug}
              to="/docs/$slug"
              params={{ slug: d.slug }}
              className="docs-nav-link"
              activeProps={{ className: 'docs-nav-link active' }}
              aria-current={active === d.slug ? 'page' : undefined}
              onClick={onNavigate}
            >
              {d.title}
            </Link>
          ))}
        </div>
      ))}
    </aside>
  )
}

function DocsShell({ active, children }: { active?: string; children: React.ReactNode }) {
  const [navOpen, setNavOpen] = useState(false)

  // Close the mobile drawer on Escape.
  useEffect(() => {
    if (!navOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setNavOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [navOpen])

  return (
    <div className="docs-root">
      <a href="#docs-content" className="skip-link">Skip to content</a>
      <DocsTopbar navOpen={navOpen} onMenuToggle={() => setNavOpen((v) => !v)} />
      <div className="docs-body">
        {navOpen && <div className="docs-scrim" aria-hidden="true" onClick={() => setNavOpen(false)} />}
        <DocsSidebar active={active} open={navOpen} onNavigate={() => setNavOpen(false)} />
        <main className="docs-main" id="docs-content" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  )
}

export function DocsIndexPage() {
  useDocumentTitle('Documentation')
  return (
    <DocsShell>
      <div className="doc-prose">
        <p className="doc-eyebrow">Documentation · v0.1.0 · pre-release</p>
        <h1>ForgeFlow documentation</h1>
        <p>
          Everything to install, operate, and extend ForgeFlow. New here? Start with{' '}
          <Link to="/docs/$slug" params={{ slug: 'tutorials-first-workflow' }}>
            Your first workflow
          </Link>{' '}
          — clone to a completed run in about 15 minutes.
        </p>
      </div>
      {DOC_GROUPS.map((group) => (
        <section className="docs-index-group" key={group}>
          <h2>{group}</h2>
          <div className="docs-card-grid">
            {DOCS.filter((d) => d.group === group).map((d) => (
              <Link key={d.slug} to="/docs/$slug" params={{ slug: d.slug }} className="docs-card">
                <span className="docs-card-title">{d.title}</span>
                {d.summary && <span className="docs-card-summary">{d.summary}</span>}
              </Link>
            ))}
          </div>
        </section>
      ))}
    </DocsShell>
  )
}

export function DocsArticlePage() {
  const { slug } = useParams({ strict: false }) as { slug?: string }
  const entry = slug ? DOCS_BY_SLUG[slug] : undefined
  useDocumentTitle(entry ? entry.title : 'Documentation')

  // Scroll to a hash target (or the top) after the page renders.
  useEffect(() => {
    const hash = window.location.hash
    requestAnimationFrame(() => {
      if (hash.length > 1) {
        document.getElementById(decodeURIComponent(hash.slice(1)))?.scrollIntoView()
      } else {
        document.getElementById('docs-content')?.scrollTo?.(0, 0)
        window.scrollTo(0, 0)
      }
    })
  }, [slug])

  if (!entry) {
    return (
      <DocsShell>
        <div className="doc-prose">
          <h1>Page not found</h1>
          <p>
            No documentation page matches this URL. Head back to the{' '}
            <Link to="/docs">documentation home</Link>.
          </p>
        </div>
      </DocsShell>
    )
  }

  const source = getDocSource(entry.file)
  const { prev, next } = prevNext(entry.slug)

  return (
    <DocsShell active={entry.slug}>
      <nav className="docs-breadcrumbs" aria-label="Breadcrumb">
        <Link to="/docs">Docs</Link>
        <span className="sep">/</span>
        <span>{entry.group}</span>
        <span className="sep">/</span>
        <span className="cur">{entry.title}</span>
      </nav>

      {source ? (
        <DocMarkdown source={source} file={entry.file} />
      ) : (
        <div className="doc-prose">
          <h1>{entry.title}</h1>
          <p>This page's source could not be loaded.</p>
        </div>
      )}

      <nav className="docs-prevnext" aria-label="Pagination">
        {prev ? (
          <Link to="/docs/$slug" params={{ slug: prev.slug }} className="docs-prevnext-link prev">
            <span className="dir">← Previous</span>
            <span className="ttl">{prev.title}</span>
          </Link>
        ) : (
          <span />
        )}
        {next ? (
          <Link to="/docs/$slug" params={{ slug: next.slug }} className="docs-prevnext-link next">
            <span className="dir">Next →</span>
            <span className="ttl">{next.title}</span>
          </Link>
        ) : (
          <span />
        )}
      </nav>
    </DocsShell>
  )
}
