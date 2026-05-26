import { useEvaluationSummary } from '../api/hooks'

export function EvaluationsView() {
  const q = useEvaluationSummary()
  const e = q.data

  const overall = e
    ? ((e.avg_faithfulness + e.avg_relevance + e.avg_coherence) / 3).toFixed(1)
    : '—'

  return (
    <section className="view active" data-screen-label="Evaluations">
      <div className="page-head">
        <div className="row">
          <div>
            <h1>Evaluations</h1>
            <p className="sub">
              LLM-as-judge · faithfulness · relevance · coherence ·{' '}
              {e ? `${e.sample_count} sampled runs` : '—'}
            </p>
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="kpi-strip">
          <div className="kpi">
            <span className="label">Overall</span>
            <span className="val" style={{ color: 'var(--emerald-4)' }}>
              {overall}<span className="u">/10</span>
            </span>
            <span className="delta">composite</span>
          </div>
          <div className="kpi">
            <span className="label">Faithfulness</span>
            <span className="val">{e ? e.avg_faithfulness.toFixed(1) : '—'}</span>
            <span className="delta">factual grounding</span>
          </div>
          <div className="kpi">
            <span className="label">Relevance</span>
            <span className="val">{e ? e.avg_relevance.toFixed(1) : '—'}</span>
            <span className="delta">on-topic</span>
          </div>
          <div className="kpi">
            <span className="label">Coherence</span>
            <span className="val">{e ? e.avg_coherence.toFixed(1) : '—'}</span>
            <span className="delta">readability</span>
          </div>
          <div className="kpi">
            <span className="label">Hallucination</span>
            <span className="val" style={{ color: (e?.hallucination_rate ?? 0) > 0.01 ? 'var(--red-4)' : 'var(--emerald-4)' }}>
              {e ? (e.hallucination_rate * 100).toFixed(2) : '—'}<span className="u">%</span>
            </span>
            <span className="delta">unsupported claims</span>
          </div>
        </div>

        <div className="grid-2" style={{ marginTop: 16 }}>
          <div className="panel">
            <div className="panel-head">
              <div className="title">Score distribution · sample</div>
            </div>
            <div className="panel-body">
              <svg viewBox="0 0 480 200" width="100%" height={200}>
                {[2, 3, 5, 8, 14, 22, 38, 68, 110, 142, 118, 68].map((v, i, arr) => {
                  const max = Math.max(...arr)
                  const h = (v / max) * 160
                  const x = 20 + i * 38
                  return (
                    <g key={i}>
                      <rect x={x} y={180 - h} width={30} height={h} fill="var(--blue-4)" opacity={0.4 + (i / arr.length) * 0.6} rx={2} />
                      <text x={x + 15} y={195} textAnchor="middle" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">
                        {(i * 0.5 + 4).toFixed(1)}
                      </text>
                    </g>
                  )
                })}
              </svg>
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <div className="title">Failure classes · sample</div>
            </div>
            <div className="panel-body">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <FailBar label="hallucination · unsupported claim" pct={38} count={42} color="var(--red-3)" />
                <FailBar label="tool failure · timeout" pct={25} count={28} color="var(--amber-3)" />
                <FailBar label="policy block · pii" pct={20} count={22} color="var(--purple-3)" />
                <FailBar label="budget guard halt" pct={11} count={12} color="var(--blue-3)" />
                <FailBar label="schema mismatch" pct={6} count={6} color="var(--emerald-3)" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function FailBar({ label, pct, count, color }: { label: string; pct: number; count: number; color: string }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
        <span>{label}</span>
        <span className="mono">
          {count} · {pct}%
        </span>
      </div>
      <div style={{ height: 8, background: 'var(--bg-inset)', borderRadius: 4, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color }} />
      </div>
    </div>
  )
}
