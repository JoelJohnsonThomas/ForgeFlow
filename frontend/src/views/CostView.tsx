import { useCostByAgent, useCostByWorkflow, useMetricsSummary, useTopRuns } from '../api/hooks'

export function CostView() {
  return (
    <section className="view active" data-screen-label="Cost">
      <div className="page-head">
        <div className="row">
          <div>
            <h1>Cost &amp; spend</h1>
            <p className="sub">Acme · all workflows · MTD $4,148.20 · budget $6,000 · forecast on track</p>
          </div>
          <div className="actions">
            <button className="btn sm" disabled title="Filter UI — selector not yet wired">Group by: agent ▾</button>
            <button className="btn sm" disabled title="Filter UI — selector not yet wired">Last 30d ▾</button>
            <a
              href="/api/metrics/cost?days=30"
              target="_blank"
              rel="noopener noreferrer"
              className="btn sm"
            >
              JSON →
            </a>
          </div>
        </div>
      </div>
      <div className="page-body">
        <KpiStrip />
        <DesignChartsRow />
        <LiveBreakdown />
        <TopCostDrivers />
      </div>
    </section>
  )
}

function KpiStrip() {
  const summary = useMetricsSummary()
  const s = summary.data
  return (
    <div className="kpi-strip">
      <div className="kpi">
        <span className="label">MTD spend</span>
        <span className="val">$4,148.20</span>
        <span className="delta down">▼ 6.2% vs last mo.</span>
      </div>
      <div className="kpi">
        <span className="label">Forecast EOM</span>
        <span className="val">$5,720</span>
        <span className="delta">95% of $6k budget</span>
      </div>
      <div className="kpi">
        <span className="label">$ / run (live)</span>
        <span className="val">{s ? `$${s.avg_cost_usd.toFixed(3)}` : '—'}</span>
        <span className="delta">avg across {s ? s.total_runs.toLocaleString() : '—'} runs</span>
      </div>
      <div className="kpi">
        <span className="label">Cache hit</span>
        <span className="val">42.1<span className="u">%</span></span>
        <span className="delta">saves $1.8k/mo</span>
      </div>
      <div className="kpi">
        <span className="label">Hallucination $</span>
        <span className="val" style={{ color: 'var(--red-4)' }}>$48.20</span>
        <span className="delta">retry burn</span>
      </div>
    </div>
  )
}

function DesignChartsRow() {
  return (
    <div className="grid-2" style={{ marginTop: 16 }}>
      <SpendTrendPanel />
      <ForecastPanel />
    </div>
  )
}

function SpendTrendPanel() {
  return (
    <div className="panel">
      <div className="panel-head">
        <div className="title">Spend trend · 30d</div>
        <div className="actions">
          <span>by model</span>
        </div>
      </div>
      <div className="panel-body">
        <svg viewBox="0 0 800 220" width="100%" height={220}>
          <g stroke="var(--border-subtle)" strokeDasharray="2 4" opacity="0.5">
            <line x1="0" y1="40" x2="800" y2="40" />
            <line x1="0" y1="100" x2="800" y2="100" />
            <line x1="0" y1="160" x2="800" y2="160" />
          </g>
          <path
            d="M 20 180 L 50 174 L 80 168 L 110 162 L 140 158 L 170 152 L 200 158 L 230 142 L 260 138 L 290 130 L 320 124 L 350 110 L 380 108 L 410 96 L 440 90 L 470 92 L 500 82 L 530 76 L 560 70 L 590 64 L 620 58 L 650 54 L 680 50 L 710 46 L 740 42 L 770 40 L 770 200 L 20 200 Z"
            fill="oklch(0.42 0.13 240 / 0.25)"
            stroke="var(--blue-4)"
            strokeWidth="1.5"
          />
          <path
            d="M 20 195 L 50 192 L 80 190 L 110 186 L 140 185 L 170 180 L 200 184 L 230 175 L 260 172 L 290 168 L 320 164 L 350 158 L 380 156 L 410 150 L 440 146 L 470 148 L 500 142 L 530 138 L 560 134 L 590 130 L 620 126 L 650 124 L 680 122 L 710 118 L 740 116 L 770 114 L 770 200 L 20 200 Z"
            fill="oklch(0.42 0.14 295 / 0.22)"
            stroke="var(--purple-4)"
            strokeWidth="1.5"
          />
          <g fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">
            <text x="4" y="44">$300</text>
            <text x="4" y="104">$200</text>
            <text x="4" y="164">$100</text>
          </g>
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
          <LegendChip color="var(--blue-4)" label="gpt-4o · $2,840" />
          <LegendChip color="var(--purple-4)" label="claude-3.7 · $920" />
          <LegendChip color="var(--emerald-4)" label="llama-3.1 (local) · $0" />
        </div>
      </div>
    </div>
  )
}

function LegendChip({ color, label }: { color: string; label: string }) {
  return (
    <span>
      <i style={{ display: 'inline-block', width: 8, height: 8, background: color, borderRadius: 2, marginRight: 6 }} />
      {label}
    </span>
  )
}

function ForecastPanel() {
  return (
    <div className="panel">
      <div className="panel-head">
        <div className="title">AI cost forecast</div>
        <div className="actions">
          <span>predicted by ForgeFlow</span>
        </div>
      </div>
      <div className="panel-body">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-muted)', letterSpacing: '.12em', textTransform: 'uppercase' }}>
              FORECAST · END OF MONTH
            </div>
            <div style={{ fontSize: 30, fontWeight: 500, letterSpacing: '-.02em', fontVariantNumeric: 'tabular-nums', marginTop: 4 }}>
              $5,720<span style={{ fontSize: 14, color: 'var(--fg-muted)' }}> ±$220</span>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-muted)', letterSpacing: '.12em', textTransform: 'uppercase' }}>
              BUDGET
            </div>
            <div style={{ fontSize: 18, fontVariantNumeric: 'tabular-nums', marginTop: 4 }}>$6,000</div>
          </div>
        </div>
        <div style={{ position: 'relative', height: 28, background: 'var(--bg-inset)', borderRadius: 4, overflow: 'hidden' }}>
          <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '69%', background: 'linear-gradient(90deg, var(--blue-3), var(--blue-4))' }} />
          <div style={{ position: 'absolute', left: '69%', top: 0, bottom: 0, width: '26%', background: 'oklch(0.42 0.13 240 / 0.4)', borderLeft: '1px dashed var(--blue-4)' }} />
          <div style={{ position: 'absolute', right: 6, top: 6, fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--fg-muted)' }}>
            95% budget
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--fg-muted)', marginTop: 6 }}>
          <span>MTD $4,148</span>
          <span style={{ color: 'var(--blue-4)' }}>forecast remainder $1,572</span>
          <span>$6,000 cap</span>
        </div>
        <ForgeSuggestion />
      </div>
    </div>
  )
}

function ForgeSuggestion() {
  return (
    <div
      style={{
        marginTop: 18,
        padding: 12,
        background: 'var(--bg-inset)',
        borderRadius: 6,
        borderLeft: '2px solid var(--blue-4)',
        fontSize: 12.5,
        color: 'var(--fg-secondary)',
      }}
    >
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--blue-4)', letterSpacing: '.12em', textTransform: 'uppercase' }}>
        FORGE · SUGGESTION
      </span>
      <br />
      Switching <span style={{ color: 'var(--fg-primary)' }}>analyzer</span> from gpt-4o to{' '}
      <span style={{ color: 'var(--fg-primary)' }}>claude-3.5-haiku</span> on runs scored ≤6.0 would save{' '}
      <span style={{ color: 'var(--emerald-4)', fontFamily: 'var(--font-mono)' }}>~$412/mo</span> with judge delta of{' '}
      <span style={{ color: 'var(--emerald-4)', fontFamily: 'var(--font-mono)' }}>-0.08</span>.
      <div style={{ marginTop: 8 }}>
        <a
          href="https://github.com/JoelJohnsonThomas/forgeflow/discussions/categories/ideas"
          target="_blank"
          rel="noopener noreferrer"
          className="btn sm primary"
        >
          Vote for policy automation →
        </a>
        <a
          href="https://github.com/JoelJohnsonThomas/forgeflow/discussions/categories/ideas"
          target="_blank"
          rel="noopener noreferrer"
          className="btn sm"
          style={{ marginLeft: 6 }}
        >
          Discuss
        </a>
      </div>
    </div>
  )
}

function LiveBreakdown() {
  const byAgent = useCostByAgent(7)
  const byWorkflow = useCostByWorkflow(7)
  const total = (byAgent.data ?? []).reduce((sum, r) => sum + r.total_cost, 0)

  return (
    <div className="grid-2" style={{ marginTop: 16 }}>
      <div className="panel">
        <div className="panel-head">
          <div className="title">Live · spend by agent (7d)</div>
          <div className="actions">
            <span>${total.toFixed(2)} · /metrics/cost</span>
          </div>
        </div>
        <div className="panel-body">
          {byAgent.isLoading ? (
            <p style={{ color: 'var(--fg-muted)' }}>loading…</p>
          ) : (byAgent.data ?? []).length === 0 ? (
            <p style={{ color: 'var(--fg-muted)' }}>No agent cost data yet — kick off a workflow to populate.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
              {(byAgent.data ?? []).map((r) => {
                const pct = total > 0 ? (r.total_cost / total) * 100 : 0
                return (
                  <div key={r.agent}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span>{r.agent}</span>
                      <span className="mono">${r.total_cost.toFixed(2)} · {pct.toFixed(0)}%</span>
                    </div>
                    <div style={{ height: 6, background: 'var(--bg-inset)', borderRadius: 3, overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${pct}%`,
                          height: '100%',
                          background: 'linear-gradient(90deg, var(--blue-3), var(--blue-4))',
                        }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      <div className="panel">
        <div className="panel-head">
          <div className="title">Live · spend by workflow (7d)</div>
          <div className="actions">
            <span>{(byWorkflow.data ?? []).length} types</span>
          </div>
        </div>
        <div className="panel-body">
          {byWorkflow.isLoading ? (
            <p style={{ color: 'var(--fg-muted)' }}>loading…</p>
          ) : (byWorkflow.data ?? []).length === 0 ? (
            <p style={{ color: 'var(--fg-muted)' }}>No data yet.</p>
          ) : (
            <table className="tbl">
              <thead>
                <tr>
                  <th>Workflow</th>
                  <th className="num">Runs</th>
                  <th className="num">Tokens</th>
                  <th className="num">Cost</th>
                </tr>
              </thead>
              <tbody>
                {(byWorkflow.data ?? []).map((r) => (
                  <tr key={r.workflow_type}>
                    <td>{r.workflow_type}</td>
                    <td className="num">{r.runs.toLocaleString()}</td>
                    <td className="num">{r.total_tokens.toLocaleString()}</td>
                    <td className="num">${r.total_cost.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

type DriverRow = {
  workflow: string
  agent: string
  agentColor: 'blue' | 'purple' | 'emerald' | 'amber' | 'red'
  agentInitials: string
  model: string
  runs: string
  tokens: string
  cost: string
  perRun: string
  trend: number[]
  trendColor: string
}

const DRIVERS: DriverRow[] = [
  { workflow: 'sales_ops', agent: 'executor', agentColor: 'amber', agentInitials: 'EX', model: 'gpt-4o', runs: '8,124', tokens: '14.2M', cost: '$1,840', perRun: '$0.227', trend: [14, 12, 10, 11, 8, 6, 5], trendColor: 'var(--blue-4)' },
  { workflow: 'sales_ops', agent: 'researcher', agentColor: 'purple', agentInitials: 'RS', model: 'gpt-4o-mini', runs: '8,124', tokens: '9.8M', cost: '$612', perRun: '$0.075', trend: [10, 12, 9, 11, 12, 9, 8], trendColor: 'var(--purple-4)' },
  { workflow: 'support_ops', agent: 'executor', agentColor: 'amber', agentInitials: 'EX', model: 'claude-3.7-sonnet', runs: '12,418', tokens: '8.4M', cost: '$520', perRun: '$0.042', trend: [8, 10, 7, 8, 9, 7, 6], trendColor: 'var(--blue-4)' },
  { workflow: 'finance_recon', agent: 'analyzer', agentColor: 'emerald', agentInitials: 'AN', model: 'llama-3.1 (local)', runs: '412', tokens: '1.2M', cost: '$0.00', perRun: '$0.000', trend: [10, 10, 10, 10, 10, 10, 10], trendColor: 'var(--emerald-4)' },
]

function TopCostDrivers() {
  const top = useTopRuns(7, 10)
  return (
    <>
      <div className="panel" style={{ marginTop: 16 }}>
        <div className="panel-head">
          <div className="title">Top cost drivers</div>
          <div className="actions">
            <span>workflow × agent × model</span>
          </div>
        </div>
        <div className="panel-body flush">
          <table className="tbl">
            <thead>
              <tr>
                <th>Workflow</th>
                <th>Agent</th>
                <th>Model</th>
                <th className="num">Runs</th>
                <th className="num">Tokens</th>
                <th className="num">Cost</th>
                <th className="num">$/run</th>
                <th>Trend</th>
              </tr>
            </thead>
            <tbody>
              {DRIVERS.map((d) => (
                <tr key={`${d.workflow}-${d.agent}`}>
                  <td>{d.workflow}</td>
                  <td>
                    <span className="agent-av">
                      <span className={`av ${d.agentColor}`}>{d.agentInitials}</span>
                      {d.agent}
                    </span>
                  </td>
                  <td className="mono">{d.model}</td>
                  <td className="num">{d.runs}</td>
                  <td className="num">{d.tokens}</td>
                  <td className="num">{d.cost}</td>
                  <td className="num">{d.perRun}</td>
                  <td><Sparkline points={d.trend} color={d.trendColor} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 16 }}>
        <div className="panel-head">
          <div className="title">Live · top runs by cost (7d)</div>
          <div className="actions">
            <span>/metrics/cost/top_runs</span>
          </div>
        </div>
        <div className="panel-body flush">
          <table className="tbl">
            <thead>
              <tr>
                <th>Run</th>
                <th>Workflow</th>
                <th className="num">Tokens</th>
                <th className="num">Cost</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {top.isLoading && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: 24, color: 'var(--fg-muted)' }}>
                    loading…
                  </td>
                </tr>
              )}
              {(top.data ?? []).length === 0 && !top.isLoading && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: 24, color: 'var(--fg-muted)' }}>
                    No runs in window.
                  </td>
                </tr>
              )}
              {(top.data ?? []).map((r) => (
                <tr key={r.run_id}>
                  <td><span className="id">{r.run_id.slice(0, 8)}</span></td>
                  <td>{r.workflow_type}</td>
                  <td className="num">{r.total_tokens.toLocaleString()}</td>
                  <td className="num">${r.total_cost_usd.toFixed(3)}</td>
                  <td className="num text-mono text-muted">
                    {r.created_at ? new Date(r.created_at).toLocaleString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}

function Sparkline({ points, color }: { points: number[]; color: string }) {
  const width = 60
  const height = 20
  const max = Math.max(...points)
  const min = Math.min(...points)
  const range = max - min || 1
  const path = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * width
      const y = height - ((p - min) / range) * (height - 4) - 2
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline points={path} stroke={color} strokeWidth="1.2" fill="none" />
    </svg>
  )
}
