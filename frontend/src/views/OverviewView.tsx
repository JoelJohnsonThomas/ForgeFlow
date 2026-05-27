import { useEvaluationSummary, useMetricsSummary, useRecentRuns } from '../api/hooks'
import type { RecentRun } from '../api/client'

export function OverviewView() {
  return (
    <section className="view active" data-screen-label="Overview">
      <div className="page-head">
        <div className="row">
          <div>
            <h1>Operations overview</h1>
            <p className="sub">Acme · sales_ops · prod-us-east-1 · last 24h</p>
          </div>
          <div className="actions">
            <button className="btn sm" disabled title="Time-window selector — wire to /metrics/* days param">
              Last 24h ▾
            </button>
            <a
              href="/api/metrics/"
              target="_blank"
              rel="noopener noreferrer"
              className="btn sm"
              title="Open raw JSON in a new tab"
            >
              JSON →
            </a>
            <a href="/console/workflows" className="btn sm primary">
              + New workflow
            </a>
          </div>
        </div>
      </div>
      <div className="page-body">
        <KpiStrip />
        <ChartsRow />
        <RecentRunsTable />
      </div>
    </section>
  )
}

function KpiStrip() {
  const metrics = useMetricsSummary()
  const evals = useEvaluationSummary()

  const summary = metrics.data
  const judgeAvg = evals.data
    ? ((evals.data.avg_faithfulness + evals.data.avg_relevance + evals.data.avg_coherence) / 3).toFixed(1)
    : '—'
  const hallRate = evals.data ? `hall rate: ${(evals.data.hallucination_rate * 100).toFixed(2)}%` : '—'

  return (
    <div className="kpi-strip">
      <Kpi
        label="Active runs"
        value={summary ? summary.total_runs.toLocaleString() : '—'}
        delta={{ kind: 'neutral', text: metrics.isLoading ? 'loading…' : 'all-time count' }}
      />
      <Kpi
        label="Success rate"
        value={
          summary ? (
            <>
              {(summary.success_rate * 100).toFixed(1)}<span className="u">%</span>
            </>
          ) : (
            '—'
          )
        }
        delta={{ kind: 'up', text: summary && summary.total_runs > 0 ? '▲ vs prior window' : '—' }}
      />
      <Kpi
        label="Total spend"
        value={summary ? `$${summary.total_cost_usd.toFixed(2)}` : '—'}
        delta={{
          kind: 'neutral',
          text: summary ? `avg $${summary.avg_cost_usd.toFixed(3)}/run` : '—',
        }}
      />
      <Kpi
        label="Avg latency"
        value={
          summary ? (
            <>
              {(summary.avg_latency_ms / 1000).toFixed(1)}<span className="u">s</span>
            </>
          ) : (
            '—'
          )
        }
        delta={{ kind: 'neutral', text: 'per workflow run' }}
      />
      <Kpi
        label="Judge score"
        valueStyle={{ color: 'var(--emerald-4)' }}
        value={
          <>
            {judgeAvg}<span className="u">/10</span>
          </>
        }
        delta={{ kind: 'neutral', text: hallRate }}
      />
    </div>
  )
}

function Kpi({
  label,
  value,
  delta,
  valueStyle,
}: {
  label: string
  value: React.ReactNode
  delta: { kind: 'up' | 'down' | 'neutral'; text: string }
  valueStyle?: React.CSSProperties
}) {
  const deltaClass = delta.kind === 'up' ? 'delta up' : delta.kind === 'down' ? 'delta down' : 'delta'
  return (
    <div className="kpi">
      <span className="label">{label}</span>
      <span className="val" style={valueStyle}>
        {value}
      </span>
      <span className={deltaClass}>{delta.text}</span>
    </div>
  )
}

function ChartsRow() {
  return (
    <div className="grid-2" style={{ marginTop: 16 }}>
      <RunsChart />
      <SpendByAgent />
    </div>
  )
}

function RunsChart() {
  return (
    <div className="panel">
      <div className="panel-head">
        <div className="title">Runs · last 24h</div>
        <div className="actions">
          <span>by status</span>
        </div>
      </div>
      <div className="panel-body">
        <svg viewBox="0 0 800 220" width="100%" height={220}>
          <g stroke="var(--border-subtle)" strokeDasharray="2 4" opacity="0.5">
            <line x1="0" y1="40" x2="800" y2="40" />
            <line x1="0" y1="100" x2="800" y2="100" />
            <line x1="0" y1="160" x2="800" y2="160" />
          </g>
          <g fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">
            <text x="4" y="36">300</text>
            <text x="4" y="96">200</text>
            <text x="4" y="156">100</text>
          </g>
          <path
            d="M 30 200 L 30 180 L 70 174 L 110 162 L 150 158 L 190 142 L 230 130 L 270 132 L 310 116 L 350 100 L 390 84 L 430 76 L 470 62 L 510 70 L 550 58 L 590 50 L 630 44 L 670 36 L 710 38 L 750 30 L 790 28 L 790 200 Z"
            fill="oklch(0.40 0.11 160 / 0.5)"
            stroke="var(--emerald-4)"
            strokeWidth="1.5"
          />
          <path
            d="M 30 188 L 70 185 L 110 178 L 150 178 L 190 172 L 230 168 L 270 168 L 310 162 L 350 158 L 390 154 L 430 152 L 470 144 L 510 152 L 550 148 L 590 144 L 630 138 L 670 132 L 710 134 L 750 130 L 790 128 L 790 200 L 30 200 Z"
            fill="oklch(0.50 0.12 75 / 0.5)"
            stroke="var(--amber-4)"
            strokeWidth="1.2"
          />
          <path
            d="M 30 196 L 70 195 L 110 193 L 150 194 L 190 192 L 230 190 L 270 192 L 310 189 L 350 188 L 390 186 L 430 185 L 470 184 L 510 187 L 550 185 L 590 184 L 630 182 L 670 180 L 710 181 L 750 179 L 790 178 L 790 200 L 30 200 Z"
            fill="oklch(0.45 0.18 25 / 0.5)"
            stroke="var(--red-4)"
            strokeWidth="1.2"
          />
          <line x1="730" y1="20" x2="730" y2="200" stroke="var(--blue-4)" strokeDasharray="3 3" />
          <text x="734" y="30" fontFamily="var(--font-mono)" fontSize="9" fill="var(--blue-4)">
            NOW
          </text>
        </svg>
        <div
          style={{
            display: 'flex',
            gap: 20,
            fontFamily: 'var(--font-mono)',
            fontSize: 11,
            color: 'var(--fg-muted)',
            marginTop: 8,
          }}
        >
          <span>
            <ChartSwatch color="var(--emerald-4)" />
            completed
          </span>
          <span>
            <ChartSwatch color="var(--amber-4)" />
            pending approval
          </span>
          <span>
            <ChartSwatch color="var(--red-4)" />
            failed
          </span>
          <span style={{ marginLeft: 'auto', color: 'var(--fg-faint)' }}>chart: sample · Phase 3 will plot live</span>
        </div>
      </div>
    </div>
  )
}

function ChartSwatch({ color }: { color: string }) {
  return (
    <i
      style={{
        display: 'inline-block',
        width: 8,
        height: 8,
        background: color,
        borderRadius: 2,
        marginRight: 6,
      }}
    />
  )
}

function SpendByAgent() {
  return (
    <div className="panel">
      <div className="panel-head">
        <div className="title">Spend by agent · 24h</div>
        <div className="actions">
          <span>sample</span>
        </div>
      </div>
      <div className="panel-body">
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <svg viewBox="0 0 200 200" width={180} height={180} className="donut">
            <circle cx="100" cy="100" r="80" fill="none" strokeWidth={22} stroke="oklch(0.25 0.012 250)" />
            <circle cx="100" cy="100" r="80" fill="none" strokeWidth={22} stroke="var(--blue-4)" strokeDasharray="180 502" strokeDashoffset="0" />
            <circle cx="100" cy="100" r="80" fill="none" strokeWidth={22} stroke="var(--purple-4)" strokeDasharray="140 502" strokeDashoffset="-180" />
            <circle cx="100" cy="100" r="80" fill="none" strokeWidth={22} stroke="var(--emerald-4)" strokeDasharray="100 502" strokeDashoffset="-320" />
            <circle cx="100" cy="100" r="80" fill="none" strokeWidth={22} stroke="var(--amber-4)" strokeDasharray="82 502" strokeDashoffset="-420" />
          </svg>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
            <SpendRow color="var(--blue-4)" name="executor" amount="$66.32 · 36%" />
            <SpendRow color="var(--purple-4)" name="researcher" amount="$51.58 · 28%" />
            <SpendRow color="var(--emerald-4)" name="analyzer" amount="$36.84 · 20%" />
            <SpendRow color="var(--amber-4)" name="supervisor" amount="$29.46 · 16%" />
          </div>
        </div>
      </div>
    </div>
  )
}

function SpendRow({ color, name, amount }: { color: string; name: string; amount: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <span>
        <ChartSwatch color={color} />
        {name}
      </span>
      <span className="mono">{amount}</span>
    </div>
  )
}

function statusBadge(status: string) {
  const s = status.toLowerCase()
  if (s === 'done' || s === 'completed' || s === 'success') return <span className="badge emerald">● completed</span>
  if (s === 'pending_approval' || s === 'awaiting_approval' || s === 'paused')
    return <span className="badge amber">● awaiting approval</span>
  if (s === 'failed' || s === 'error') return <span className="badge red">● failed</span>
  if (s === 'running' || s === 'in_progress') return <span className="badge blue">● running</span>
  return <span className="badge">● {status}</span>
}

function relativeTime(iso: string | null): string {
  if (!iso) return '—'
  const then = new Date(iso).getTime()
  const now = Date.now()
  const diff = Math.max(0, now - then) / 1000
  if (diff < 60) return `${Math.floor(diff)}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

function shortRunId(run: RecentRun): string {
  return `wf_${run.run_id.slice(0, 5)}`
}

function RecentRunsTable() {
  const runsQ = useRecentRuns(10)
  const runs = runsQ.data ?? []

  return (
    <div className="panel" style={{ marginTop: 16 }}>
      <div className="panel-head">
        <div className="title">Recent runs</div>
        <div className="actions">
          <span>{runsQ.isLoading ? 'loading…' : `${runs.length} shown`}</span>
          {runsQ.isError && <span style={{ color: 'var(--red-4)' }}>· error</span>}
          <span style={{ color: 'var(--fg-faint)' }}>·</span>
          <span style={{ color: 'var(--blue-4)', cursor: 'pointer' }}>+ filter</span>
        </div>
      </div>
      <div className="panel-body flush">
        <table className="tbl">
          <thead>
            <tr>
              <th>Run</th>
              <th>Workflow</th>
              <th>Status</th>
              <th className="num">Cost</th>
              <th className="num">Tokens</th>
              <th>When</th>
            </tr>
          </thead>
          <tbody>
            {runs.length === 0 && !runsQ.isLoading && (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: 32, color: 'var(--fg-muted)' }}>
                  No runs yet. POST to /workflows/run to kick one off.
                </td>
              </tr>
            )}
            {runs.map((r) => (
              <tr key={r.run_id}>
                <td>
                  <span className="id">{shortRunId(r)}</span>
                </td>
                <td>{r.workflow_type}</td>
                <td>{statusBadge(r.status)}</td>
                <td className="num">${r.total_cost_usd.toFixed(3)}</td>
                <td className="num">{r.total_tokens.toLocaleString()}</td>
                <td className="num text-mono text-muted">{relativeTime(r.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
