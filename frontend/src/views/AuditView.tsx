import { useState } from 'react'
import { useAuditSearch, useAuditStats } from '../api/hooks'
import type { AuditRow } from '../api/client'

export function AuditView() {
  const [actionFilter, setActionFilter] = useState<string | undefined>(undefined)
  const stats = useAuditStats(7)
  const search = useAuditSearch(actionFilter)

  return (
    <section className="view active" data-screen-label="Audit">
      <div className="page-head">
        <div className="row">
          <div>
            <h1>Audit log</h1>
            <p className="sub">
              Immutable · partitioned by tenant + day ·{' '}
              {/* /audit/stats degrades to {error} on a query failure — never crash on it. */}
              {stats.data?.total != null
                ? `${stats.data.total.toLocaleString()} entries (${stats.data.window_days}d)`
                : '—'}
              {stats.data?.denied != null && ` · ${stats.data.denied} denied`}
              {stats.data?.errors != null && ` · ${stats.data.errors} errors`}
              {stats.data?.error && (
                <span style={{ color: 'var(--red-4)' }}> · stats unavailable: {stats.data.error.slice(0, 80)}</span>
              )}
            </p>
          </div>
          <div className="actions">
            <button className={`btn sm${!actionFilter ? ' primary' : ''}`} onClick={() => setActionFilter(undefined)}>
              All
            </button>
            <button className={`btn sm${actionFilter === 'GET' ? ' primary' : ''}`} onClick={() => setActionFilter('GET')}>
              GET
            </button>
            <button className={`btn sm${actionFilter === 'POST' ? ' primary' : ''}`} onClick={() => setActionFilter('POST')}>
              POST
            </button>
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="panel">
          <div className="panel-head">
            <div className="title">Recent events</div>
            <div className="actions">
              <span className="mono">limit=50</span>
              <span style={{ color: 'var(--fg-faint)' }}>·</span>
              <span>{search.data?.items ? `${search.data.items.length} of ${search.data.total}` : '—'}</span>
              {search.data?.error && (
                <span style={{ color: 'var(--red-4)' }}>· {search.data.error.slice(0, 80)}</span>
              )}
            </div>
          </div>
          <div className="panel-body flush">
            <div
              className="audit-row"
              style={{
                background: 'var(--bg-page)',
                borderBottom: '1px solid var(--border-default)',
                fontFamily: 'var(--font-mono)',
                fontSize: 10,
                letterSpacing: '.12em',
                textTransform: 'uppercase',
                color: 'var(--fg-muted)',
              }}
            >
              <span>TIME</span>
              <span>ACTOR</span>
              <span>ACTION</span>
              <span>SCOPE</span>
              <span style={{ textAlign: 'right' }}>IP</span>
            </div>
            {search.isLoading && (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--fg-muted)' }}>loading…</div>
            )}
            {search.data?.items?.length === 0 && !search.isLoading && (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--fg-muted)' }}>
                No entries match.
              </div>
            )}
            {(search.data?.items ?? []).map((row) => (
              <AuditRowEl key={row.id} row={row} />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

function timeOnly(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleTimeString('en-US', { hour12: false })
}

function actionColor(action: string | null): string {
  if (!action) return 'var(--fg-muted)'
  if (action === 'GET') return 'var(--blue-4)'
  if (action === 'POST') return 'var(--amber-4)'
  if (action === 'PUT' || action === 'PATCH') return 'var(--purple-4)'
  if (action === 'DELETE') return 'var(--red-4)'
  return 'var(--fg-primary)'
}

function AuditRowEl({ row }: { row: AuditRow }) {
  const ip = (row.metadata?.client_ip as string | undefined) ?? '—'
  return (
    <div className="audit-row">
      <span className="when">{timeOnly(row.timestamp)}</span>
      <span className="actor">{row.user_id ?? 'anonymous'}</span>
      <span className="action">
        <span style={{ color: actionColor(row.action) }}>{row.action ?? '—'}</span>{' '}
        {row.resource ?? '—'}
      </span>
      <span className="scope">{row.role ?? ''}</span>
      <span className="ip">{ip}</span>
    </div>
  )
}
