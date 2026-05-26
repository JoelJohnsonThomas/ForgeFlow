import { useState } from 'react'
import { useApprovalsPending, useApproveMutation, useRejectMutation } from '../api/hooks'
import type { Approval } from '../api/client'

export function ApprovalsView() {
  const q = useApprovalsPending()
  const pending = q.data ?? []

  return (
    <section className="view active" data-screen-label="Approvals">
      <div className="page-head">
        <div className="row">
          <div>
            <h1>Approval queue</h1>
            <p className="sub">
              {q.isLoading ? 'loading…' : `${pending.length} pending`}
              {q.isError && <span style={{ color: 'var(--red-4)', marginLeft: 8 }}>· {q.error?.message ?? 'error'}</span>}
            </p>
          </div>
          <div className="actions">
            <button className="btn sm">Assigned to me</button>
            <button className="btn sm">All</button>
            <button className="btn sm primary" disabled={pending.length === 0}>
              Bulk approve · {pending.length}
            </button>
          </div>
        </div>
      </div>
      <div className="page-body">
        {pending.length === 0 && !q.isLoading ? (
          <EmptyState />
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            {pending.map((a) => (
              <ApprovalCard key={a.token} approval={a} />
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

function EmptyState() {
  return (
    <div className="panel">
      <div className="panel-body" style={{ padding: 64, textAlign: 'center', color: 'var(--fg-muted)' }}>
        <p style={{ fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '.12em', textTransform: 'uppercase' }}>
          Inbox zero
        </p>
        <p style={{ marginTop: 12, fontSize: 13 }}>
          No pending approvals. Approval requests appear here when a workflow hits a
          <code style={{ color: 'var(--blue-4)', margin: '0 4px' }}>human_approval</code>
          interrupt.
        </p>
      </div>
    </div>
  )
}

function ApprovalCard({ approval }: { approval: Approval }) {
  const [note, setNote] = useState('')
  const approve = useApproveMutation()
  const reject = useRejectMutation()
  const pending = approve.isPending || reject.isPending
  const ageMin = Math.max(0, Math.floor((Date.now() - new Date(approval.requested_at).getTime()) / 60000))
  const proposal = approval.proposal as Record<string, unknown>
  const title = (proposal?.title as string) ?? (proposal?.subject as string) ?? `Approval · ${approval.token.slice(0, 8)}`
  const summary = (proposal?.summary as string) ?? (proposal?.description as string)

  return (
    <div className="approval">
      <div className="hd">
        <span className="badge amber">● PENDING · {ageMin}m</span>
        <span className="meta">
          {approval.token.slice(0, 8)} · {approval.workflow_id?.slice(0, 8) ?? '—'}
        </span>
      </div>
      <div className="ttl">{title}</div>
      {summary && <div className="meta">{summary}</div>}
      <pre className="diff" style={{ margin: '12px 0 0' }}>
        {Object.entries(proposal ?? {})
          .filter(([k]) => k !== 'title' && k !== 'summary' && k !== 'description' && k !== 'subject')
          .slice(0, 6)
          .map(([k, v]) => (
            <span key={k}>
              <span className="add">+ {k}</span>
              {'  '}
              {typeof v === 'string' ? v : JSON.stringify(v)}
              {'\n'}
            </span>
          ))}
      </pre>
      <input
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Optional note…"
        style={{
          marginTop: 10,
          width: '100%',
          padding: '6px 10px',
          background: 'var(--bg-inset)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 5,
          color: 'var(--fg-primary)',
          fontFamily: 'var(--font-mono)',
          fontSize: 11.5,
          outline: 'none',
        }}
      />
      <div className="ctas">
        <button
          className="btn sm primary"
          style={{ flex: 1, justifyContent: 'center' }}
          disabled={pending}
          onClick={() => approve.mutate({ token: approval.token, note })}
        >
          {approve.isPending ? '…' : 'Approve'}
        </button>
        <button
          className="btn sm"
          style={{ flex: 1, justifyContent: 'center' }}
          disabled={pending}
          onClick={() => reject.mutate({ token: approval.token, note })}
        >
          {reject.isPending ? '…' : 'Reject'}
        </button>
      </div>
      {(approve.isError || reject.isError) && (
        <div style={{ color: 'var(--red-4)', fontSize: 11, marginTop: 8 }}>
          {(approve.error ?? reject.error)?.message}
        </div>
      )}
    </div>
  )
}
