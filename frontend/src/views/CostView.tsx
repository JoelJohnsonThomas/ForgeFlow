import { useCostByAgent, useCostByWorkflow, useMetricsSummary, useTopRuns } from '../api/hooks'

export function CostView() {
  return (
    <section className="view active" data-screen-label="Cost">
      <div className="page-head">
        <div className="row">
          <div>
            <h1>Cost &amp; spend</h1>
            <p className="sub">Per-agent and per-workflow breakdown · live from /metrics/cost</p>
          </div>
          <div className="actions">
            <button className="btn sm">Group by: agent ▾</button>
            <button className="btn sm">Last 7d ▾</button>
            <button className="btn sm">Export CSV</button>
          </div>
        </div>
      </div>
      <div className="page-body">
        <KpiStrip />
        <ChartsRow />
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
        <span className="label">Total spend</span>
        <span className="val">{s ? `$${s.total_cost_usd.toFixed(2)}` : '—'}</span>
        <span className="delta">all-time</span>
      </div>
      <div className="kpi">
        <span className="label">$ / run</span>
        <span className="val">{s ? `$${s.avg_cost_usd.toFixed(3)}` : '—'}</span>
        <span className="delta">average</span>
      </div>
      <div className="kpi">
        <span className="label">Total runs</span>
        <span className="val">{s ? s.total_runs.toLocaleString() : '—'}</span>
        <span className="delta">workflows executed</span>
      </div>
      <div className="kpi">
        <span className="label">Success rate</span>
        <span className="val">{s ? `${(s.success_rate * 100).toFixed(1)}` : '—'}<span className="u">%</span></span>
        <span className="delta">vs failed/cancelled</span>
      </div>
      <div className="kpi">
        <span className="label">Avg latency</span>
        <span className="val">{s ? (s.avg_latency_ms / 1000).toFixed(1) : '—'}<span className="u">s</span></span>
        <span className="delta">per workflow run</span>
      </div>
    </div>
  )
}

function ChartsRow() {
  const byAgent = useCostByAgent(7)
  const byWorkflow = useCostByWorkflow(7)
  const total = (byAgent.data ?? []).reduce((sum, r) => sum + r.total_cost, 0)

  return (
    <div className="grid-2" style={{ marginTop: 16 }}>
      <div className="panel">
        <div className="panel-head">
          <div className="title">Spend by agent · 7d</div>
          <div className="actions">
            <span>${total.toFixed(2)}</span>
          </div>
        </div>
        <div className="panel-body">
          {byAgent.isLoading ? (
            <p style={{ color: 'var(--fg-muted)' }}>loading…</p>
          ) : (byAgent.data ?? []).length === 0 ? (
            <p style={{ color: 'var(--fg-muted)' }}>No agent cost data — kick off a workflow to populate.</p>
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
          <div className="title">Spend by workflow · 7d</div>
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

function TopCostDrivers() {
  const top = useTopRuns(7, 10)
  return (
    <div className="panel" style={{ marginTop: 16 }}>
      <div className="panel-head">
        <div className="title">Top cost drivers · last 7d</div>
        <div className="actions">
          <span>highest spend per run</span>
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
                <td>
                  <span className="id">{r.run_id.slice(0, 8)}</span>
                </td>
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
  )
}
