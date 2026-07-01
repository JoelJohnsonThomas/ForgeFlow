import { useEffect, useMemo } from 'react'
import { Link } from '@tanstack/react-router'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import '../styles/architecture.css'

export function ArchitecturePage() {
  useDocumentTitle('Architecture — reference topology')
  useEffect(() => {
    document.body.classList.add('architecture')
    return () => document.body.classList.remove('architecture')
  }, [])

  return (
    <>
      <ArchTopbar />
      <div className="arch-page">
        <PageHeader />
        <Section01 />
        <Section02 />
        <Section03 />
        <Section04 />
        <Section05 />
        <Section06 />
        <Section07 />
        <Section08 />
        <Endnote />
      </div>
    </>
  )
}

function ArchTopbar() {
  return (
    <header className="arch-topbar">
      <div className="inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
          <Link to="/" className="brand">
            <span className="brand-mark" />
            <span className="brand-name">ForgeFlow</span>
          </Link>
          <ul>
            <li><a href="/design-hub">Index</a></li>
            <li><a href="/">Landing</a></li>
            <li><a href="/console">Console</a></li>
            <li><a href="/architecture" className="active">Architecture</a></li>
            <li><a href="/design-system">Design system</a></li>
          </ul>
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-muted)' }}>
          v3.4.1 · 2026.05.21
        </div>
      </div>
    </header>
  )
}

function PageHeader() {
  return (
    <div className="top">
      <div>
        <div className="section-eyebrow">System</div>
        <h1 className="page-h1" style={{ marginTop: 8 }}>The anatomy of a workflow.</h1>
        <p className="lede">
          Eight visualizations of ForgeFlow's runtime — from a single supervisor decision to a multi-region
          Kubernetes deploy. Use this as the reference architecture for security reviews, platform onboarding,
          and capacity planning.
        </p>
        <p
          role="note"
          style={{
            marginTop: 14,
            padding: '8px 12px',
            borderLeft: '2px solid var(--amber-4)',
            background: 'var(--bg-inset)',
            borderRadius: 6,
            fontSize: 12.5,
            color: 'var(--fg-secondary)',
            maxWidth: '72ch',
          }}
        >
          <b style={{ color: 'var(--amber-4)' }}>Reference architecture.</b> Figures, node counts, and latencies on
          this page are illustrative — a target topology, not live telemetry from a running cluster. Multi-region
          failover and the air-gapped enclave describe a deployment pattern, not a hosted service.
        </p>
      </div>
      <div style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-muted)', lineHeight: 1.6 }}>
        8 sections<br />
        LangGraph · MCP · A2A · pgvector<br />
        Apache 2.0
      </div>
    </div>
  )
}

function SectionHeader({ num, title, sub }: { num: string; title: string; sub: string }) {
  return (
    <div className="h">
      <span className="num">{num}</span>
      <h2>{title}</h2>
      <span className="sub" style={{ marginLeft: 'auto' }}>{sub}</span>
    </div>
  )
}

/* ── 01 · Supervisor orchestration ───────────────────────────────────── */
function Section01() {
  return (
    <section className="block">
      <SectionHeader num="01" title="Supervisor orchestration" sub="hub-and-spoke · structured routing · LangGraph" />
      <div className="pair">
        <div className="canvas">
          <div className="meta-strip">
            <span>StateGraph · sales_ops · 6 nodes · 14 edges</span>
            <span style={{ display: 'flex', gap: 14 }}>
              <LegendSwatch color="var(--blue-4)" label="supervisor" />
              <LegendSwatch color="var(--fg-muted)" label="worker" />
              <LegendSwatch color="var(--amber-4)" label="interrupt" />
            </span>
          </div>
          <svg viewBox="0 0 800 480" width="100%" height={480} className="diagram-grid" role="img" aria-label="Supervisor orchestration: a hub-and-spoke StateGraph where one supervisor routes work to researcher, analyzer, and executor workers, with a human-approval interrupt before execution. State is checkpointed on every transition.">
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                <path d="M0,0 L10,5 L0,10 z" fill="var(--fg-muted)" />
              </marker>
              <marker id="arrow-blue" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                <path d="M0,0 L10,5 L0,10 z" fill="var(--blue-4)" />
              </marker>
            </defs>
            <g transform="translate(40 200)">
              <circle cx="20" cy="20" r="18" fill="var(--bg-page)" stroke="var(--border-default)" strokeWidth="1.4" />
              <text x="20" y="24" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="10" fill="var(--fg-muted)" letterSpacing="1">START</text>
            </g>
            <g transform="translate(330 180)">
              <rect width="140" height="80" rx="14" className="node accent-blue" />
              <text x="70" y="22" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="9" fill="var(--blue-4)" letterSpacing="2">SUPERVISOR</text>
              <text x="70" y="42" textAnchor="middle" fontFamily="var(--font-sans)" fontSize="14" fill="var(--fg-primary)" fontWeight="500">router</text>
              <text x="70" y="58" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">RoutingDecision</text>
              <text x="70" y="72" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">structured-out</text>
            </g>
            <WorkerNode y={60} accent="accent-purple" color="var(--purple-4)" name="researcher" sub="web_search · scrape" />
            <WorkerNode y={160} accent="accent-emerald" color="var(--emerald-4)" name="analyzer" sub="structured(LeadScore)" />
            <WorkerNode y={260} accent="accent-amber" color="var(--amber-4)" name="executor" sub="CRM · email · write" />
            <g transform="translate(600 360)">
              <rect width="160" height="60" rx="10" className="node accent-amber" strokeDasharray="5 4" />
              <text x="14" y="18" fontFamily="var(--font-mono)" fontSize="9" fill="var(--amber-4)" letterSpacing="2">INTERRUPT</text>
              <text x="14" y="36" fontFamily="var(--font-sans)" fontSize="12" fill="var(--fg-primary)" fontWeight="500">human_approval</text>
              <text x="14" y="50" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">interrupt_before</text>
            </g>
            <g transform="translate(40 420)">
              <circle cx="20" cy="20" r="18" fill="var(--bg-page)" stroke="var(--emerald-3)" strokeWidth="1.4" />
              <text x="20" y="24" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="10" fill="var(--emerald-4)" letterSpacing="1">END</text>
            </g>
            <g fill="none" stroke="var(--fg-muted)" strokeWidth="1.2">
              <path d="M 80 220 C 200 220, 240 220, 330 220" markerEnd="url(#arrow)" />
              <path d="M 470 200 C 530 130, 560 100, 600 90" markerEnd="url(#arrow)" />
              <path d="M 470 220 C 540 200, 560 195, 600 190" markerEnd="url(#arrow)" />
              <path d="M 470 240 C 540 270, 560 285, 600 290" markerEnd="url(#arrow)" />
              <path d="M 470 250 C 520 350, 560 385, 600 390" markerEnd="url(#arrow)" strokeDasharray="4 3" />
              <path d="M 600 80 C 510 80, 470 130, 470 180" stroke="var(--blue-3)" opacity="0.5" markerEnd="url(#arrow-blue)" />
              <path d="M 600 180 C 510 170, 480 180, 470 200" stroke="var(--blue-3)" opacity="0.5" markerEnd="url(#arrow-blue)" />
              <path d="M 600 280 C 510 270, 480 250, 470 240" stroke="var(--blue-3)" opacity="0.5" markerEnd="url(#arrow-blue)" />
              <path d="M 400 260 C 300 380, 200 430, 80 438" markerEnd="url(#arrow)" stroke="var(--emerald-3)" opacity="0.6" />
            </g>
            <text x="200" y="210" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">user_payload</text>
            <text x="510" y="180" fontFamily="var(--font-mono)" fontSize="9" fill="var(--blue-4)">route(stage)</text>
          </svg>
          <div className="legend-row">
            <span><span className="solid" style={{ color: 'var(--fg-muted)' }} /> route forward</span>
            <span><span className="solid" style={{ color: 'var(--blue-4)' }} /> return to supervisor</span>
            <span><span className="dashed" style={{ color: 'var(--fg-muted)' }} /> interruptible edge</span>
            <span style={{ marginLeft: 'auto' }}>checkpoint persisted on every transition</span>
          </div>
        </div>
        <div className="copy">
          <h3>One supervisor decides. The graph stays deterministic.</h3>
          <p>
            Every step, the supervisor reads the current state and emits a typed{' '}
            <span className="mono" style={{ color: 'var(--blue-4)' }}>RoutingDecision = {`{next: Worker, reasoning: str}`}</span>.
            The conditional edge consumes the decision and picks the next node — no string parsing, no "agent freelancing."
          </p>
          <p>
            Workers run, mutate state, and return. The supervisor runs again. Interruptible nodes pause the graph
            cleanly and resume from a token — no in-memory continuation hacks.
          </p>
          <KvTable rows={[
            ['Routing model', 'gpt-4o · structured_output'],
            ['State schema', 'WorkflowState · Pydantic'],
            ['Checkpoint', 'postgres://checkpoints/wf_*'],
            ['Resume', 'any worker · any region · any pod'],
            ['p50 routing latency', '412ms'],
          ]} />
        </div>
      </div>
    </section>
  )
}

function WorkerNode({ y, accent, color, name, sub }: { y: number; accent: string; color: string; name: string; sub: string }) {
  return (
    <g transform={`translate(600 ${y})`}>
      <rect width="160" height="60" rx="10" className={`node ${accent}`} />
      <text x="14" y="18" fontFamily="var(--font-mono)" fontSize="9" fill={color} letterSpacing="2">WORKER</text>
      <text x="14" y="36" fontFamily="var(--font-sans)" fontSize="12" fill="var(--fg-primary)" fontWeight="500">{name}</text>
      <text x="14" y="50" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">{sub}</text>
    </g>
  )
}

function LegendSwatch({ color, label }: { color: string; label: string }) {
  return (
    <span>
      <i style={{ display: 'inline-block', width: 8, height: 8, background: color, borderRadius: '50%', marginRight: 4 }} />
      {label}
    </span>
  )
}

function KvTable({ rows }: { rows: [string, string][] }) {
  return (
    <table className="kv" style={{ marginTop: 14 }}>
      <tbody>
        {rows.map(([k, v]) => (
          <tr key={k}><td>{k}</td><td>{v}</td></tr>
        ))}
      </tbody>
    </table>
  )
}

/* ── 02 · A2A communication ──────────────────────────────────────────── */
function Section02() {
  return (
    <section className="block">
      <SectionHeader num="02" title="A2A communication" sub="JSON-RPC 2.0 · capability discovery · direct worker-to-worker" />
      <div className="pair">
        <div className="copy">
          <h3>Workers can talk past the supervisor.</h3>
          <p>
            For latency-sensitive collaboration — passing enrichment between researcher and analyzer,
            broadcasting a shared lookup — workers exchange A2A messages over JSON-RPC 2.0. Each agent publishes
            an <span className="mono" style={{ color: 'var(--purple-4)' }}>AgentCard</span> describing capabilities;
            the registry resolves <span className="mono">capability/v</span> to a live endpoint.
          </p>
          <p>The supervisor still owns workflow state and routing. A2A is for sideband collaboration, not control flow.</p>
          <KvTable rows={[
            ['Wire format', 'JSON-RPC 2.0 over HTTP/2'],
            ['Discovery', 'AgentCard · capability/v1.json'],
            ['Auth', 'mTLS · workload identity'],
            ['Tracing', 'OTel · W3C traceparent'],
            ['Backpressure', 'token-bucket per peer'],
          ]} />
        </div>
        <div className="canvas">
          <div className="meta-strip">
            <span>A2A registry · 14 cards · 38 capabilities</span>
            <span>JSON-RPC 2.0</span>
          </div>
          <svg viewBox="0 0 520 420" width="100%" height={420} className="diagram-grid" role="img" aria-label="Agent-to-agent communication: workers register capability cards with a central registry and exchange peer-to-peer messages over JSON-RPC 2.0, while the supervisor still owns workflow state and routing.">
            <g transform="translate(220 180)">
              <rect width="100" height="60" rx="10" className="node accent-purple" />
              <text x="50" y="20" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="9" fill="var(--purple-4)" letterSpacing="2">REGISTRY</text>
              <text x="50" y="40" textAnchor="middle" fontFamily="var(--font-sans)" fontSize="12" fill="var(--fg-primary)" fontWeight="500">a2a.svc</text>
              <text x="50" y="54" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="8" fill="var(--fg-muted)">14 cards</text>
            </g>
            <A2AAgent x={40} y={60} accent="accent-purple" color="var(--purple-4)" name="researcher" cap="research/v2" />
            <A2AAgent x={360} y={60} accent="accent-emerald" color="var(--emerald-4)" name="analyzer" cap="score/v3" />
            <A2AAgent x={40} y={320} accent="accent-purple" color="var(--purple-4)" name="enricher" cap="enrich/v1" />
            <A2AAgent x={360} y={320} accent="accent-amber" color="var(--amber-4)" name="executor" cap="execute/v3" />
            <g fill="none" stroke="var(--fg-muted)" strokeWidth="1" strokeDasharray="2 4" opacity="0.6">
              <path d="M 160 84 C 200 84, 240 140, 270 180" />
              <path d="M 360 84 C 320 90, 290 140, 270 180" />
              <path d="M 160 344 C 220 320, 240 250, 270 240" />
              <path d="M 360 344 C 320 320, 290 250, 270 240" />
            </g>
            <text x="180" y="155" fontFamily="var(--font-mono)" fontSize="8" fill="var(--fg-muted)">register</text>
            <g fill="none" stroke="var(--purple-3)" strokeWidth="1.6">
              <path d="M 160 84 C 240 50, 320 50, 360 84" />
              <path d="M 160 344 C 240 380, 320 380, 360 344" />
              <path d="M 100 108 C 60 200, 60 280, 100 320" />
              <path d="M 420 108 C 460 200, 460 280, 420 320" />
            </g>
            <g>
              <rect width="22" height="10" rx="2" fill="var(--purple-4)" opacity="0.85">
                <animateMotion dur="2.4s" repeatCount="indefinite" path="M 160 84 C 240 50, 320 50, 360 84" />
              </rect>
              <rect width="22" height="10" rx="2" fill="var(--purple-4)" opacity="0.85">
                <animateMotion dur="2.6s" repeatCount="indefinite" begin="0.8s" path="M 360 344 C 320 380, 240 380, 160 344" />
              </rect>
              <rect width="22" height="10" rx="2" fill="var(--purple-4)" opacity="0.85">
                <animateMotion dur="3.0s" repeatCount="indefinite" begin="1.4s" path="M 100 108 C 60 200, 60 280, 100 320" />
              </rect>
            </g>
            <g transform="translate(180 130)">
              <rect width="180" height="42" rx="4" fill="var(--bg-overlay)" stroke="var(--border-default)" />
              <text x="10" y="14" fontFamily="var(--font-mono)" fontSize="9" fill="var(--purple-4)" letterSpacing="2">PAYLOAD · 2.1KB</text>
              <text x="10" y="28" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">capability: score_lead/v1</text>
              <text x="10" y="40" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">trace: 9F1C…E08A</text>
            </g>
          </svg>
          <div className="legend-row">
            <span><span className="dashed" style={{ color: 'var(--fg-muted)' }} /> register / lookup</span>
            <span><span className="solid" style={{ color: 'var(--purple-4)' }} /> peer-to-peer message</span>
            <span style={{ marginLeft: 'auto' }}>avg 64ms · p99 184ms</span>
          </div>
        </div>
      </div>
    </section>
  )
}

function A2AAgent({ x, y, accent, color, name, cap }: { x: number; y: number; accent: string; color: string; name: string; cap: string }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect width="120" height="48" rx="8" className={`node ${accent}`} />
      <text x="10" y="16" fontFamily="var(--font-mono)" fontSize="8" fill={color} letterSpacing="2">AGENT</text>
      <text x="10" y="30" fontFamily="var(--font-sans)" fontSize="11" fill="var(--fg-primary)">{name}</text>
      <text x="10" y="42" fontFamily="var(--font-mono)" fontSize="8" fill="var(--fg-muted)">{cap}</text>
    </g>
  )
}

/* ── 03 · MCP tool topology ──────────────────────────────────────────── */
const MCP_TOOLS_LEFT = [
  { name: 'tavily.web_search', ver: 'v2' },
  { name: 'browser.scrape_url', ver: 'v1' },
  { name: 'salesforce.write', ver: 'v3' },
  { name: 'crm.stage', ver: 'v3' },
  { name: 'smtp.send', ver: 'v1' },
]
const MCP_TOOLS_RIGHT = [
  { name: 'memory.recall', ver: 'internal' },
  { name: 'memory.store', ver: 'internal' },
  { name: 'snowflake.query', ver: 'v4' },
  { name: 'jira.create_issue', ver: 'v2' },
  { name: 'slack.notify', ver: 'v2' },
]

function Section03() {
  return (
    <section className="block">
      <SectionHeader num="03" title="MCP tool topology" sub="streamable-HTTP · capability discovery · swap providers" />
      <div className="canvas">
        <div className="meta-strip">
          <span>FastMCP :8001 · 14 tools · 4 providers · 8,124 invocations/min</span>
          <span>streamable-HTTP</span>
        </div>
        <svg viewBox="0 0 1280 360" width="100%" height={360} className="diagram-grid" role="img" aria-label="MCP tool topology: agents call tools through a single FastMCP server that fronts SaaS, data, and on-premise providers over a streamable-HTTP wire format, so providers can be swapped without redeploying agents.">
          <g fontFamily="var(--font-mono)" fontSize="10" fill="var(--fg-muted)" letterSpacing="2">
            <text x="20" y="36">AGENTS</text>
            <text x="500" y="36">MCP SERVER</text>
            <text x="900" y="36">PROVIDERS</text>
          </g>
          <McpAgent y={60} accent="accent-purple" name="researcher" sub="2 tools" />
          <McpAgent y={120} accent="accent-emerald" name="analyzer" sub="1 tool" />
          <McpAgent y={180} accent="accent-amber" name="executor" sub="4 tools" />
          <McpAgent y={240} accent="accent-purple" name="enricher" sub="3 tools" />
          <g transform="translate(420 60)">
            <rect width="440" height="240" rx="12" fill="var(--bg-canvas)" stroke="var(--border-default)" strokeWidth="1.2" />
            <text x="20" y="22" fontFamily="var(--font-mono)" fontSize="10" fill="var(--blue-4)" letterSpacing="2">MCP SERVER · FastMCP</text>
            <text x="20" y="36" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">tools registered: 14</text>
            {MCP_TOOLS_LEFT.map((t, i) => (
              <ToolRow key={t.name} x={20} y={58 + i * 32} width={180} tool={t} />
            ))}
            {MCP_TOOLS_RIGHT.map((t, i) => (
              <ToolRow key={t.name} x={220} y={58 + i * 32} width={200} tool={t} />
            ))}
          </g>
          <McpProvider x={900} y={60} accent="accent-blue" color="var(--blue-4)" eyebrow="SAAS" name="Tavily · Salesforce" sub="Snowflake · Jira · Slack" />
          <McpProvider x={900} y={140} accent="accent-emerald" color="var(--emerald-4)" eyebrow="DATA" name="Postgres · pgvector" sub="memory · checkpoint" />
          <McpProvider x={900} y={220} accent="accent-amber" color="var(--amber-4)" eyebrow="ON-PREM" name="SMTP · Internal CRM" sub="behind VPC" />
          <g fill="none" stroke="var(--fg-muted)" strokeWidth="1" opacity="0.6">
            <path d="M 180 80 C 280 80, 320 80, 420 100" />
            <path d="M 180 140 C 280 140, 320 130, 420 130" />
            <path d="M 180 200 C 280 180, 320 180, 420 160" />
            <path d="M 180 260 C 280 240, 320 240, 420 220" />
            <path d="M 860 90 C 880 90, 880 90, 900 90" />
            <path d="M 860 130 C 880 140, 880 160, 900 160" />
            <path d="M 860 200 C 880 220, 880 240, 900 240" />
          </g>
          <g>
            <circle r="3" fill="var(--blue-4)">
              <animateMotion dur="1.8s" repeatCount="indefinite" path="M 180 80 C 280 80, 320 80, 420 100" />
            </circle>
            <circle r="3" fill="var(--amber-4)">
              <animateMotion dur="2.2s" repeatCount="indefinite" begin="0.3s" path="M 180 200 C 280 180, 320 180, 420 160" />
            </circle>
          </g>
        </svg>
        <div className="legend-row">
          <span>discover · invoke · stream — same wire format across all 14 tools</span>
          <span style={{ marginLeft: 'auto' }}>swap tavily → bing without redeploying any agent</span>
        </div>
      </div>
    </section>
  )
}

function McpAgent({ y, accent, name, sub }: { y: number; accent: string; name: string; sub: string }) {
  return (
    <g transform={`translate(20 ${y})`}>
      <rect width="160" height="44" rx="8" className={`node ${accent}`} />
      <text x="14" y="18" fontFamily="var(--font-sans)" fontSize="12" fill="var(--fg-primary)" fontWeight="500">{name}</text>
      <text x="14" y="34" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">{sub}</text>
    </g>
  )
}

function ToolRow({ x, y, width, tool }: { x: number; y: number; width: number; tool: { name: string; ver: string } }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect width={width} height="26" rx="5" fill="var(--bg-elevated)" stroke="var(--border-subtle)" />
      <text x="10" y="18" fontFamily="var(--font-mono)" fontSize="11" fill="var(--fg-primary)">{tool.name}</text>
      <text x={width - 8} y="18" textAnchor="end" fontSize="9" fill="var(--fg-muted)">{tool.ver}</text>
    </g>
  )
}

function McpProvider({ x, y, accent, color, eyebrow, name, sub }: { x: number; y: number; accent: string; color: string; eyebrow: string; name: string; sub: string }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect width="180" height="60" rx="8" className={`node ${accent}`} />
      <text x="14" y="18" fontFamily="var(--font-mono)" fontSize="9" fill={color} letterSpacing="2">{eyebrow}</text>
      <text x="14" y="36" fontFamily="var(--font-sans)" fontSize="12" fill="var(--fg-primary)">{name}</text>
      <text x="14" y="50" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">{sub}</text>
    </g>
  )
}

/* ── 04 · Semantic memory graph ──────────────────────────────────────── */
// Deterministic cluster point cloud (replaces document.write random scatter).
function makeClusterPoints(seed: number) {
  // Mulberry32 PRNG — tiny, deterministic, plenty for visual scatter.
  let s = seed >>> 0
  function rnd() {
    s |= 0; s = (s + 0x6D2B79F5) | 0
    let t = Math.imul(s ^ (s >>> 15), 1 | s)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
  const clusters = [
    { cx: 200, cy: 160, r: 90, color: 'var(--blue-4)', n: 120 },
    { cx: 510, cy: 190, r: 80, color: 'var(--purple-4)', n: 90 },
    { cx: 280, cy: 350, r: 100, color: 'var(--emerald-4)', n: 110 },
    { cx: 540, cy: 370, r: 70, color: 'var(--amber-4)', n: 70 },
  ]
  const out: { x: number; y: number; color: string }[] = []
  for (const cl of clusters) {
    for (let i = 0; i < cl.n; i++) {
      const a = rnd() * Math.PI * 2
      const r = Math.pow(rnd(), 0.6) * cl.r
      out.push({ x: cl.cx + Math.cos(a) * r, y: cl.cy + Math.sin(a) * r, color: cl.color })
    }
  }
  return out
}

function Section04() {
  const points = useMemo(() => makeClusterPoints(42), [])
  return (
    <section className="block">
      <SectionHeader num="04" title="Semantic memory graph" sub="pgvector · ivfflat · namespace-scoped · cosine" />
      <div className="pair">
        <div className="canvas">
          <div className="meta-strip">
            <span>memory · 1.4M vectors · 1536d · ns:sales/*</span>
            <span>UMAP projection</span>
          </div>
          <svg viewBox="0 0 720 460" width="100%" height={460} className="diagram-grid" role="img" aria-label="Semantic memory: embeddings stored in Postgres with pgvector, projected into clusters by namespace. A query returns the nearest namespace-scoped matches by cosine similarity.">
            <g opacity="0.12">
              <ellipse cx="200" cy="160" rx="140" ry="100" fill="var(--blue-4)" />
              <ellipse cx="510" cy="190" rx="130" ry="95" fill="var(--purple-4)" />
              <ellipse cx="280" cy="350" rx="160" ry="80" fill="var(--emerald-4)" />
              <ellipse cx="540" cy="370" rx="110" ry="65" fill="var(--amber-4)" />
            </g>
            <g fontFamily="var(--font-mono)" fontSize="11" fill="var(--fg-secondary)">
              <text x="120" y="70">ns:sales/stripe</text>
              <text x="450" y="100">ns:sales/vercel</text>
              <text x="190" y="436">ns:policy/global</text>
              <text x="478" y="436">ns:support/*</text>
            </g>
            <g>
              {points.map((p, i) => (
                <circle key={i} cx={p.x.toFixed(1)} cy={p.y.toFixed(1)} r="1.8" fill={p.color} opacity="0.7" />
              ))}
            </g>
            <g>
              <circle cx="240" cy="140" r="9" fill="none" stroke="var(--fg-primary)" strokeWidth="1.6" />
              <circle cx="240" cy="140" r="4" fill="var(--fg-primary)" />
              <line x1="240" y1="140" x2="208" y2="156" stroke="var(--fg-primary)" strokeDasharray="2 3" opacity="0.5" />
              <line x1="240" y1="140" x2="172" y2="148" stroke="var(--fg-primary)" strokeDasharray="2 3" opacity="0.5" />
              <line x1="240" y1="140" x2="226" y2="184" stroke="var(--fg-primary)" strokeDasharray="2 3" opacity="0.5" />
              <circle cx="208" cy="156" r="3.4" fill="var(--fg-primary)" stroke="var(--bg-page)" strokeWidth="1" />
              <circle cx="172" cy="148" r="3.4" fill="var(--fg-primary)" stroke="var(--bg-page)" strokeWidth="1" />
              <circle cx="226" cy="184" r="3.4" fill="var(--fg-primary)" stroke="var(--bg-page)" strokeWidth="1" />
              <g transform="translate(260 130)">
                <rect width="160" height="46" rx="4" fill="var(--bg-overlay)" stroke="var(--border-default)" />
                <text x="10" y="14" fontFamily="var(--font-mono)" fontSize="9" fill="var(--blue-4)" letterSpacing="2">QUERY · k=3</text>
                <text x="10" y="28" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">"expansion deal Q2 2026"</text>
                <text x="10" y="40" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">cos: 0.89 · 0.84 · 0.78</text>
              </g>
            </g>
            <g stroke="var(--fg-faint)" strokeWidth="0.6" strokeDasharray="1 3" opacity="0.6">
              <line x1="240" y1="140" x2="500" y2="180" />
              <line x1="240" y1="140" x2="290" y2="340" />
            </g>
          </svg>
          <div className="legend-row">
            <span>ivfflat · lists=200 · probes=10</span>
            <span style={{ marginLeft: 'auto' }}>p50 recall: 38ms · p99: 92ms</span>
          </div>
        </div>
        <div className="copy">
          <h3>Memory that belongs to the workload, not the LLM.</h3>
          <p>
            Embeddings are stored in Postgres next to the rest of your transactional data — no extra service,
            no consistency story to explain to security. Every entry is scoped to a namespace so workflows can't
            accidentally recall each other's data.
          </p>
          <p>
            Recall is just a tool call: any agent invokes{' '}
            <span className="mono" style={{ color: 'var(--blue-4)' }}>memory.recall(ns, q, k)</span> through MCP
            and gets typed, cited matches.
          </p>
          <KvTable rows={[
            ['Index', 'ivfflat · cosine · 1536d'],
            ['Tenant isolation', 'row-level security · ns prefix'],
            ['Encryption', 'at rest · KMS key per tenant'],
            ['TTL', 'per-namespace policy'],
            ['Right-to-erasure', 'cascading delete by trace_id'],
          ]} />
        </div>
      </div>
    </section>
  )
}

/* ── 05 · State machine & checkpointing ──────────────────────────────── */
type CheckpointKind = 'start' | 'route' | 'work' | 'recall' | 'tool' | 'pause' | 'now'
const CHECKPOINTS: { x: number; lbl: string; kind: CheckpointKind; stage: string }[] = [
  { x: 60, lbl: '#01', kind: 'start', stage: 'qualify' },
  { x: 140, lbl: '#02', kind: 'route', stage: 'route→research' },
  { x: 220, lbl: '#03', kind: 'work', stage: 'research' },
  { x: 300, lbl: '#04', kind: 'work', stage: 'research' },
  { x: 380, lbl: '#05', kind: 'route', stage: 'route→analyze' },
  { x: 460, lbl: '#06', kind: 'work', stage: 'analyze' },
  { x: 540, lbl: '#07', kind: 'recall', stage: 'memory.recall' },
  { x: 620, lbl: '#08', kind: 'route', stage: 'route→propose' },
  { x: 700, lbl: '#09', kind: 'work', stage: 'propose' },
  { x: 780, lbl: '#10', kind: 'tool', stage: 'crm.stage' },
  { x: 860, lbl: '#11', kind: 'tool', stage: 'draft.email' },
  { x: 940, lbl: '#12', kind: 'route', stage: 'route→approval' },
  { x: 1020, lbl: '#13', kind: 'pause', stage: 'interrupt_before' },
  { x: 1100, lbl: '#14', kind: 'now', stage: 'awaiting' },
]
const KIND_COLOR: Record<CheckpointKind, string> = {
  start: 'var(--blue-4)',
  route: 'var(--blue-4)',
  work: 'var(--purple-4)',
  recall: 'var(--emerald-4)',
  tool: 'var(--amber-4)',
  pause: 'var(--amber-4)',
  now: 'oklch(0.96 0.005 250)',
}

function Section05() {
  return (
    <section className="block">
      <SectionHeader num="05" title="Workflow state & checkpointing" sub="every node persists · resumable across pods · forkable" />
      <div className="canvas">
        <div className="meta-strip">
          <span>StateGraph transitions · sales_ops</span>
          <span>14 checkpoints persisted · this run</span>
        </div>
        <div style={{ padding: '28px 32px' }}>
          <div className="state-row">
            <span className="pill start">qualify</span><span className="arr">→</span>
            <span className="pill">research</span><span className="arr">→</span>
            <span className="pill">analyze</span><span className="arr">→</span>
            <span className="pill">propose</span><span className="arr">→</span>
            <span className="pill pause">await_approval</span><span className="arr">→</span>
            <span className="pill">execute</span><span className="arr">→</span>
            <span className="pill end">done</span>
          </div>
          <svg viewBox="0 0 1200 200" width="100%" height={200} style={{ marginTop: 36 }} role="img" aria-label="Workflow state and checkpointing: a timeline of persisted checkpoints across a run, from qualify through routing, work, memory recall, and tool calls, pausing at a human-approval interrupt. Any pod can resume from the latest checkpoint.">
            <line x1="60" y1="100" x2="1140" y2="100" stroke="var(--border-default)" strokeWidth="1" />
            {CHECKPOINTS.map((c) => {
              const col = KIND_COLOR[c.kind]
              const isNow = c.kind === 'now'
              return (
                <g key={c.lbl} transform={`translate(${c.x} 100)`}>
                  <line x1="0" y1="-26" x2="0" y2="0" stroke={col} strokeWidth="1.2" opacity="0.5" />
                  <circle cx="0" cy="0" r={isNow ? 6 : 4} fill={col} stroke="var(--bg-canvas)" strokeWidth="2" />
                  {isNow && (
                    <circle cx="0" cy="0" r="10" fill="none" stroke={col} opacity="0.5">
                      <animate attributeName="r" values="6;14;6" dur="1.6s" repeatCount="indefinite" />
                      <animate attributeName="opacity" values="0.5;0;0.5" dur="1.6s" repeatCount="indefinite" />
                    </circle>
                  )}
                  <text x="0" y="-32" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">{c.lbl}</text>
                  <text x="0" y="22" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="9" fill={col}>{c.stage}</text>
                </g>
              )
            })}
            <text x="1100" y="60" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="10" fill="var(--fg-primary)" letterSpacing="2">NOW</text>
          </svg>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 32, marginTop: 36 }}>
            <ColumnNote eyebrow="Resumability" body={<>Any pod can resume any run by loading the latest checkpoint by <span className="mono" style={{ color: 'var(--blue-4)' }}>run_id</span>. Cold-start latency: 240ms p50.</>} />
            <ColumnNote eyebrow="Replay & fork" body="Fork at any checkpoint to test prompt / model changes against the exact upstream state. Replay produces deterministic transcripts for evaluation." />
            <ColumnNote eyebrow="Audit chain" body="Each checkpoint is hash-chained to the previous one and signed with the pod's workload identity — tamper-evident state for regulated workflows." />
          </div>
        </div>
      </div>
    </section>
  )
}

function ColumnNote({ eyebrow, body }: { eyebrow: string; body: React.ReactNode }) {
  return (
    <div>
      <div className="section-eyebrow">{eyebrow}</div>
      <p style={{ marginTop: 6, color: 'var(--fg-secondary)', fontSize: 13 }}>{body}</p>
    </div>
  )
}

/* ── 06 · Event streaming & observability pipeline ───────────────────── */
function Section06() {
  return (
    <section className="block">
      <SectionHeader num="06" title="Event streaming & observability pipeline" sub="Kafka · Redis · LangSmith · OTel" />
      <div className="canvas">
        <div className="meta-strip">
          <span>~1.8k events/s sustained · 12k peak · 30d retention</span>
          <span>SSE · Kafka · OTel</span>
        </div>
        <svg viewBox="0 0 1280 280" width="100%" height={280} className="diagram-grid" role="img" aria-label="Event streaming and observability pipeline: producers emit events to Kafka topics, fanned out live over Redis Streams and server-sent events to the console, and exported through an OpenTelemetry collector to tracing, analytics, cold storage, and SIEM sinks.">
          <g transform="translate(40 80)">
            <rect width="160" height="120" rx="10" fill="var(--bg-canvas)" stroke="var(--border-default)" />
            <text x="14" y="20" fontFamily="var(--font-mono)" fontSize="9" fill="var(--blue-4)" letterSpacing="2">PRODUCERS</text>
            {['workflow.node', 'tool.invoke', 'agent.message', 'audit.write', 'cost.tick'].map((p, i) => (
              <text key={p} x="14" y={44 + i * 16} fontFamily="var(--font-sans)" fontSize="11" fill="var(--fg-primary)">{p}</text>
            ))}
          </g>
          <g transform="translate(300 60)">
            <rect width="280" height="160" rx="12" fill="var(--bg-canvas)" stroke="var(--border-default)" />
            <text x="20" y="22" fontFamily="var(--font-mono)" fontSize="9" fill="var(--blue-4)" letterSpacing="2">KAFKA · 6 PARTITIONS</text>
            {[
              { name: 'forge.events.runs', rps: '820/s' },
              { name: 'forge.events.tools', rps: '512/s' },
              { name: 'forge.events.audit', rps: '128/s' },
              { name: 'forge.events.cost', rps: '340/s' },
            ].map((t, i) => (
              <g key={t.name} transform={`translate(20 ${36 + i * 28})`}>
                <rect width="240" height="22" rx="4" fill="var(--bg-elevated)" stroke="var(--border-subtle)" />
                <text x="10" y="15" fontFamily="var(--font-mono)" fontSize="10" fill="var(--fg-secondary)">{t.name}</text>
                <text x="232" y="15" textAnchor="end" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">{t.rps}</text>
              </g>
            ))}
          </g>
          <g transform="translate(640 60)">
            <rect width="180" height="80" rx="10" fill="var(--bg-canvas)" stroke="var(--border-default)" />
            <text x="14" y="20" fontFamily="var(--font-mono)" fontSize="9" fill="var(--red-4)" letterSpacing="2">REDIS STREAMS</text>
            <text x="14" y="40" fontFamily="var(--font-sans)" fontSize="12" fill="var(--fg-primary)" fontWeight="500">live fanout</text>
            <text x="14" y="56" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">SSE · UI subs</text>
            <text x="14" y="70" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">~1.6k clients</text>
          </g>
          <g transform="translate(640 152)">
            <rect width="180" height="68" rx="10" fill="var(--bg-canvas)" stroke="var(--border-default)" />
            <text x="14" y="20" fontFamily="var(--font-mono)" fontSize="9" fill="var(--emerald-4)" letterSpacing="2">OTel COLLECTOR</text>
            <text x="14" y="40" fontFamily="var(--font-sans)" fontSize="12" fill="var(--fg-primary)" fontWeight="500">otelcol</text>
            <text x="14" y="56" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">spans · metrics · logs</text>
          </g>
          <Sink x={880} y={60} accent="accent-blue" name="Console UI" sub="live timeline" />
          <Sink x={880} y={116} accent="accent-purple" name="LangSmith" sub="trace · eval" />
          <Sink x={880} y={172} accent="accent-emerald" name="Datadog · Honeycomb" sub="OTel out" />
          <Sink x={1080} y={60} accent="accent-amber" name="S3 cold" sub="WORM · 7y" />
          <Sink x={1080} y={116} accent="accent-red" name="SIEM · Splunk" sub="audit pipe" />
          <Sink x={1080} y={172} accent="accent-emerald" name="Postgres · pgvector" sub="analytics" />
          <g fill="none" stroke="var(--fg-muted)" strokeWidth="1" opacity="0.55">
            <path d="M 200 110 C 240 110, 270 110, 300 110" />
            <path d="M 200 130 C 240 130, 270 130, 300 130" />
            <path d="M 200 150 C 240 150, 270 150, 300 150" />
            <path d="M 580 90 C 600 90, 620 90, 640 90" />
            <path d="M 580 130 C 600 140, 620 170, 640 180" />
            <path d="M 820 80 C 850 80, 860 80, 880 80" />
            <path d="M 820 100 C 850 110, 860 130, 880 130" />
            <path d="M 820 180 C 850 180, 860 180, 880 180" />
            <path d="M 1040 80 C 1060 80, 1060 80, 1080 80" />
            <path d="M 1040 132 C 1060 130, 1060 130, 1080 130" />
            <path d="M 1040 190 C 1060 190, 1060 190, 1080 190" />
          </g>
          <g>
            <rect width="6" height="6" fill="var(--blue-4)">
              <animateMotion dur="1.6s" repeatCount="indefinite" path="M 200 110 C 280 110, 320 110, 580 110" />
            </rect>
            <rect width="6" height="6" fill="var(--amber-4)">
              <animateMotion dur="2.0s" repeatCount="indefinite" begin="0.4s" path="M 200 130 C 280 130, 320 130, 580 130" />
            </rect>
            <rect width="6" height="6" fill="var(--emerald-4)">
              <animateMotion dur="2.2s" repeatCount="indefinite" begin="0.8s" path="M 200 150 C 280 150, 320 150, 580 150" />
            </rect>
          </g>
        </svg>
      </div>
    </section>
  )
}

function Sink({ x, y, accent, name, sub }: { x: number; y: number; accent: string; name: string; sub: string }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect width="160" height="44" rx="8" className={`node ${accent}`} />
      <text x="14" y="18" fontFamily="var(--font-sans)" fontSize="11" fill="var(--fg-primary)">{name}</text>
      <text x="14" y="34" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">{sub}</text>
    </g>
  )
}

/* ── 07 · Kubernetes deployment topology ─────────────────────────────── */
type PodKind = 'api' | 'sup' | 'rs' | 'an' | 'ex' | 'mcp' | 'pg' | 'r' | ''
type Node = { name: string; size: string; cpu: string; mem: string; pods: { kind: PodKind; label: string }[] }

const K8S_NODES: Node[] = [
  {
    name: 'node-01 · m6i.4xlarge', size: '', cpu: '64%', mem: '71%',
    pods: [
      { kind: 'api', label: 'api' }, { kind: 'api', label: 'api' }, { kind: 'api', label: 'api' },
      { kind: 'sup', label: 'sup' }, { kind: 'sup', label: 'sup' },
      { kind: 'rs', label: 'rs' }, { kind: 'an', label: 'an' }, { kind: 'an', label: 'an' },
      { kind: 'ex', label: 'ex' }, { kind: 'ex', label: 'ex' },
      { kind: 'mcp', label: 'mcp' }, { kind: 'mcp', label: 'mcp' },
      { kind: 'pg', label: 'pg' }, { kind: 'pg', label: 'pg' },
      { kind: '', label: 'o11y' }, { kind: '', label: 'otel' },
    ],
  },
  {
    name: 'node-02 · m6i.4xlarge', size: '', cpu: '58%', mem: '64%',
    pods: [
      { kind: 'api', label: 'api' }, { kind: 'api', label: 'api' },
      { kind: 'sup', label: 'sup' }, { kind: 'sup', label: 'sup' },
      { kind: 'rs', label: 'rs' }, { kind: 'rs', label: 'rs' },
      { kind: 'an', label: 'an' },
      { kind: 'ex', label: 'ex' }, { kind: 'ex', label: 'ex' }, { kind: 'ex', label: 'ex' },
      { kind: 'mcp', label: 'mcp' }, { kind: 'pg', label: 'pg' },
      { kind: '', label: 'kafka' }, { kind: '', label: 'redis' }, { kind: '', label: 'otel' }, { kind: '', label: 'cron' },
    ],
  },
  {
    name: 'node-03 · m6i.4xlarge', size: '', cpu: '61%', mem: '68%',
    pods: [
      { kind: 'api', label: 'api' }, { kind: 'sup', label: 'sup' },
      { kind: 'rs', label: 'rs' }, { kind: 'rs', label: 'rs' },
      { kind: 'an', label: 'an' }, { kind: 'an', label: 'an' },
      { kind: 'ex', label: 'ex' }, { kind: 'ex', label: 'ex' },
      { kind: 'mcp', label: 'mcp' }, { kind: 'mcp', label: 'mcp' },
      { kind: 'pg', label: 'pg' }, { kind: 'r', label: 'r' },
      { kind: '', label: 'kafka' }, { kind: '', label: 'redis' }, { kind: '', label: 'otel' }, { kind: '', label: 'vault' },
    ],
  },
  {
    name: 'node-04 · m6i.4xlarge', size: '', cpu: '49%', mem: '52%',
    pods: [
      { kind: 'api', label: 'api' }, { kind: 'sup', label: 'sup' }, { kind: 'rs', label: 'rs' },
      { kind: 'an', label: 'an' }, { kind: 'ex', label: 'ex' }, { kind: 'ex', label: 'ex' },
      { kind: 'mcp', label: 'mcp' }, { kind: 'mcp', label: 'mcp' },
      { kind: 'pg', label: 'pg' },
      { kind: '', label: 'kafka' }, { kind: '', label: 'redis' }, { kind: '', label: 'otel' },
      { kind: '', label: 'vault' }, { kind: '', label: 'dash' }, { kind: '', label: 'cron' }, { kind: '', label: 'jobs' },
    ],
  },
  {
    name: 'node-05 · m6i.4xlarge', size: '', cpu: '71%', mem: '78%',
    pods: [
      { kind: 'api', label: 'api' }, { kind: 'sup', label: 'sup' },
      { kind: 'rs', label: 'rs' }, { kind: 'rs', label: 'rs' },
      { kind: 'an', label: 'an' }, { kind: 'an', label: 'an' },
      { kind: 'ex', label: 'ex' }, { kind: 'ex', label: 'ex' }, { kind: 'ex', label: 'ex' },
      { kind: 'mcp', label: 'mcp' }, { kind: 'mcp', label: 'mcp' },
      { kind: 'pg', label: 'pg' },
      { kind: '', label: 'kafka' }, { kind: '', label: 'redis' }, { kind: '', label: 'otel' }, { kind: '', label: 'dash' },
    ],
  },
  {
    name: 'node-06 · m6i.4xlarge', size: '', cpu: '54%', mem: '62%',
    pods: [
      { kind: 'api', label: 'api' }, { kind: 'sup', label: 'sup' }, { kind: 'rs', label: 'rs' },
      { kind: 'an', label: 'an' }, { kind: 'an', label: 'an' },
      { kind: 'ex', label: 'ex' }, { kind: 'ex', label: 'ex' },
      { kind: 'mcp', label: 'mcp' }, { kind: 'mcp', label: 'mcp' },
      { kind: 'pg', label: 'pg' },
      { kind: '', label: 'kafka' }, { kind: '', label: 'redis' }, { kind: '', label: 'otel' },
      { kind: '', label: 'dash' }, { kind: '', label: 'jobs' }, { kind: '', label: 'jobs' },
    ],
  },
]

function Section07() {
  return (
    <section className="block">
      <SectionHeader num="07" title="Kubernetes deployment topology" sub="3 namespaces · HPA · NetworkPolicy · 0-egress for air-gap" />
      <div className="canvas">
        <div className="meta-strip">
          <span>prod-us-east-1 · k8s 1.30 · 6 nodes · 128 pods</span>
          <span>Helm chart · forgeflow-3.4.1</span>
        </div>
        <div className="k8s-nodes" role="img" aria-label="Kubernetes deployment topology: six worker nodes each running a mix of API, supervisor, worker, MCP, Postgres, and platform pods, with the horizontal pod autoscaler scaling API, researcher, and executor pods on p95 latency.">
          {K8S_NODES.map((n) => (
            <div className="k8s-node" key={n.name}>
              <div className="hd">
                <b>{n.name}</b>
                <span>cpu {n.cpu} · mem {n.mem}</span>
              </div>
              <div className="pods">
                {n.pods.map((p, i) => (
                  <div key={`${p.label}-${i}`} className={`pod${p.kind ? ` ${p.kind}` : ''}`}>{p.label}</div>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="legend-row">
          <span><i style={{ background: 'oklch(0.28 0.07 240 / 0.5)', border: '1px solid var(--blue-3)' }} />api</span>
          <span><i style={{ background: 'oklch(0.42 0.13 240 / 0.4)', border: '1px solid var(--blue-3)' }} />supervisor</span>
          <span><i style={{ background: 'oklch(0.28 0.08 295 / 0.5)', border: '1px solid var(--purple-3)' }} />researcher</span>
          <span><i style={{ background: 'oklch(0.26 0.06 160 / 0.5)', border: '1px solid var(--emerald-3)' }} />analyzer</span>
          <span><i style={{ background: 'oklch(0.30 0.06 75 / 0.5)', border: '1px solid var(--amber-3)' }} />executor</span>
          <span><i style={{ background: 'oklch(0.26 0.06 160 / 0.3)', border: '1px solid var(--emerald-2)' }} />postgres</span>
          <span><i style={{ background: 'oklch(0.28 0.10 25 / 0.3)', border: '1px solid var(--red-3)' }} />restarting</span>
          <span style={{ marginLeft: 'auto' }}>HPA scales api · researcher · executor on p95 latency</span>
        </div>
      </div>
    </section>
  )
}

/* ── 08 · Multi-region failover & air-gap ────────────────────────────── */
function Section08() {
  return (
    <section className="block">
      <SectionHeader num="08" title="Multi-region failover & air-gap" sub="checkpoint replication · RPO 5s · air-gap parity" />
      <div className="canvas">
        <div className="meta-strip">
          <span>3 regions · 1 air-gapped enclave · cross-region p99 84ms</span>
          <span>RPO 5s · RTO 90s</span>
        </div>
        <svg viewBox="0 0 1280 380" width="100%" height={380} className="diagram-grid" role="img" aria-label="Multi-region failover and air-gap: a primary region streams write-ahead-log changes to a warm read-only standby, while a fully air-gapped enclave runs independently with a local LLM and receives updates only via signed offline bundles.">
          <defs>
            <marker id="arrow-r" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M0,0 L10,5 L0,10 z" fill="var(--fg-muted)" />
            </marker>
          </defs>
          <Region x={80} color="var(--blue-3)" eyebrowColor="var(--blue-4)" eyebrow="PRIMARY · us-east-1" title="Live workloads" sub="6 nodes · 128 pods · 4.8k rps" rows={[
            { eyebrow: 'PG PRIMARY', eyebrowColor: 'var(--emerald-4)', body: 'checkpoints · memory · audit' },
            { eyebrow: 'CONTROL PLANE', eyebrowColor: 'var(--blue-4)', body: 'api · supervisor · mcp · agents' },
            { eyebrow: 'EVENT BUS', eyebrowColor: 'var(--red-4)', body: 'kafka · redis · otel' },
          ]} />
          <Region x={490} color="var(--purple-3)" eyebrowColor="var(--purple-4)" eyebrow="WARM · eu-west-2" title="Read-only standby" sub="4 nodes · 84 pods · 2.1k rps" rows={[
            { eyebrow: 'PG REPLICA · 5s lag', eyebrowColor: 'var(--emerald-4)', body: 'read-only · ready to promote' },
            { eyebrow: 'CONTROL PLANE', eyebrowColor: 'var(--purple-4)', body: 'read traffic · failover ready' },
            { eyebrow: 'MIRROR BUS', eyebrowColor: 'var(--red-4)', body: 'kafka mirror-maker · 80ms p99' },
          ]} />
          <g transform="translate(900 60)">
            <rect width="320" height="260" rx="14" fill="oklch(0.20 0.013 250 / 0.5)" stroke="var(--amber-2)" strokeWidth="1.5" strokeDasharray="6 4" />
            <text x="20" y="26" fontFamily="var(--font-mono)" fontSize="10" fill="var(--amber-4)" letterSpacing="2">AIR-GAPPED · gov-zone</text>
            <text x="20" y="44" fontFamily="var(--font-sans)" fontSize="14" fill="var(--fg-primary)" fontWeight="500">Offline enclave</text>
            <text x="20" y="60" fontFamily="var(--font-mono)" fontSize="10" fill="var(--fg-muted)">2 nodes · 64 pods · Ollama · 0 egress</text>
            <RegionRow y={84} width={280} eyebrow="PG · LOCAL" eyebrowColor="var(--emerald-4)" body="independent state · WORM audit" />
            <RegionRow y={138} width={280} eyebrow="LOCAL LLM" eyebrowColor="var(--amber-4)" body="ollama · llama-3.1 · 8b + 70b" />
            <RegionRow y={192} width={280} eyebrow="UPDATE PATH" eyebrowColor="var(--fg-muted)" body="signed bundle · USB · 4.2GB" />
          </g>
          <g fill="none">
            <path d="M 360 200 C 420 200, 430 200, 490 200" stroke="var(--emerald-3)" strokeWidth="2" markerEnd="url(#arrow-r)" />
            <text x="380" y="190" fontFamily="var(--font-mono)" fontSize="10" fill="var(--emerald-4)">WAL · 5s lag</text>
          </g>
          <g fill="none">
            <line x1="770" y1="190" x2="900" y2="190" stroke="var(--fg-faint)" strokeDasharray="2 6" strokeWidth="2" />
            <g transform="translate(820 185)">
              <circle cx="0" cy="0" r="10" fill="var(--bg-canvas)" stroke="var(--fg-muted)" strokeWidth="1" />
              <text x="0" y="3" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="10" fill="var(--fg-muted)">✕</text>
            </g>
            <text x="800" y="172" fontFamily="var(--font-mono)" fontSize="10" fill="var(--fg-muted)">no network · USB bundle</text>
          </g>
        </svg>
      </div>
    </section>
  )
}

function Region({
  x, color, eyebrowColor, eyebrow, title, sub, rows,
}: {
  x: number; color: string; eyebrowColor: string; eyebrow: string; title: string; sub: string;
  rows: { eyebrow: string; eyebrowColor: string; body: string }[]
}) {
  return (
    <g transform={`translate(${x} 60)`}>
      <rect width="280" height="260" rx="14" fill="oklch(0.20 0.013 250 / 0.5)" stroke={color} strokeWidth="1.5" />
      <text x="20" y="26" fontFamily="var(--font-mono)" fontSize="10" fill={eyebrowColor} letterSpacing="2">{eyebrow}</text>
      <text x="20" y="44" fontFamily="var(--font-sans)" fontSize="14" fill="var(--fg-primary)" fontWeight="500">{title}</text>
      <text x="20" y="60" fontFamily="var(--font-mono)" fontSize="10" fill="var(--fg-muted)">{sub}</text>
      {rows.map((r, i) => (
        <RegionRow key={r.eyebrow} y={84 + i * 54} width={240} eyebrow={r.eyebrow} eyebrowColor={r.eyebrowColor} body={r.body} />
      ))}
    </g>
  )
}

function RegionRow({ y, width, eyebrow, eyebrowColor, body }: { y: number; width: number; eyebrow: string; eyebrowColor: string; body: string }) {
  return (
    <g transform={`translate(20 ${y})`}>
      <rect width={width} height="42" rx="6" fill="var(--bg-elevated)" stroke="var(--border-default)" />
      <text x="14" y="18" fontFamily="var(--font-mono)" fontSize="9" fill={eyebrowColor} letterSpacing="2">{eyebrow}</text>
      <text x="14" y="34" fontFamily="var(--font-mono)" fontSize="10" fill="var(--fg-primary)">{body}</text>
    </g>
  )
}

/* ── Endnote ─────────────────────────────────────────────────────────── */
function Endnote() {
  return (
    <section style={{
      marginTop: 72,
      padding: '28px 32px',
      border: '1px solid var(--border-default)',
      borderRadius: 'var(--r-4)',
      background:
        'radial-gradient(80% 70% at 100% 0%, oklch(0.72 0.18 240 / 0.10), transparent 60%),' +
        'radial-gradient(80% 70% at 0% 100%, oklch(0.70 0.20 295 / 0.10), transparent 60%),' +
        'var(--bg-canvas)',
    }}>
      <div className="section-eyebrow">Implementation reference</div>
      <h2 style={{ fontSize: 'var(--fs-30)', fontWeight: 500, letterSpacing: 'var(--tracking-tight)', margin: '6px 0 8px' }}>
        Frontend stack we ship the console on.
      </h2>
      <p style={{ color: 'var(--fg-secondary)', maxWidth: '70ch', fontSize: 'var(--fs-14)' }}>
        Use this as a starter for your own surface area. Boring choices, deliberately — the console needs to outlive
        a few framework cycles.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 24, marginTop: 28 }}>
        <ColumnNote eyebrow="UI runtime" body="React 19 · TypeScript · Vite · tokens.css. No UI kit." />
        <ColumnNote eyebrow="Realtime" body="SSE for run streams · TanStack Query for invalidation · component state for ephemeral UI." />
        <ColumnNote eyebrow="Graphs" body="Hand-rolled SVG with animateMotion for topology · CSS gradients for charts." />
        <ColumnNote eyebrow="Charts" body="Inline SVG for the dashboards · Recharts reserved for high-cardinality time-series." />
      </div>
    </section>
  )
}
