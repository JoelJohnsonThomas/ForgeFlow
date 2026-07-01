import { useEffect, useState } from 'react'
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
            <button className="btn sm" disabled title="Assignee filter — wire when /approvals exposes assignee">
              Assigned to me
            </button>
            <button className="btn sm" disabled title="Default — current view shows all pending">
              All
            </button>
            <button className="btn sm primary" disabled title="Bulk approve endpoint not implemented yet">
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
        <ActivityTable />
      </div>
    </section>
  )
}

type ActivityRow = {
  token: string
  action: string
  reviewer: string
  decision: 'approved' | 'rejected' | 'sent_back'
  decisionLabel: string
  latency: string
  when: string
}

const ACTIVITY: ActivityRow[] = [
  { token: 'apr_jK02p', action: 'Send proposal — Vercel · $96K', reviewer: 's.chen', decision: 'approved', decisionLabel: 'approved', latency: '2m 41s', when: '14m ago' },
  { token: 'apr_mL18p', action: 'Refund — Quanta · $1,820', reviewer: 'j.kim', decision: 'approved', decisionLabel: 'approved', latency: '4m 12s', when: '38m ago' },
  { token: 'apr_yT72k', action: 'Send proposal — Northwind · $260K', reviewer: 'v.lopez', decision: 'rejected', decisionLabel: 'rejected · ICP miss', latency: '8m 04s', when: '1h ago' },
  { token: 'apr_dW91x', action: 'Q1 journal posting', reviewer: 't.alvarez', decision: 'sent_back', decisionLabel: 'sent back · variance > 5%', latency: '12m 18s', when: '2h ago' },
]

function decisionBadge(d: ActivityRow['decision'], label: string) {
  if (d === 'approved') return <span className="badge emerald">{label}</span>
  if (d === 'rejected') return <span className="badge red">{label}</span>
  return <span className="badge amber">{label}</span>
}

function ActivityTable() {
  return (
    <div className="panel" style={{ marginTop: 16 }}>
      <div className="panel-head">
        <div className="title">Approval activity · last 7d</div>
        <div className="actions">
          <span>p50 review: 6m 12s</span>
        </div>
      </div>
      <div className="panel-body flush">
        <table className="tbl">
          <thead>
            <tr>
              <th>Token</th>
              <th>Action</th>
              <th>Reviewer</th>
              <th>Decision</th>
              <th className="num">Latency</th>
              <th>When</th>
            </tr>
          </thead>
          <tbody>
            {ACTIVITY.map((r) => (
              <tr key={r.token}>
                <td><span className="id">{r.token}</span></td>
                <td>{r.action}</td>
                <td>{r.reviewer}</td>
                <td>{decisionBadge(r.decision, r.decisionLabel)}</td>
                <td className="num">{r.latency}</td>
                <td className="text-mono text-muted">{r.when}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
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
  // Reading Date.now() during render is impure (react-hooks/purity). Capture it
  // in state via a lazy initializer and tick it once a minute so the displayed
  // age stays correct without an unstable render-time read.
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60_000)
    return () => clearInterval(id)
  }, [])
  const ageMin = Math.max(0, Math.floor((now - new Date(approval.requested_at).getTime()) / 60000))
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
