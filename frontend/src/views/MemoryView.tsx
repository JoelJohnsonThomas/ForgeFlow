import { useState } from 'react'
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
            <p className="sub">pgvector · cosine similarity · k=8</p>
          </div>
          <div className="actions">
            <button className="btn sm">Namespace: all ▾</button>
            <button className="btn sm primary">+ Store</button>
          </div>
        </div>
      </div>
      <div className="page-body">
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
                setSubmitted(query)
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
              {!submitted && (
                <p style={{ color: 'var(--fg-muted)', textAlign: 'center', padding: 32 }}>
                  Enter a query to search semantic memory.
                </p>
              )}
              {results.isLoading && (
                <p style={{ color: 'var(--fg-muted)', textAlign: 'center', padding: 24 }}>loading…</p>
              )}
              {results.isError && (
                <p style={{ color: 'var(--red-4)', padding: 16 }}>
                  {results.error.message}
                </p>
              )}
              {results.data && results.data.length === 0 && (
                <p style={{ color: 'var(--fg-muted)', textAlign: 'center', padding: 24 }}>
                  No memories matched.
                </p>
              )}
              {(results.data ?? []).map((r) => (
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
      </div>
    </section>
  )
}
