import { useState } from 'react'
import { RunSalesOpsDialog } from '../components/RunSalesOpsDialog'

type Status = 'production' | 'scaffold'

type Template = {
  name: string
  title: string
  desc: string
  color: 'blue' | 'emerald' | 'amber'
  status: Status
  ctaPrimary: string
  connector?: string
  missingPieces?: string[]
}

const TEMPLATES: Template[] = [
  {
    name: 'sales_ops',
    title: 'Sales lead qualification',
    desc: 'qualify → research → analyze → propose → approve → execute',
    color: 'blue',
    status: 'production',
    ctaPrimary: 'Run →',
    connector: 'HubSpot CRM · upsert-by-email + idempotent deals',
  },
  {
    name: 'support_ops',
    title: 'Customer support triage',
    desc: 'triage → investigate → respond → escalate → resolve',
    color: 'emerald',
    status: 'scaffold',
    ctaPrimary: 'Dry-run only',
    missingPieces: [
      'No ticketing connector wired (Zendesk / Intercom / Freshdesk)',
      'No knowledge-base search tool',
      'No idempotent ticket reply path',
    ],
  },
  {
    name: 'finance_recon',
    title: 'Finance reconciliation',
    desc: 'ingest → match → flag_variance → approve → post',
    color: 'amber',
    status: 'scaffold',
    ctaPrimary: 'Dry-run only',
    missingPieces: [
      'No bank/ERP data source wired (QuickBooks + SAP exist but unconnected)',
      'No journal-posting tool with double-entry validation',
      'No regulatory audit trail (period locks, signed entries)',
    ],
  },
]

export function WorkflowsView() {
  const productionCount = TEMPLATES.filter((t) => t.status === 'production').length
  const scaffoldCount = TEMPLATES.filter((t) => t.status === 'scaffold').length
  return (
    <section className="view active" data-screen-label="Workflows">
      <div className="page-head">
        <div className="row">
          <div>
            <h1>Workflows</h1>
            <p className="sub">
              {productionCount} production · {scaffoldCount} template scaffold · POST /workflows/run to trigger
            </p>
          </div>
          <div className="actions">
            <a
              href="https://github.com/JoelJohnsonThomas/forgeflow/blob/main/docs/sales-ops-production.md"
              target="_blank"
              rel="noopener noreferrer"
              className="btn sm"
            >
              Production runbook →
            </a>
            <a
              href="https://github.com/JoelJohnsonThomas/forgeflow/blob/main/forgeflow/workflows/sales_ops/pipeline.py"
              target="_blank"
              rel="noopener noreferrer"
              className="btn sm primary"
            >
              + Build new (sample) →
            </a>
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="grid-3">
          {TEMPLATES.map((t) => (
            <TemplateCard key={t.name} t={t} />
          ))}
        </div>
        <FootnoteBanner />
      </div>
    </section>
  )
}

function TemplateCard({ t }: { t: Template }) {
  const isProduction = t.status === 'production'
  const [runOpen, setRunOpen] = useState(false)
  return (
    <div className="card" style={{ padding: 20, display: 'flex', flexDirection: 'column', minHeight: 280 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
        <span className={`badge ${t.color}`}>{t.name}</span>
        {isProduction ? (
          <span className="badge emerald">
            <span className="dot live" /> production
          </span>
        ) : (
          <span className="badge amber">⚠ template scaffold</span>
        )}
      </div>
      <h3
        style={{
          margin: '0 0 6px',
          fontSize: 17,
          fontWeight: 500,
          letterSpacing: 'var(--tracking-tight)',
        }}
      >
        {t.title}
      </h3>
      <p style={{ margin: 0, color: 'var(--fg-secondary)', fontSize: 13, lineHeight: 1.5 }}>{t.desc}</p>

      {isProduction && t.connector && (
        <div
          style={{
            marginTop: 14,
            padding: '8px 12px',
            background: 'var(--bg-inset)',
            borderRadius: 6,
            borderLeft: '2px solid var(--emerald-4)',
            fontSize: 12,
            color: 'var(--fg-secondary)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          {t.connector}
        </div>
      )}

      {!isProduction && t.missingPieces && (
        <div
          style={{
            marginTop: 14,
            padding: '10px 12px',
            background: 'var(--bg-inset)',
            borderRadius: 6,
            borderLeft: '2px solid var(--amber-4)',
            fontSize: 12,
            color: 'var(--fg-secondary)',
            lineHeight: 1.5,
          }}
        >
          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 10,
              letterSpacing: '.12em',
              textTransform: 'uppercase',
              color: 'var(--amber-4)',
              marginBottom: 6,
            }}
          >
            Missing for production
          </div>
          {t.missingPieces.map((m) => (
            <div key={m} style={{ paddingLeft: 12, position: 'relative', marginTop: 3 }}>
              <span
                style={{
                  position: 'absolute',
                  left: 0,
                  top: 7,
                  width: 4,
                  height: 4,
                  background: 'var(--fg-faint)',
                  borderRadius: '50%',
                }}
              />
              {m}
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: 'auto', paddingTop: 16, display: 'flex', gap: 8 }}>
        {isProduction ? (
          <>
            <button className="btn sm primary" onClick={() => setRunOpen(true)}>
              {t.ctaPrimary}
            </button>
            <a
              href="https://github.com/JoelJohnsonThomas/forgeflow/blob/main/docs/sales-ops-production.md"
              target="_blank"
              rel="noopener noreferrer"
              className="btn sm"
            >
              Runbook
            </a>
          </>
        ) : (
          <button className="btn sm" disabled title="Template scaffold — wire a connector first">
            {t.ctaPrimary}
          </button>
        )}
        <a href="/architecture#architecture" className="btn sm">View graph</a>
      </div>
      {isProduction && <RunSalesOpsDialog open={runOpen} onClose={() => setRunOpen(false)} />}
    </div>
  )
}

function FootnoteBanner() {
  return (
    <div
      style={{
        marginTop: 20,
        padding: '14px 18px',
        background: 'var(--bg-canvas)',
        border: '1px solid var(--border-subtle)',
        borderLeft: '2px solid var(--blue-4)',
        borderRadius: 'var(--r-3)',
        fontSize: 12.5,
        color: 'var(--fg-secondary)',
        lineHeight: 1.55,
      }}
    >
      <div
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 10,
          letterSpacing: '.12em',
          textTransform: 'uppercase',
          color: 'var(--blue-4)',
          marginBottom: 6,
        }}
      >
        Honest signal
      </div>
      Three named templates ≠ three production workflows. Today only{' '}
      <span className="mono" style={{ color: 'var(--fg-primary)' }}>sales_ops</span> ships with a real connector
      (HubSpot), idempotency on retries, retry-with-backoff, an end-to-end validation script, and a Fly.io deploy
      story. The other two are graph + prompt scaffolds — calling them from the API raises unless{' '}
      <span className="mono" style={{ color: 'var(--fg-primary)' }}>dry_run=true</span>. See{' '}
      <code style={{ color: 'var(--blue-4)' }}>docs/sales-ops-production.md</code> for the reference pattern.
    </div>
  )
}
