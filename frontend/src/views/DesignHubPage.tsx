import { useEffect } from 'react'
import { Link } from '@tanstack/react-router'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import '../styles/design-hub.css'

export function DesignHubPage() {
  useDocumentTitle('Design hub')
  useEffect(() => {
    document.body.classList.add('design-hub')
    return () => document.body.classList.remove('design-hub')
  }, [])

  return (
    <>
      <HubTopStrip />
      <div className="hub">
        <HubTop />
        <StatStrip />
        <Deliverables />
        <DesignMoves />
        <AiNativeFeatures />
        <Positioning />
        <Roadmap />
        <HubFooter />
      </div>
    </>
  )
}

function HubTopStrip() {
  return (
    <header className="hub-top-strip">
      <div className="inner">
        <Link to="/" className="brand">
          <span className="brand-mark" />
          <span className="brand-name">ForgeFlow</span>
        </Link>
        <nav>
          <a href="/design-hub" className="active">Index</a>
          <a href="/">Landing</a>
          <a href="/console">Console</a>
          <a href="/architecture">Architecture</a>
          <a href="/design-system">Design system</a>
        </nav>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-muted)' }}>
          design v1 · 2026.05.26
        </div>
      </div>
    </header>
  )
}

function HubTop() {
  return (
    <div className="hub-top">
      <div style={{ flex: 1, maxWidth: 880 }}>
        <div className="section-eyebrow">DESIGN EXPLORATION · ENTERPRISE AI ORCHESTRATION</div>
        <h1>An operating system <em>for production AI agents.</em></h1>
        <p className="lede">
          A complete design pass on ForgeFlow — landing surface, multi-screen operator console, system
          architecture reference, and the design system that holds it together. Built dark-first, mono-tabular,
          density-forward. For the on-call engineer at 2am, the platform PM in a security review, and the CTO
          sizing a renewal.
        </p>
      </div>
      <div className="right">
        <div><b>4 surfaces</b> · 1 design system</div>
        <div>~12 screens · 8 system diagrams</div>
        <div style={{ marginTop: 10 }}>
          <span className="status-bar">
            <span className="dot live" /> v1 · ready for review
          </span>
        </div>
      </div>
    </div>
  )
}

function StatStrip() {
  return (
    <div className="stat-strip">
      <div className="stat">
        <span className="k">Landing</span>
        <span className="v">9 sections</span>
        <span className="note">hero · arch · trust · cta</span>
      </div>
      <div className="stat">
        <span className="k">Console screens</span>
        <span className="v">13<em> · interactive</em></span>
        <span className="note">wired to FastAPI · live data</span>
      </div>
      <div className="stat">
        <span className="k">System diagrams</span>
        <span className="v">8<em> · animated</em></span>
        <span className="note">supervisor · A2A · MCP · K8s</span>
      </div>
      <div className="stat">
        <span className="k">Tokens</span>
        <span className="v">60+<em> · oklch</em></span>
        <span className="note">color · type · space · motion</span>
      </div>
    </div>
  )
}

type Deliverable = {
  href: string
  iframeSrc: string
  iframeTall?: boolean
  num: string
  title: string
  desc: string
  badges: string[]
}

const DELIVERABLES: Deliverable[] = [
  {
    href: '/',
    iframeSrc: '/',
    iframeTall: true,
    num: '01 · LANDING',
    title: 'Marketing surface · hero, architecture, platform, trust',
    desc: 'Hero with a live mini-console floating in the negative space. Sub-second observability preview, animated supervisor topology, deep enterprise & air-gap story. Built to convert SREs & security reviewers, not just buyers.',
    badges: ['9 sections', 'animated arch diagram', 'enterprise pitch'],
  },
  {
    href: '/console',
    iframeSrc: '/console/runs',
    num: '02 · CONSOLE',
    title: 'Operator console · 13 screens, navigable',
    desc: 'Lands on a live run — the killer screen — with Gantt, event stream, tool flame trace, approval card, memory recall, state diff, agent roster. Plus overview, approval queue, agent topology, cost, evals, audit, clusters, memory.',
    badges: ['13 screens', 'wired to FastAPI', 'live SSE feel'],
  },
  {
    href: '/architecture',
    iframeSrc: '/architecture',
    iframeTall: true,
    num: '03 · ARCHITECTURE',
    title: 'System reference · 8 visualizations',
    desc: 'Supervisor orchestration · A2A protocol · MCP topology · semantic memory graph · checkpointed state · event streaming · K8s pod placement · multi-region with air-gap. The artifact that gets pinned in the platform-team Notion.',
    badges: ['8 diagrams', 'animated packets', 'implementation specs'],
  },
  {
    href: '/design-system',
    iframeSrc: '/design-system',
    iframeTall: true,
    num: '04 · DESIGN SYSTEM',
    title: 'Tokens, type, components, motion',
    desc: 'Color (oklch), Geist + JetBrains Mono pairing, spacing scale, radii, elevation, agent avatars, workflow node primitives, motion principles. Every surface composes from these tokens — change once, propagate everywhere.',
    badges: ['60+ tokens', '5 component families', '3 motion curves'],
  },
]

function Deliverables() {
  return (
    <>
      <div className="sec-h">
        <span className="num">01</span>
        <h2>Deliverables</h2>
        <span className="sub" style={{ marginLeft: 'auto' }}>click any tile to open at full size</span>
      </div>
      <div className="hub-grid">
        {DELIVERABLES.slice(0, 2).map((d) => (
          <DeliverableCard key={d.href} d={d} />
        ))}
      </div>
      <div className="hub-grid" style={{ marginTop: 16 }}>
        {DELIVERABLES.slice(2).map((d) => (
          <DeliverableCard key={d.href} d={d} />
        ))}
      </div>
    </>
  )
}

function DeliverableCard({ d }: { d: Deliverable }) {
  return (
    <a className="deliverable" href={d.href}>
      <div className="preview">
        <div className="pad">
          <iframe src={d.iframeSrc} className={d.iframeTall ? 'tall' : ''} loading="lazy" title={d.title} />
        </div>
      </div>
      <div className="meta">
        <div className="label">
          <span>{d.num}</span>
          <span className="arrow">→</span>
        </div>
        <div className="title">{d.title}</div>
        <p className="desc">{d.desc}</p>
      </div>
      <div className="footer">
        {d.badges.map((b) => (
          <span key={b} className="badge">{b}</span>
        ))}
      </div>
    </a>
  )
}

const DESIGN_MOVES = [
  { num: '01 · DARK-FIRST, GRAPHITE NOT BLACK', title: "The console isn't pretending it's a notebook.", body: 'Deep graphite canvas at oklch(0.165) — never pure black, never high-chroma slate. Reads as an instrument panel; survives at 2am on the on-call shift without inducing eye strain.' },
  { num: '02 · TABULAR EVERYTHING', title: 'Numbers line up. Always.', body: 'Mono numerals on every cost, latency, score, token count. The eye tracks down a column without bouncing. Mono is also the visual whisper for "this came out of the system, not a human."' },
  { num: '03 · MOTION POINTS AT STATE', title: "Live indicators pulse. UI doesn't.", body: 'The only place motion is loud is the running workflow shimmer and SSE packets traversing the topology — exactly where the user needs to know something is alive. Hover states settle in 180ms.' },
  { num: '04 · AGENTS ARE FIRST-CLASS', title: 'Same avatar in 4 places.', body: "The researcher's purple RS mark is identical in the topology, the Gantt, the audit log, and the approval card. Operators recognize agents the same way SREs recognize services." },
  { num: '05 · DENSITY OVER DECORATION', title: 'Hairlines, not cards-in-cards.', body: '1px subtle borders, 12-16px spacing, no shadow stacks, no gradient fills on data surfaces. The information is the design; chrome stays out of the way.' },
  { num: '06 · AI-NATIVE UX HOOKS', title: 'Forge AI lives in the cost & eval views.', body: 'Root-cause assistant on the eval page; predictive cost forecasting with a "apply policy" CTA on the cost page; cmd-K offers "Ask Forge AI" and "Simulate cost change" — operator AI as an action, not a chatbot.' },
]

function DesignMoves() {
  return (
    <>
      <div className="sec-h">
        <span className="num">02</span>
        <h2>The design moves that matter</h2>
        <span className="sub" style={{ marginLeft: 'auto' }}>why this reads as enterprise AI infra, not generic SaaS</span>
      </div>
      <div className="wins">
        {DESIGN_MOVES.map((m) => (
          <div key={m.num} className="w">
            <div className="num">{m.num}</div>
            <h4>{m.title}</h4>
            <p>{m.body}</p>
          </div>
        ))}
      </div>
    </>
  )
}

type FeatureStatus = 'preview' | 'planned'
const AI_FEATURES: { status: FeatureStatus; title: string; body: string }[] = [
  { status: 'preview', title: 'Forge AI · root-cause assistant', body: 'A designed panel on the Evaluations page that groups failure classes and suggests a fix. The suggestion is illustrative today; automated analysis is not yet wired.' },
  { status: 'preview', title: 'Predictive cost forecasting', body: 'An end-of-month spend forecast with a budget bar and a model-swap suggestion. The forecast figures are illustrative; live spend is shown in the panels below it.' },
  { status: 'planned', title: 'Natural-language run search', body: 'Planned: a cmd-K palette to search runs, agents, audit, and memory, with "Ask Forge AI" and "Simulate cost change" as first-class actions. Search today links to the audit log.' },
  { status: 'planned', title: 'Replay & fork-at-checkpoint', body: 'Runs persist a Postgres checkpoint at every node. A console UI to replay or fork from a checkpoint is planned; the run "Replay" control is not yet wired.' },
  { status: 'planned', title: 'Workflow simulation mode', body: 'Dry-run a workflow against historical traffic before pushing the change. Outputs an A/B view of cost, judge score, and hallucination rate.' },
  { status: 'planned', title: 'Autonomous workflow healing', body: 'When a circuit breaker trips on a tool, the supervisor falls back to declared alternates — surfaced in audit, replayable in the console.' },
  { status: 'planned', title: 'AI governance center', body: 'Policy bundles, model allow-lists, PII detection on every tool input, and signed checkpoints — the AI version of "least privilege."' },
  { status: 'planned', title: 'Semantic observability', body: 'Search audit and traces by intent, not just by string. "Show me runs where the researcher hit a paywall" returns the right transcripts.' },
]

function statusPill(status: FeatureStatus) {
  return status === 'preview'
    ? <span className="new" style={{ background: 'oklch(0.30 0.06 75 / 0.45)', color: 'var(--amber-4)' }}>PREVIEW</span>
    : <span className="new" style={{ background: 'var(--bg-elevated)', color: 'var(--fg-muted)' }}>PLANNED</span>
}

function AiNativeFeatures() {
  return (
    <>
      <div className="sec-h">
        <span className="num">03</span>
        <h2>The AI-native moves in the design</h2>
        <span className="sub" style={{ marginLeft: 'auto' }}>preview = designed &amp; visible · planned = not yet built</span>
      </div>
      <div className="features-tight">
        {AI_FEATURES.map((f) => (
          <div key={f.title} className="f">
            <h5>
              {statusPill(f.status)}
              {f.title}
            </h5>
            <p>{f.body}</p>
          </div>
        ))}
      </div>
    </>
  )
}

type Mark = 'check' | 'partial' | 'miss'
type PosRow = { capability: string; cells: { mark: Mark; label: string }[] }

const POSITIONING: PosRow[] = [
  { capability: 'Multi-agent orchestration', cells: [
    { mark: 'check', label: '● production · supervised' },
    { mark: 'partial', label: '● demo / framework' },
    { mark: 'partial', label: '● studio · not prod' },
    { mark: 'miss', label: '● workflow only · no agent loop' },
    { mark: 'miss', label: '●' },
  ]},
  { capability: 'Human-in-the-loop', cells: [
    { mark: 'check', label: '● typed approval · interrupt_before' },
    { mark: 'partial', label: '● bring your own' },
    { mark: 'partial', label: '●' },
    { mark: 'check', label: '●' },
    { mark: 'check', label: '● UI-builder' },
  ]},
  { capability: 'LLM evaluation', cells: [
    { mark: 'check', label: '● judge + datasets · built-in' },
    { mark: 'check', label: '●' },
    { mark: 'miss', label: '●' },
    { mark: 'miss', label: '●' },
    { mark: 'miss', label: '●' },
  ]},
  { capability: 'Cost & budget guard', cells: [
    { mark: 'check', label: '● per-agent · forecasting · halt' },
    { mark: 'partial', label: '● cost only' },
    { mark: 'miss', label: '●' },
    { mark: 'miss', label: '●' },
    { mark: 'partial', label: '● infra only' },
  ]},
  { capability: 'Air-gapped deploy', cells: [
    { mark: 'check', label: '● Ollama · signed bundle' },
    { mark: 'miss', label: '● SaaS-first' },
    { mark: 'partial', label: '● self-host' },
    { mark: 'check', label: '●' },
    { mark: 'miss', label: '●' },
  ]},
  { capability: 'Enterprise governance', cells: [
    { mark: 'check', label: '● RBAC · audit · OIDC · MFA' },
    { mark: 'partial', label: '● cloud RBAC' },
    { mark: 'miss', label: '●' },
    { mark: 'check', label: '●' },
    { mark: 'check', label: '●' },
  ]},
  { capability: 'Production observability UI', cells: [
    { mark: 'check', label: '● live console + cmd-K' },
    { mark: 'partial', label: '● trace viewer' },
    { mark: 'miss', label: '●' },
    { mark: 'partial', label: '● workflow UI' },
    { mark: 'check', label: '● not AI-aware' },
  ]},
]

function Positioning() {
  return (
    <>
      <div className="sec-h">
        <span className="num">04</span>
        <h2>Competitive position</h2>
        <span className="sub" style={{ marginLeft: 'auto' }}>how ForgeFlow lines up vs adjacent tools</span>
      </div>
      <div className="positioning">
        <div className="prow">
          <div className="pcell">Capability</div>
          <div className="pcell">ForgeFlow</div>
          <div className="pcell">LangSmith / CrewAI</div>
          <div className="pcell">AutoGen Studio</div>
          <div className="pcell">Temporal · Airflow</div>
          <div className="pcell">Datadog · Retool</div>
        </div>
        {POSITIONING.map((row) => (
          <div className="prow" key={row.capability}>
            <div className="pcell">{row.capability}</div>
            {row.cells.map((c, i) => (
              <div className="pcell" key={i}>
                <span className={c.mark}>{c.label}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </>
  )
}

const ROADMAP_COLS = [
  { cls: '', tag: 'SHIPPING NOW', when: 'v3.4 · 2026 Q2', items: [
    'Live console (current build) — runs, agents, approvals',
    'Air-gapped deploy against a local Ollama daemon',
    'Postgres checkpointing for resumable runs',
    'RBAC roles + scoped API tokens + audit log',
  ]},
  { cls: 'q2', tag: 'NEXT', when: 'v3.5 · 2026 Q3', items: [
    'Workflow simulation mode (replay against historical traffic)',
    'Drag-and-drop graph editor (React Flow)',
    'Marketplace v2 — signed community templates',
    'Forge AI · failure root-cause assistant GA',
  ]},
  { cls: 'q3', tag: 'DESIGNED', when: 'v4.0 · 2026 Q4', items: [
    'Natural-language workflow creation',
    'Autonomous workflow healing (auto-fallback tools)',
    'Self-improving orchestration (online supervisor)',
    'SDK · TypeScript + Go parity with Python',
  ]},
  { cls: 'q4', tag: 'EXPLORING', when: 'v4.1+ · 2027 H1', items: [
    'Agent collaboration visual replay (time-scrubbable)',
    'Semantic observability — search by intent',
    'AI governance center · model + tool allow-lists',
    'Native voice + multimodal agent inputs',
  ]},
]

function Roadmap() {
  return (
    <>
      <div className="sec-h">
        <span className="num">05</span>
        <h2>What ships next</h2>
        <span className="sub" style={{ marginLeft: 'auto' }}>design + product roadmap · next 4 quarters</span>
      </div>
      <div className="roadmap">
        {ROADMAP_COLS.map((c) => (
          <div key={c.tag} className={`col ${c.cls}`}>
            <div className="q">{c.tag}</div>
            <div className="when">{c.when}</div>
            <ul>
              {c.items.map((it) => <li key={it}>{it}</li>)}
            </ul>
          </div>
        ))}
      </div>
    </>
  )
}

function HubFooter() {
  return (
    <div
      style={{
        marginTop: 80,
        paddingTop: 32,
        borderTop: '1px solid var(--border-subtle)',
        display: 'flex',
        justifyContent: 'space-between',
        fontFamily: 'var(--font-mono)',
        fontSize: 11,
        color: 'var(--fg-muted)',
      }}
    >
      <span>ForgeFlow · design exploration v1 · 2026.05.26</span>
      <span>4 deliverables · landing · console · architecture · system</span>
    </div>
  )
}
