const ROLES = [
  { name: 'admin', desc: 'full read/write across workspaces', count: 2, color: 'red' },
  { name: 'manager', desc: 'approve workflows; read all metrics', count: 8, color: 'amber' },
  { name: 'sales_rep', desc: 'trigger sales_ops; read own runs', count: 24, color: 'blue' },
  { name: 'analyst', desc: 'read-only metrics, traces, audit', count: 12, color: 'purple' },
  { name: 'viewer', desc: 'dashboard read-only', count: 31, color: 'emerald' },
]

export function RbacView() {
  return (
    <section className="view active" data-screen-label="RBAC">
      <div className="page-head">
        <div className="row">
          <div>
            <h1>RBAC &amp; secrets</h1>
            <p className="sub">Roles · policy bundles · secret rotation · JWT auth</p>
          </div>
          <div className="actions">
            <button className="btn sm">Policy bundle</button>
            <button className="btn sm primary">+ Add role</button>
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="panel">
          <div className="panel-head">
            <div className="title">Roles</div>
            <div className="actions">
              <span>{ROLES.length} defined</span>
            </div>
          </div>
          <div className="panel-body flush">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Role</th>
                  <th>Description</th>
                  <th className="num">Users</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {ROLES.map((r) => (
                  <tr key={r.name}>
                    <td>
                      <span className={`badge ${r.color}`}>{r.name}</span>
                    </td>
                    <td style={{ color: 'var(--fg-secondary)' }}>{r.desc}</td>
                    <td className="num">{r.count}</td>
                    <td>
                      <span className="badge emerald">● active</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  )
}
