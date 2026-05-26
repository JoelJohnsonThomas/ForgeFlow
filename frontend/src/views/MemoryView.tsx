import { useMemo, useState } from 'react'
import { useMemorySearch } from '../api/hooks'

export function MemoryView() {
  const [query, setQuery] = useState('')
  const [submitted, setSubmitted] = useState('')
  const results = useMemorySearch(submitted)

  return (
    <section className="view active" data-screen-label="Memory">
      <div className="page-head">
        <div className="row">
          <div>
            <h1>Semantic memory</h1>
            <p className="sub">pgvector · 1.4M embeddings · 9 namespaces · ivfflat · cosine</p>
          </div>
          <div className="actions">
            <button className="btn sm">Namespace: sales/* ▾</button>
            <button className="btn sm">Embed model: text-embed-3-large ▾</button>
            <button className="btn sm primary">+ Store</button>
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="grid-2">
          <div>
            <SearchPanel
              query={query}
              setQuery={setQuery}
              onSubmit={() => setSubmitted(query)}
              results={results.data ?? []}
              isLoading={results.isLoading}
              isError={results.isError}
              errorMessage={results.error?.message}
              submitted={submitted}
            />
          </div>
          <div>
            <EmbeddingScatter />
            <RecallHeatmap />
          </div>
        </div>
      </div>
    </section>
  )
}

type SearchPanelProps = {
  query: string
  setQuery: (q: string) => void
  onSubmit: () => void
  results: { id: string; content: string; similarity: number; namespace: string }[]
  isLoading: boolean
  isError: boolean
  errorMessage?: string
  submitted: string
}

function SearchPanel({ query, setQuery, onSubmit, results, isLoading, isError, errorMessage, submitted }: SearchPanelProps) {
  return (
    <div className="panel">
      <div className="panel-head">
        <div className="title">Search · cosine similarity</div>
        <div className="actions">
          <span>k=8</span>
        </div>
      </div>
      <div className="panel-body">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            onSubmit()
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '10px 12px',
            border: '1px solid var(--border-default)',
            borderRadius: 6,
            background: 'var(--bg-page)',
          }}
        >
          <span style={{ color: 'var(--fg-muted)' }}>⌕</span>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a query and press Enter…"
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--fg-primary)',
              fontFamily: 'var(--font-sans)',
              fontSize: 13,
            }}
          />
          <span className="kbd">⏎</span>
        </form>

        <div style={{ marginTop: 14, display: 'grid', gap: 8 }}>
          {!submitted && <SampleResults />}
          {isLoading && (
            <p style={{ color: 'var(--fg-muted)', textAlign: 'center', padding: 24 }}>loading…</p>
          )}
          {isError && (
            <p style={{ color: 'var(--red-4)', padding: 16 }}>
              {errorMessage}
            </p>
          )}
          {submitted && !isLoading && results.length === 0 && !isError && (
            <p style={{ color: 'var(--fg-muted)', textAlign: 'center', padding: 24 }}>
              No memories matched.
            </p>
          )}
          {results.map((r) => (
            <div className="mem-card" key={r.id}>
              <div className="top">
                <span className="ns">{r.namespace}</span>
                <span className="sim">cos {r.similarity.toFixed(2)}</span>
              </div>
              <div className="snippet">{r.content}</div>
              <div className="footer">
                <span className="badge mono">{r.id.slice(0, 8)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// Sample results shown before the user has typed anything — matches design.
function SampleResults() {
  return (
    <>
      <div className="mem-card">
        <div className="top">
          <span className="ns">sales/stripe · decision</span>
          <span className="sim">cos 0.89</span>
        </div>
        <div className="snippet">Stripe declined 2025 expansion citing existing Adyen contract through Q2 2026. Re-engage post-renewal window.</div>
        <div className="footer">
          <span className="badge">2025-11-20</span>
          <span className="badge">v.lopez</span>
          <span className="badge mono">3 tokens</span>
        </div>
      </div>
      <div className="mem-card">
        <div className="top">
          <span className="ns">sales/stripe · interaction</span>
          <span className="sim">cos 0.84</span>
        </div>
        <div className="snippet">VP Eng demoed ForgeFlow during ELC dinner. Flagged interest in revenue ops automation. Owner: s.chen.</div>
        <div className="footer">
          <span className="badge">2026-02-08</span>
          <span className="badge">s.chen</span>
          <span className="badge mono">12 tokens</span>
        </div>
      </div>
      <div className="mem-card">
        <div className="top">
          <span className="ns">policy · global</span>
          <span className="sim">cos 0.78</span>
        </div>
        <div className="snippet">Net-new ARR ≥ $100K requires VP-level approval before send. Applies to all sales_ops workflows.</div>
        <div className="footer">
          <span className="badge">policy</span>
          <span className="badge">k.miller</span>
          <span className="badge mono">global</span>
        </div>
      </div>
      <div className="mem-card">
        <div className="top">
          <span className="ns">sales/quanta · decision</span>
          <span className="sim">cos 0.62</span>
        </div>
        <div className="snippet">Quanta closed $84K expansion 2026-Q1; champion = head of platform. Reference customer.</div>
        <div className="footer">
          <span className="badge">2026-03-14</span>
          <span className="badge">j.kim</span>
          <span className="badge mono">8 tokens</span>
        </div>
      </div>
    </>
  )
}

// Deterministic point cloud (replaces design's document.write random scatter).
function makeScatter(seed: number) {
  let s = seed >>> 0
  function rnd() {
    s |= 0; s = (s + 0x6D2B79F5) | 0
    let t = Math.imul(s ^ (s >>> 15), 1 | s)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
  const clusters = [
    { x: 140, y: 120, r: 55, color: 'var(--blue-4)', n: 80 },
    { x: 320, y: 160, r: 48, color: 'var(--purple-4)', n: 60 },
    { x: 200, y: 270, r: 60, color: 'var(--emerald-4)', n: 90 },
    { x: 370, y: 290, r: 42, color: 'var(--amber-4)', n: 50 },
  ]
  const out: { x: number; y: number; color: string }[] = []
  for (const cl of clusters) {
    for (let i = 0; i < cl.n; i++) {
      const a = rnd() * Math.PI * 2
      const r = Math.sqrt(rnd()) * cl.r
      out.push({ x: cl.x + Math.cos(a) * r, y: cl.y + Math.sin(a) * r, color: cl.color })
    }
  }
  return out
}

function EmbeddingScatter() {
  const points = useMemo(() => makeScatter(7), [])
  return (
    <div className="panel">
      <div className="panel-head">
        <div className="title">Embedding space · 2D projection</div>
        <div className="actions">
          <span>UMAP · n=8k</span>
        </div>
      </div>
      <div className="panel-body">
        <svg viewBox="0 0 480 380" width="100%" height={380}>
          <rect width="480" height="380" fill="var(--bg-inset)" rx="6" />
          <g opacity="0.16">
            <ellipse cx="140" cy="120" rx="80" ry="60" fill="var(--blue-4)" />
            <ellipse cx="320" cy="160" rx="70" ry="50" fill="var(--purple-4)" />
            <ellipse cx="200" cy="270" rx="90" ry="55" fill="var(--emerald-4)" />
            <ellipse cx="370" cy="290" rx="60" ry="50" fill="var(--amber-4)" />
          </g>
          <g>
            {points.map((p, i) => (
              <circle key={i} cx={p.x.toFixed(1)} cy={p.y.toFixed(1)} r="1.6" fill={p.color} opacity="0.7" />
            ))}
          </g>
          <circle cx="178" cy="148" r="6" fill="none" stroke="var(--fg-primary)" strokeWidth="1.5" />
          <circle cx="178" cy="148" r="3" fill="var(--fg-primary)" />
          <text x="190" y="146" fontFamily="var(--font-mono)" fontSize="10" fill="var(--fg-primary)">
            your query
          </text>
          <g fontFamily="var(--font-mono)" fontSize="10" fill="var(--fg-muted)">
            <text x="100" y="56">sales/stripe</text>
            <text x="296" y="100">sales/vercel</text>
            <text x="160" y="338">policy/global</text>
            <text x="334" y="346">support/*</text>
          </g>
        </svg>
      </div>
    </div>
  )
}

// Deterministic heatmap intensities — same PRNG so the page is stable across renders.
function makeHeatmap(seed: number, rows: number, cols: number) {
  let s = seed >>> 0
  function rnd() {
    s |= 0; s = (s + 0x6D2B79F5) | 0
    let t = Math.imul(s ^ (s >>> 15), 1 | s)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
  return Array.from({ length: rows }, () => Array.from({ length: cols }, () => 0.1 + rnd() * 0.9))
}

const NAMESPACES = ['sales/*', 'support/*', 'finance/*', 'policy/global', 'agents/*']

function RecallHeatmap() {
  const data = useMemo(() => makeHeatmap(11, NAMESPACES.length, 24), [])
  return (
    <div className="panel" style={{ marginTop: 16 }}>
      <div className="panel-head">
        <div className="title">Recall heatmap · last 24h</div>
        <div className="actions">
          <span>by namespace × hour</span>
        </div>
      </div>
      <div className="panel-body">
        <div style={{ display: 'grid', gridTemplateColumns: '80px repeat(24, 1fr)', gap: 2, fontFamily: 'var(--font-mono)', fontSize: 9 }}>
          {NAMESPACES.map((ns, r) => (
            <div key={ns} style={{ display: 'contents' }}>
              <div style={{ color: 'var(--fg-muted)', padding: '2px 0' }}>{ns}</div>
              {data[r].map((v, c) => (
                <div
                  key={c}
                  style={{
                    aspectRatio: '1',
                    background: 'var(--blue-4)',
                    opacity: v.toFixed(2),
                    borderRadius: 1,
                  }}
                  title={`${ns} · h${c}`}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
