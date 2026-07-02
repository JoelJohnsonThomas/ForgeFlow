import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from '@tanstack/react-router'
import { DOCS, DOC_GROUPS, DOCS_BY_SLUG, editUrl, issueUrl, prevNext } from '../docs/manifest'
import type { DocEntry } from '../docs/manifest'
import { getDocSource } from '../docs/content'
import { extractToc, highlightSegments, searchDocs } from '../docs/search'
import type { TocItem } from '../docs/search'
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
      <span className="docs-version" title="Documented version">v0.1.0</span>
      <nav aria-label="Site">
        <a href="/">Landing</a>
        <a href="/console">Console</a>
        <Link to="/architecture">Architecture</Link>
        <a href="/api/docs">API reference ↗</a>
        <a href="https://github.com/JoelJohnsonThomas/forgeflow" target="_blank" rel="noopener noreferrer">GitHub ↗</a>
      </nav>
    </header>
  )
}

function Highlighted({ text, query }: { text: string; query: string }) {
  return (
    <>
      {highlightSegments(text, query).map((seg, i) =>
        seg.match ? <mark key={i}>{seg.text}</mark> : <span key={i}>{seg.text}</span>,
      )}
    </>
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
  const inputRef = useRef<HTMLInputElement>(null)
  const query = q.trim()
  const hits = useMemo(() => (query ? searchDocs(query) : []), [query])

  // "/" or Ctrl/Cmd+K focuses search from anywhere on the page.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null
      const typing = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)
      if ((e.key === '/' && !typing) || (e.key.toLowerCase() === 'k' && (e.ctrlKey || e.metaKey))) {
        e.preventDefault()
        inputRef.current?.focus()
        inputRef.current?.select()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <aside id="docs-sidebar" className={`docs-sidebar${open ? ' open' : ''}`} aria-label="Documentation">
      <label className="docs-search">
        <span className="sr-only">Search documentation</span>
        <input
          ref={inputRef}
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Escape' && q) {
              e.stopPropagation()
              setQ('')
            }
          }}
          placeholder="Search docs…"
          aria-label="Search documentation"
        />
        <kbd className="docs-search-kbd" aria-hidden="true">/</kbd>
      </label>

      {query ? (
        <div className="docs-results" role="region" aria-label="Search results">
          <p className="docs-results-count" role="status">
            {hits.length === 0 ? `No pages match “${query}”.` : `${hits.length} result${hits.length === 1 ? '' : 's'}`}
          </p>
          {hits.map((h) => (
            <Link
              key={h.entry.slug}
              to="/docs/$slug"
              params={{ slug: h.entry.slug }}
              hash={h.heading?.id}
              className="docs-result"
              onClick={() => {
                setQ('')
                onNavigate?.()
              }}
            >
              <span className="docs-result-title">
                <Highlighted text={h.entry.title} query={query} />
              </span>
              {h.heading && (
                <span className="docs-result-heading">
                  § <Highlighted text={h.heading.text} query={query} />
                </span>
              )}
              {h.snippet && (
                <span className="docs-result-snippet">
                  <Highlighted text={h.snippet} query={query} />
                </span>
              )}
            </Link>
          ))}
        </div>
      ) : (
        DOC_GROUPS.map((group) => (
          <div className="docs-nav-group" key={group}>
            <div className="docs-nav-title">{group}</div>
            {DOCS.filter((d) => d.group === group).map((d) => (
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
        ))
      )}
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
          — clone to a completed run in about 15 minutes. Press <kbd className="kbd">/</kbd> to search.
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

/** ~220 wpm, floored at 1 minute. */
function readingTime(source: string): number {
  const words = source.split(/\s+/).filter(Boolean).length
  return Math.max(1, Math.round(words / 220))
}

/** Right-rail "On this page" with scroll-spy. Hidden on narrow viewports (CSS). */
function DocToc({ items }: { items: TocItem[] }) {
  const [activeId, setActiveId] = useState<string | undefined>()

  useEffect(() => {
    const els = items.map((t) => document.getElementById(t.id)).filter((el): el is HTMLElement => el !== null)
    if (els.length === 0) return
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting)
        if (visible.length > 0) setActiveId(visible[0].target.id)
      },
      { rootMargin: '-64px 0px -70% 0px' },
    )
    els.forEach((el) => observer.observe(el))
    return () => observer.disconnect()
  }, [items])

  if (items.length < 2) return null
  return (
    <nav className="doc-toc" aria-label="On this page">
      <div className="doc-toc-title">On this page</div>
      {items.map((t, i) => (
        <a
          key={`${t.id}-${i}`}
          href={`#${t.id}`}
          className={`doc-toc-link lvl-${t.level}${activeId === t.id ? ' active' : ''}`}
        >
          {t.text}
        </a>
      ))}
    </nav>
  )
}

/** "Was this page helpful?" — recorded locally; issues go to GitHub. */
function DocFeedback({ entry }: { entry: DocEntry }) {
  const storageKey = `ff-docs-feedback:${entry.slug}`
  const [vote, setVote] = useState<string | null>(() => {
    try {
      return window.localStorage.getItem(storageKey)
    } catch {
      return null
    }
  })
  const record = (v: 'up' | 'down') => {
    setVote(v)
    try {
      window.localStorage.setItem(storageKey, v)
    } catch {
      // Storage unavailable (private mode) — the thanks message still shows.
    }
  }

  return (
    <div className="doc-feedback" role="group" aria-label="Page feedback">
      {vote ? (
        <p className="doc-feedback-thanks">
          Thanks for the feedback.{' '}
          <a href={issueUrl(entry)} target="_blank" rel="noopener noreferrer">
            Report an issue on GitHub ↗
          </a>
        </p>
      ) : (
        <>
          <span>Was this page helpful?</span>
          <button type="button" className="btn sm" onClick={() => record('up')}>
            👍 Yes
          </button>
          <button type="button" className="btn sm" onClick={() => record('down')}>
            👎 No
          </button>
        </>
      )}
    </div>
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
  const toc = source ? extractToc(source) : []

  return (
    <DocsShell active={entry.slug}>
      <div className="docs-article">
        <div className="docs-article-content">
          <nav className="docs-breadcrumbs" aria-label="Breadcrumb">
            <Link to="/docs">Docs</Link>
            <span className="sep">/</span>
            <span>{entry.group}</span>
            <span className="sep">/</span>
            <span className="cur">{entry.title}</span>
          </nav>

          {source && (
            <div className="docs-meta">
              <span>{readingTime(source)} min read</span>
              <span className="sep" aria-hidden="true">·</span>
              <a href={editUrl(entry.file)} target="_blank" rel="noopener noreferrer">
                Edit this page on GitHub ↗
              </a>
            </div>
          )}

          {source ? (
            <DocMarkdown source={source} file={entry.file} />
          ) : (
            <div className="doc-prose">
              <h1>{entry.title}</h1>
              <p>This page's source could not be loaded.</p>
            </div>
          )}

          <DocFeedback entry={entry} />

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
        </div>
        <DocToc items={toc} />
      </div>
    </DocsShell>
  )
}
