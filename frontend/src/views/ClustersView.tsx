/**
 * Static port of the Clusters view from the design.
 * The backend doesn't yet expose k8s pod state; this renders deterministic
 * sample data so the design fidelity is preserved.
 */

type Cluster = {
  name: string
  region: string
  pods: number
  warn?: number[]
  fail?: number[]
  idle?: number[]
  cpu: string
  mem: string
  p50: string
  rps: string
  note?: string
  badge: 'emerald' | 'plain' | 'purple'
  badgeLabel: string
}

const CLUSTERS: Cluster[] = [
  { name: 'prod-us-east-1', region: 'aws · k8s 1.30 · 6 nodes · 128 pods', pods: 128, warn: [14, 61], fail: [119], cpu: '62%', mem: '71%', p50: '142ms', rps: '4.8k', note: '2 restarting', badge: 'emerald', badgeLabel: 'healthy' },
  { name: 'prod-eu-west-2', region: 'aws · k8s 1.30 · 4 nodes · 84 pods', pods: 84, warn: [22], cpu: '48%', mem: '54%', p50: '168ms', rps: '2.1k', badge: 'emerald', badgeLabel: 'healthy' },
  { name: 'stg-us-east-1', region: 'aws · k8s 1.30 · 2 nodes · 36 pods', pods: 36, idle: Array.from({ length: 6 }, (_, i) => 30 + i), cpu: '18%', mem: '22%', p50: '184ms', rps: '120', badge: 'plain', badgeLabel: 'staging' },
  { name: 'prod-airgap-gov', region: 'on-prem · k8s 1.30 · 2 nodes · 64 pods · Ollama', pods: 64, cpu: '74%', mem: '81%', p50: '412ms', rps: '820', note: 'offline 14d', badge: 'purple', badgeLabel: 'air-gapped' },
]

export function ClustersView() {
  return (
    <section className="view active" data-screen-label="Clusters">
      <div className="page-head">
        <div className="row">
          <div>
            <h1>Clusters &amp; deployment</h1>
            <p className="sub">4 environments · 312 pods · 14 nodes · 2 regions · sample data</p>
          </div>
          <div className="actions">
            <button className="btn sm">View Helm chart</button>
            <button className="btn sm">Deploy v3.4.2 →</button>
            <button className="btn sm primary">+ New cluster</button>
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="grid-2">
          {CLUSTERS.map((c) => (
            <ClusterCard key={c.name} cluster={c} />
          ))}
        </div>
      </div>
    </section>
  )
}

function ClusterCard({ cluster }: { cluster: Cluster }) {
  const warnSet = new Set(cluster.warn ?? [])
  const failSet = new Set(cluster.fail ?? [])
  const idleSet = new Set(cluster.idle ?? [])
  const badgeClass =
    cluster.badge === 'emerald'
      ? 'badge emerald'
      : cluster.badge === 'purple'
      ? 'badge purple'
      : 'badge'
  return (
    <div className="cluster">
      <div className="top">
        <div>
          <div className="name">{cluster.name}</div>
          <div className="region">{cluster.region}</div>
        </div>
        <span className={badgeClass}>
          {cluster.badge === 'emerald' && <span className="dot live" />} {cluster.badgeLabel}
        </span>
      </div>
      <div className="pods">
        {Array.from({ length: cluster.pods }, (_, i) => {
          let cls = 'pod'
          if (failSet.has(i)) cls += ' fail'
          else if (warnSet.has(i)) cls += ' warn'
          else if (idleSet.has(i)) cls += ' idle'
          return <div key={i} className={cls} />
        })}
      </div>
      <div className="stats">
        <span>
          cpu <b>{cluster.cpu}</b>
        </span>
        <span>
          mem <b>{cluster.mem}</b>
        </span>
        <span>
          p50 <b>{cluster.p50}</b>
        </span>
        <span>
          req/s <b>{cluster.rps}</b>
        </span>
        {cluster.note && <span style={{ color: 'var(--amber-4)' }}>{cluster.note}</span>}
      </div>
    </div>
  )
}
