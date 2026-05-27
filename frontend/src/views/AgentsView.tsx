import { useAgents } from '../api/hooks'
import type { Agent } from '../api/client'

const COLORS = ['blue', 'purple', 'emerald', 'amber', 'red'] as const

export function AgentsView() {
  const q = useAgents()
  const agents = q.data ?? []

  return (
    <section className="view active" data-screen-label="Agents">
      <div className="page-head">
        <div className="row">
          <div>
            <h1>Agent topology</h1>
            <p className="sub">
              Live A2A communication graph · {agents.length} registered agents
              {q.isError && <span style={{ color: 'var(--red-4)', marginLeft: 8 }}>· {q.error.message}</span>}
            </p>
          </div>
          <div className="actions">
            <button className="btn sm" disabled title="Filter UI — wire to real /agents query params">Time range: 60s ▾</button>
            <button className="btn sm" disabled title="Filter UI — wire to real /agents query params">Filter: all workflows ▾</button>
            <a
              href="https://github.com/JoelJohnsonThomas/forgeflow/blob/main/forgeflow/a2a/registry.py"
              target="_blank"
              rel="noopener noreferrer"
              className="btn sm primary"
            >
              + Register agent (docs) →
            </a>
          </div>
        </div>
      </div>
      <div className="page-body">
        <TopologySvg />
        <AgentRegistry agents={agents} loading={q.isLoading} />
      </div>
    </section>
  )
}

function TopologySvg() {
  return (
    <div className="topo">
      <div className="controls">
        <button title="Zoom in">+</button>
        <button title="Zoom out">−</button>
        <button title="Center">◎</button>
      </div>
      <div className="legend">
        <span><i style={{ background: 'var(--blue-4)' }} />supervisor</span>
        <span><i style={{ background: 'var(--purple-4)' }} />research</span>
        <span><i style={{ background: 'var(--emerald-4)' }} />analysis</span>
        <span><i style={{ background: 'var(--amber-4)' }} />execute</span>
        <span><i style={{ background: 'var(--fg-muted)' }} />tool</span>
      </div>
      <svg viewBox="0 0 1200 540" width="100%" height="100%">
        <defs>
          <radialGradient id="agent-glow-blue" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--blue-4)" stopOpacity="0.4" />
            <stop offset="100%" stopColor="var(--blue-4)" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="agent-glow-purple" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--purple-4)" stopOpacity="0.4" />
            <stop offset="100%" stopColor="var(--purple-4)" stopOpacity="0" />
          </radialGradient>
          <pattern id="topo-grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="oklch(0.30 0.012 250 / 0.3)" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="1200" height="540" fill="url(#topo-grid)" />

        <g fill="none">
          <line x1="600" y1="270" x2="320" y2="160" stroke="var(--blue-3)" strokeWidth="2.5" opacity="0.5" />
          <line x1="600" y1="270" x2="320" y2="380" stroke="var(--blue-3)" strokeWidth="2" opacity="0.5" />
          <line x1="600" y1="270" x2="880" y2="160" stroke="var(--blue-3)" strokeWidth="3" opacity="0.5" />
          <line x1="600" y1="270" x2="880" y2="380" stroke="var(--blue-3)" strokeWidth="2.2" opacity="0.5" />
          <line x1="320" y1="160" x2="880" y2="380" stroke="var(--purple-3)" strokeWidth="1.5" opacity="0.45" strokeDasharray="4 4" />
          <line x1="320" y1="380" x2="880" y2="160" stroke="var(--purple-3)" strokeWidth="1.3" opacity="0.45" strokeDasharray="4 4" />
          <line x1="880" y1="160" x2="880" y2="380" stroke="var(--purple-3)" strokeWidth="1.6" opacity="0.45" strokeDasharray="4 4" />
          <line x1="320" y1="160" x2="100" y2="100" stroke="var(--fg-muted)" strokeWidth="1" opacity="0.4" />
          <line x1="320" y1="380" x2="100" y2="440" stroke="var(--fg-muted)" strokeWidth="1" opacity="0.4" />
          <line x1="880" y1="160" x2="1100" y2="100" stroke="var(--fg-muted)" strokeWidth="1" opacity="0.4" />
          <line x1="880" y1="380" x2="1100" y2="380" stroke="var(--fg-muted)" strokeWidth="1" opacity="0.4" />
          <line x1="880" y1="380" x2="1100" y2="460" stroke="var(--fg-muted)" strokeWidth="1" opacity="0.4" />
        </g>

        <g>
          <circle r="3" fill="oklch(0.86 0.10 240)">
            <animateMotion dur="1.8s" repeatCount="indefinite" path="M 600 270 L 320 160" />
          </circle>
          <circle r="3" fill="oklch(0.86 0.10 240)">
            <animateMotion dur="2.2s" repeatCount="indefinite" begin="0.4s" path="M 600 270 L 880 160" />
          </circle>
          <circle r="3" fill="oklch(0.84 0.14 295)">
            <animateMotion dur="2.6s" repeatCount="indefinite" begin="0.9s" path="M 320 160 L 880 380" />
          </circle>
          <circle r="3" fill="oklch(0.86 0.10 240)">
            <animateMotion dur="2.0s" repeatCount="indefinite" begin="1.2s" path="M 600 270 L 880 380" />
          </circle>
          <circle r="3" fill="oklch(0.78 0.16 75)">
            <animateMotion dur="1.6s" repeatCount="indefinite" begin="0.6s" path="M 880 380 L 1100 460" />
          </circle>
        </g>

        <AgentNode x={540} y={220} color="blue" big eyebrow="SUPERVISOR" name="router" sub="412 hops/min" />
        <AgentNode x={260} y={110} color="purple" name="researcher" sub="v2.1 · 142 rpm" glow />
        <AgentNode x={820} y={110} color="emerald" name="analyzer" sub="v3.0 · 128 rpm" />
        <AgentNode x={260} y={330} color="purple" name="enricher" sub="v1.4 · 86 rpm" />
        <AgentNode x={820} y={330} color="amber" name="executor" sub="v3.0 · 109 rpm" />

        <ToolNode x={40} y={70} label="tavily.web_search" />
        <ToolNode x={40} y={410} label="internal.crm" />
        <ToolNode x={1040} y={70} label="memory.recall" />
        <ToolNode x={1040} y={350} label="salesforce.write" />
        <ToolNode x={1040} y={430} label="smtp.send" />
      </svg>
    </div>
  )
}

function AgentNode({
  x, y, color, name, sub, eyebrow, big, glow,
}: {
  x: number; y: number; color: 'blue' | 'purple' | 'emerald' | 'amber'; name: string; sub: string; eyebrow?: string; big?: boolean; glow?: boolean
}) {
  const r = big ? 48 : 40
  const stroke = `var(--${color}-3)`
  const fill = `var(--${color}-4)`
  return (
    <g transform={`translate(${x} ${y})`}>
      {(big || glow) && <circle cx={60} cy={50} r={big ? 110 : 80} fill={`url(#agent-glow-${color === 'purple' ? 'purple' : 'blue'})`} />}
      <circle cx={60} cy={50} r={r} fill="var(--bg-elevated)" stroke={stroke} strokeWidth={big ? 2 : 1.6} />
      {eyebrow && (
        <text x={60} y={44} textAnchor="middle" fontFamily="var(--font-mono)" fontSize="10" fill={fill} letterSpacing="2">
          {eyebrow}
        </text>
      )}
      <text x={60} y={eyebrow ? 60 : 48} textAnchor="middle" fontFamily="var(--font-sans)" fontSize={big ? 13 : 12} fill="var(--fg-primary)" fontWeight="500">
        {name}
      </text>
      <text x={60} y={eyebrow ? 76 : 64} textAnchor="middle" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">
        {sub}
      </text>
    </g>
  )
}

function ToolNode({ x, y, label }: { x: number; y: number; label: string }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect width="120" height="34" rx="6" fill="var(--bg-overlay)" stroke="var(--border-default)" />
      <text x="12" y="14" fontFamily="var(--font-mono)" fontSize="8" fill="var(--fg-muted)" letterSpacing="1.5">
        MCP TOOL
      </text>
      <text x="12" y="27" fontFamily="var(--font-sans)" fontSize="11" fill="var(--fg-primary)">
        {label}
      </text>
    </g>
  )
}

function colorFor(idx: number) {
  return COLORS[idx % COLORS.length]
}

function initials(name: string) {
  const parts = name.split(/[\s_-]/).filter(Boolean)
  return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase() || name.slice(0, 2).toUpperCase()
}

function AgentRegistry({ agents, loading }: { agents: Agent[]; loading: boolean }) {
  return (
    <div className="panel" style={{ marginTop: 16 }}>
      <div className="panel-head">
        <div className="title">Agent registry</div>
        <div className="actions">
          <span>{loading ? 'loading…' : `${agents.length} agents`}</span>
        </div>
      </div>
      <div className="panel-body flush">
        <table className="tbl">
          <thead>
            <tr>
              <th>Agent</th>
              <th>ID</th>
              <th>Capabilities</th>
              <th>Endpoint</th>
              <th>Health</th>
            </tr>
          </thead>
          <tbody>
            {agents.length === 0 && !loading && (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: 32, color: 'var(--fg-muted)' }}>
                  No agents registered.
                </td>
              </tr>
            )}
            {agents.map((a, i) => (
              <tr key={a.agent_id}>
                <td>
                  <span className="agent-av">
                    <span className={`av ${colorFor(i)}`}>{initials(a.name)}</span>
                    <span className="name">{a.name}</span>
                  </span>
                </td>
                <td className="mono num">{a.agent_id.slice(0, 12)}</td>
                <td>
                  {(a.capabilities ?? []).slice(0, 3).map((c) => (
                    <span key={c} className="badge" style={{ marginRight: 4 }}>
                      {c}
                    </span>
                  ))}
                </td>
                <td className="mono num" style={{ color: 'var(--fg-muted)' }}>
                  {a.endpoint}
                </td>
                <td>
                  <span className="badge emerald">● healthy</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
