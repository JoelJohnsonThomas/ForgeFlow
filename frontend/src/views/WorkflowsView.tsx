const TEMPLATES = [
  {
    name: 'sales_ops',
    title: 'Sales lead qualification',
    desc: 'qualify → research → analyze → propose → approve → execute',
    color: 'blue',
  },
  {
    name: 'support_ops',
    title: 'Customer support triage',
    desc: 'triage → investigate → respond → escalate → resolve',
    color: 'emerald',
  },
  {
    name: 'finance_recon',
    title: 'Finance reconciliation',
    desc: 'ingest → match → flag_variance → approve → post',
    color: 'amber',
  },
]

export function WorkflowsView() {
  return (
    <section className="view active" data-screen-label="Workflows">
      <div className="page-head">
        <div className="row">
          <div>
            <h1>Workflows</h1>
            <p className="sub">3 built-in templates · POST /workflows/run to trigger</p>
          </div>
          <div className="actions">
            <button className="btn sm primary">+ Build new</button>
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="grid-3">
          {TEMPLATES.map((t) => (
            <div key={t.name} className="card" style={{ padding: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <span className={`badge ${t.color}`}>{t.name}</span>
              </div>
              <h3 style={{ margin: '0 0 6px', fontSize: 17, fontWeight: 500, letterSpacing: 'var(--tracking-tight)' }}>
                {t.title}
              </h3>
              <p style={{ margin: 0, color: 'var(--fg-secondary)', fontSize: 13, lineHeight: 1.5 }}>{t.desc}</p>
              <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
                <button className="btn sm primary">Run →</button>
                <button className="btn sm">View graph</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
