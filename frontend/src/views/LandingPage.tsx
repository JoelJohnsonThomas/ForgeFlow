import { useEffect } from 'react'
import { Link } from '@tanstack/react-router'
import '../styles/landing.css'

const CONSOLE_HREF = '/console' as const

export function LandingPage() {
  // Toggle a body class so landing-only CSS scopes cleanly (no overflow-x clip on dashboard pages).
  useEffect(() => {
    document.body.classList.add('landing')
    return () => document.body.classList.remove('landing')
  }, [])

  return (
    <>
      <LandingNav />
      <Hero />
      <LogoStrip />
      <Architecture />
      <Platform />
      <ObservabilityPreview />
      <Developers />
      <Enterprise />
      <CallToAction />
      <Footer />
    </>
  )
}

function LandingNav() {
  return (
    <nav className="top">
      <div className="wrap inner">
        <div className="row gap-6">
          <Link to="/" className="brand">
            <span className="brand-mark" />
            <span className="brand-name">ForgeFlow</span>
          </Link>
          <ul>
            <li><a href="#platform">Platform</a></li>
            <li><a href="#architecture">Architecture</a></li>
            <li><a href="#observability">Observability</a></li>
            <li><a href="#enterprise">Enterprise</a></li>
            <li><a href="#developers">Developers</a></li>
            <li><a href="#docs">Docs</a></li>
          </ul>
        </div>
        <div className="right">
          <span className="nav-pill">
            <span className="tag">v3.4</span> Checkpointed runs are now resumable across regions
            <span className="arrow">→</span>
          </span>
          <a href={CONSOLE_HREF} className="btn ghost">
            Sign in
          </a>
          <a href={CONSOLE_HREF} className="btn primary">
            Open console
          </a>
        </div>
      </div>
    </nav>
  )
}

function Hero() {
  return (
    <section className="hero">
      <div className="spotlight" />
      <div className="wrap" style={{ position: 'relative', zIndex: 1 }}>
        <span className="release-pill">
          <span className="tag">NEW</span>
          Air-gapped clusters with Ollama + Anthropic
          <span className="arrow">→</span>
        </span>
        <h1>
          The operating system for <em>production AI&nbsp;agents.</em>
        </h1>
        <p className="lede">
          ForgeFlow orchestrates teams of specialized agents across your business — with human-in-the-loop
          approvals, semantic memory, sub-second observability, and the kind of audit trail your security team
          actually signs off on.
        </p>
        <div className="hero-cta">
          <a href={CONSOLE_HREF} className="btn primary">
            Open the console
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M3 7h8m0 0L7.5 3.5M11 7l-3.5 3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </a>
          <a href="#architecture" className="btn">
            <span className="mono" style={{ color: 'var(--fg-muted)', fontSize: 11 }}>$</span>
            docker compose up forgeflow
          </a>
        </div>

        <div className="hero-meta">
          <div>
            <div className="k">Avg p50 routing</div>
            <div className="v">142<span className="u">ms</span></div>
          </div>
          <div>
            <div className="k">Workflows orchestrated</div>
            <div className="v">14.2<span className="u">M+</span></div>
          </div>
          <div>
            <div className="k">Active deployments</div>
            <div className="v">1,847</div>
          </div>
          <div>
            <div className="k">Uptime · last 90d</div>
            <div className="v">99.992<span className="u">%</span></div>
          </div>
        </div>
      </div>

      <HeroStage />
    </section>
  )
}

function HeroStage() {
  return (
    <div className="hero-stage" aria-hidden="true">
      <div className="glow" />
      <div className="frame">
        <div className="miniapp">
          <div className="chrome">
            <div className="traffic">
              <span /><span /><span />
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-muted)', marginLeft: 8 }}>
              forgeflow.app/runs/wf_8K42n
            </div>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
              <span className="status-bar">
                <span className="dot live" /> LIVE · supervisor
              </span>
            </div>
          </div>
          <aside className="side">
            <div className="label">Workspaces</div>
            <ul>
              <li className="active"><span className="sq" /> Sales Ops</li>
              <li><span className="sq" /> Support</li>
              <li><span className="sq" /> Finance Recon</li>
            </ul>
            <div className="label">Run</div>
            <ul>
              <li className="active"><span className="sq" /> Live timeline</li>
              <li><span className="sq" /> Agent map</li>
              <li><span className="sq" /> Cost</li>
              <li><span className="sq" /> Memory</li>
            </ul>
          </aside>
          <main className="main">
            <div className="ma-bar">
              <div>
                <div style={{ color: 'var(--fg-primary)', fontWeight: 500 }}>Stripe — sales_ops</div>
                <div className="run-id">wf_8K42n · human_approval pending</div>
              </div>
              <span className="badge amber">● Awaiting approval</span>
            </div>
            <div className="ma-stats">
              <div className="s"><div className="v">$0.184</div><div className="k">Cost</div></div>
              <div className="s"><div className="v">12.4s</div><div className="k">Wall</div></div>
              <div className="s"><div className="v">8</div><div className="k">Hops</div></div>
              <div className="s"><div className="v">9.1<span style={{ color: 'var(--fg-muted)' }}>/10</span></div><div className="k">Eval</div></div>
            </div>
            <div className="tl-box">
              <TlRule color="var(--blue-4)" who="supervisor" left="0" width="6%" />
              <TlRule color="var(--purple-4)" who="researcher" left="5%" width="24%" tone="purple" />
              <TlRule color="var(--blue-4)" who="supervisor" left="28%" width="4%" />
              <TlRule color="var(--emerald-4)" who="analyzer" left="32%" width="18%" tone="emerald" />
              <TlRule color="var(--blue-4)" who="supervisor" left="49%" width="4%" />
              <TlRule color="var(--amber-4)" who="executor" left="52%" width="28%" tone="amber" />
              <TlRule color="var(--fg-muted)" who="human_loop" left="79%" width="14%" tone="running" />
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}

function TlRule({
  color, who, left, width, tone,
}: { color: string; who: string; left: string; width: string; tone?: 'purple' | 'emerald' | 'amber' | 'running' }) {
  return (
    <div className="tl-rule">
      <div className="who">
        <span className="dotc" style={{ background: color }} />
        {who}
      </div>
      <div className="bar-wrap">
        <div className={`bar${tone ? ` ${tone}` : ''}`} style={{ left, width }} />
      </div>
    </div>
  )
}

function LogoStrip() {
  return (
    <div className="wrap">
      <div className="logos">
        <span className="lbl">Trusted by infrastructure teams at</span>
        <div className="marks">
          {['NORTHWIND', 'Helios.ai', 'meridian', 'ATLAS', 'Quanta', 'CADENCE'].map((m) => (
            <span key={m} className="mark">
              <span className="glyph" /> {m}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

function Architecture() {
  return (
    <section id="architecture">
      <div className="wrap">
        <div className="section-eyebrow">Architecture · Hub-and-spoke supervisor</div>
        <h2>One supervisor. A roster of specialists. Every step replayable.</h2>
        <p className="sub">
          A deterministic supervisor routes work to specialist agents via structured outputs. Workers
          communicate over A2A, discover tools through MCP, and persist every node to Postgres so any worker
          can resume any run.
        </p>

        <div className="arch" style={{ marginTop: 48 }}>
          <ArchitectureSvg />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 24, marginTop: 36 }}>
          <ArchCallout num="01 · Routing" body={<>Supervisor emits a structured <span className="mono" style={{ color: 'var(--blue-4)' }}>RoutingDecision</span> at every step — deterministic, replayable, auditable.</>} />
          <ArchCallout num="02 · Tools" body="Workers discover tools through MCP. Swap providers — Tavily, Salesforce, internal — without touching agent code." />
          <ArchCallout num="03 · Communication" body="A2A protocol — JSON-RPC 2.0 + capability discovery. Workers find each other and collaborate without a fan-out hop through the supervisor." />
          <ArchCallout num="04 · Persistence" body="Every node persists to Postgres before exit. Resume any run from any worker — across pods, regions, restarts." />
        </div>
      </div>
    </section>
  )
}

function ArchCallout({ num, body }: { num: string; body: React.ReactNode }) {
  return (
    <div>
      <div className="section-eyebrow">{num}</div>
      <p style={{ marginTop: 8, color: 'var(--fg-secondary)', fontSize: 'var(--fs-14)' }}>{body}</p>
    </div>
  )
}

function ArchitectureSvg() {
  return (
    <svg viewBox="0 0 1200 540" width="100%" height={540} style={{ display: 'block', position: 'relative', zIndex: 1 }}>
      <defs>
        <linearGradient id="edge-blue" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="oklch(0.72 0.18 240)" stopOpacity="0.05" />
          <stop offset="50%" stopColor="oklch(0.72 0.18 240)" stopOpacity="0.55" />
          <stop offset="100%" stopColor="oklch(0.72 0.18 240)" stopOpacity="0.05" />
        </linearGradient>
        <linearGradient id="edge-purple" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="oklch(0.70 0.20 295)" stopOpacity="0.05" />
          <stop offset="50%" stopColor="oklch(0.70 0.20 295)" stopOpacity="0.55" />
          <stop offset="100%" stopColor="oklch(0.70 0.20 295)" stopOpacity="0.05" />
        </linearGradient>
        <radialGradient id="node-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="oklch(0.72 0.18 240)" stopOpacity="0.5" />
          <stop offset="100%" stopColor="oklch(0.72 0.18 240)" stopOpacity="0" />
        </radialGradient>
        <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="1" fill="oklch(0.30 0.012 250 / 0.5)" />
        </pattern>
      </defs>

      <rect width="1200" height="540" fill="url(#dots)" />

      <g opacity="0.6">
        <line x1="0" y1="60" x2="1200" y2="60" stroke="var(--border-subtle)" strokeDasharray="2 6" />
        <line x1="0" y1="180" x2="1200" y2="180" stroke="var(--border-subtle)" strokeDasharray="2 6" />
        <line x1="0" y1="320" x2="1200" y2="320" stroke="var(--border-subtle)" strokeDasharray="2 6" />
        <line x1="0" y1="460" x2="1200" y2="460" stroke="var(--border-subtle)" strokeDasharray="2 6" />
      </g>
      <g fontFamily="var(--font-mono)" fontSize="10" fill="var(--fg-muted)" letterSpacing="2">
        <text x="20" y="56">CLIENT</text>
        <text x="20" y="176">CONTROL PLANE</text>
        <text x="20" y="316">AGENTS</text>
        <text x="20" y="456">DATA · MEMORY</text>
      </g>

      <g fill="none" strokeWidth="1.4">
        <path d="M 200 40 C 200 100, 280 140, 280 180" stroke="url(#edge-blue)" />
        <path d="M 320 220 C 460 220, 540 260, 600 280" stroke="url(#edge-blue)" />
        <path d="M 640 280 C 700 320, 820 320, 870 320" stroke="url(#edge-purple)" />
        <path d="M 640 290 C 720 360, 820 380, 870 390" stroke="url(#edge-purple)" />
        <path d="M 640 300 C 720 420, 830 450, 870 460" stroke="url(#edge-purple)" />
        <path d="M 990 320 C 1050 320, 1080 270, 1100 230" stroke="oklch(0.42 0.13 240 / 0.5)" />
        <path d="M 990 390 C 1050 390, 1080 380, 1100 360" stroke="oklch(0.42 0.13 240 / 0.5)" />
        <path d="M 920 430 C 920 470, 700 470, 540 470" stroke="oklch(0.40 0.11 160 / 0.5)" />
        <path d="M 620 320 C 620 400, 520 440, 500 460" stroke="oklch(0.40 0.11 160 / 0.5)" />
        <path d="M 930 350 C 980 360, 980 380, 930 400" stroke="oklch(0.50 0.12 75 / 0.55)" strokeDasharray="3 3" />
      </g>

      <circle r="3" fill="oklch(0.86 0.10 240)">
        <animateMotion dur="3s" repeatCount="indefinite" path="M 200 40 C 200 100, 280 140, 280 180" />
      </circle>
      <circle r="3" fill="oklch(0.86 0.10 240)">
        <animateMotion dur="3s" repeatCount="indefinite" begin="0.6s" path="M 320 220 C 460 220, 540 260, 600 280" />
      </circle>
      <circle r="3" fill="oklch(0.84 0.14 295)">
        <animateMotion dur="2.4s" repeatCount="indefinite" begin="1.2s" path="M 640 290 C 720 360, 820 380, 870 390" />
      </circle>
      <circle r="3" fill="oklch(0.84 0.14 295)">
        <animateMotion dur="2.6s" repeatCount="indefinite" begin="1.6s" path="M 640 280 C 700 320, 820 320, 870 320" />
      </circle>

      <g transform="translate(140 20)">
        <rect width="120" height="40" rx="8" fill="var(--bg-elevated)" stroke="var(--border-default)" />
        <text x="14" y="17" fontFamily="var(--font-mono)" fontSize="10" fill="var(--fg-muted)" letterSpacing="1">CLIENT</text>
        <text x="14" y="32" fontFamily="var(--font-sans)" fontSize="12" fill="var(--fg-primary)">Console · SDK · API</text>
      </g>

      <g transform="translate(220 160)">
        <rect width="120" height="60" rx="8" fill="var(--bg-elevated)" stroke="var(--border-default)" />
        <circle cx="14" cy="14" r="4" fill="var(--blue-4)" />
        <text x="24" y="18" fontFamily="var(--font-sans)" fontSize="12" fill="var(--fg-primary)" fontWeight="500">FastAPI</text>
        <text x="14" y="36" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">REST + SSE</text>
        <text x="14" y="50" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">:8000</text>
      </g>

      <g transform="translate(540 240)">
        <ellipse cx="50" cy="50" rx="120" ry="120" fill="url(#node-glow)" />
        <rect width="100" height="80" rx="14" fill="var(--bg-elevated)" stroke="var(--blue-3)" strokeWidth="1.5" />
        <circle cx="16" cy="18" r="5" fill="var(--blue-4)" />
        <text x="28" y="22" fontFamily="var(--font-sans)" fontSize="13" fill="var(--fg-primary)" fontWeight="600">Supervisor</text>
        <text x="16" y="42" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">LangGraph</text>
        <text x="16" y="56" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">structured-out</text>
        <text x="16" y="70" fontFamily="var(--font-mono)" fontSize="9" fill="var(--blue-4)">routing · gpt-4o</text>
      </g>

      <g transform="translate(860 290)">
        <rect width="140" height="60" rx="10" fill="var(--bg-elevated)" stroke="var(--purple-3)" strokeWidth="1.2" />
        <circle cx="14" cy="14" r="4" fill="var(--purple-4)" />
        <text x="26" y="18" fontFamily="var(--font-sans)" fontSize="12" fill="var(--fg-primary)" fontWeight="500">Researcher</text>
        <text x="14" y="36" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">web_search · scrape</text>
        <text x="14" y="50" fontFamily="var(--font-mono)" fontSize="9" fill="var(--purple-4)">A2A · MCP</text>
      </g>
      <g transform="translate(860 360)">
        <rect width="140" height="60" rx="10" fill="var(--bg-elevated)" stroke="var(--emerald-3)" strokeWidth="1.2" />
        <circle cx="14" cy="14" r="4" fill="var(--emerald-4)" />
        <text x="26" y="18" fontFamily="var(--font-sans)" fontSize="12" fill="var(--fg-primary)" fontWeight="500">Analyzer</text>
        <text x="14" y="36" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">score · ICP · risk</text>
        <text x="14" y="50" fontFamily="var(--font-mono)" fontSize="9" fill="var(--emerald-4)">structured 0–10</text>
      </g>
      <g transform="translate(860 430)">
        <rect width="140" height="60" rx="10" fill="var(--bg-elevated)" stroke="var(--amber-2)" strokeWidth="1.2" />
        <circle cx="14" cy="14" r="4" fill="var(--amber-4)" />
        <text x="26" y="18" fontFamily="var(--font-sans)" fontSize="12" fill="var(--fg-primary)" fontWeight="500">Executor</text>
        <text x="14" y="36" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">CRM · email · write</text>
        <text x="14" y="50" fontFamily="var(--font-mono)" fontSize="9" fill="var(--amber-4)">human-approved</text>
      </g>

      <g transform="translate(1080 200)">
        <rect width="100" height="50" rx="8" fill="var(--bg-elevated)" stroke="var(--border-default)" />
        <text x="14" y="18" fontFamily="var(--font-mono)" fontSize="9" fill="var(--blue-4)" letterSpacing="2">MCP</text>
        <text x="14" y="34" fontFamily="var(--font-sans)" fontSize="11" fill="var(--fg-primary)">Tool server</text>
        <text x="14" y="46" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">:8001 · 14 tools</text>
      </g>
      <g transform="translate(1080 330)">
        <rect width="100" height="50" rx="8" fill="var(--bg-elevated)" stroke="var(--border-default)" />
        <text x="14" y="18" fontFamily="var(--font-mono)" fontSize="9" fill="var(--blue-4)" letterSpacing="2">A2A</text>
        <text x="14" y="34" fontFamily="var(--font-sans)" fontSize="11" fill="var(--fg-primary)">Registry</text>
        <text x="14" y="46" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">JSON-RPC 2.0</text>
      </g>

      <g transform="translate(420 440)">
        <rect width="160" height="60" rx="10" fill="var(--bg-elevated)" stroke="var(--emerald-2)" strokeWidth="1.2" />
        <text x="14" y="18" fontFamily="var(--font-mono)" fontSize="9" fill="var(--emerald-4)" letterSpacing="2">CHECKPOINTER</text>
        <text x="14" y="36" fontFamily="var(--font-sans)" fontSize="12" fill="var(--fg-primary)" fontWeight="500">Postgres 16 + pgvector</text>
        <text x="14" y="51" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">state · memory · audit · ivfflat</text>
      </g>

      <g transform="translate(700 450)">
        <rect width="120" height="50" rx="8" fill="var(--bg-elevated)" stroke="var(--border-default)" />
        <text x="14" y="18" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)" letterSpacing="2">EVENTS</text>
        <text x="14" y="34" fontFamily="var(--font-sans)" fontSize="11" fill="var(--fg-primary)">Kafka + Redis</text>
        <text x="14" y="46" fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)">stream · audit</text>
      </g>
    </svg>
  )
}

function Platform() {
  return (
    <section id="platform">
      <div className="wrap">
        <div className="section-eyebrow">Platform</div>
        <h2>Everything an AI platform team has to build, already built.</h2>
        <p className="sub">
          Routing, memory, tools, evaluation, governance, observability. Production patterns out of the box —
          not a notebook demo.
        </p>

        <div className="features">
          <Feature
            color="var(--blue-4)"
            icon={
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <circle cx="7" cy="7" r="3" stroke="currentColor" strokeWidth="1.4" />
                <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.4" strokeDasharray="2 2" />
              </svg>
            }
            title="Multi-agent orchestration"
            body="Supervisor + worker pattern with deterministic, structured routing. Spin up dozens of specialist agents and ship them like normal services."
          />
          <Feature
            color="var(--purple-4)"
            icon={
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M3 7h8M7 3v8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
              </svg>
            }
            title="Human-in-the-loop approvals"
            body="Interrupt before any node. Approvers see the proposed action, full context, and the cost — then approve, reject, or send back with notes."
          />
          <Feature
            color="var(--emerald-4)"
            icon={
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <rect x="2" y="2" width="4" height="4" rx="1" stroke="currentColor" strokeWidth="1.4" />
                <rect x="8" y="2" width="4" height="4" rx="1" stroke="currentColor" strokeWidth="1.4" />
                <rect x="2" y="8" width="4" height="4" rx="1" stroke="currentColor" strokeWidth="1.4" />
                <rect x="8" y="8" width="4" height="4" rx="1" stroke="currentColor" strokeWidth="1.4" />
              </svg>
            }
            title="Semantic memory"
            body="Postgres + pgvector, namespace-scoped. Recall any prior decision with cosine search — co-located with transactional state."
          />
          <Feature
            color="var(--amber-4)"
            icon={
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M2 11l3-3 2 2 5-5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M9 3h3v3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
              </svg>
            }
            title="Cost & eval pipelines"
            body="Per-token, per-agent, per-tenant cost. LLM-as-judge scores faithfulness, relevance, hallucination — automatic on every run."
          />
          <Feature
            color="var(--blue-4)"
            icon={
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M1 7h2l2-4 4 8 2-4h2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            }
            title="Sub-second observability"
            body="Stream every node, every tool call, every token. Trace timeline, agent map, semantic event search, OTel export."
          />
          <Feature
            color="var(--red-4)"
            icon={
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <rect x="3" y="6" width="8" height="6" rx="1" stroke="currentColor" strokeWidth="1.4" />
                <path d="M5 6V4a2 2 0 0 1 4 0v2" stroke="currentColor" strokeWidth="1.4" />
              </svg>
            }
            title="Enterprise RBAC + audit"
            body="Roles, policies, immutable audit log. Air-gap deploy with Ollama. SAML, SCIM, OPA — built in, not bolted on."
          />
        </div>
      </div>
    </section>
  )
}

function Feature({ color, icon, title, body }: { color: string; icon: React.ReactNode; title: string; body: string }) {
  return (
    <div className="feature">
      <div className="icon" style={{ color }}>{icon}</div>
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  )
}

function ObservabilityPreview() {
  return (
    <section id="observability">
      <div className="wrap">
        <div className="section-eyebrow">Observability</div>
        <h2>Operate AI like the rest of your stack.</h2>
        <p className="sub">
          Live agent timelines, cost burn, failure root-cause AI, evaluation scores — the same console an SRE
          would expect, tuned for non-deterministic systems.
        </p>

        <div className="preview-frame">
          <div className="preview-chrome">
            <div className="traffic"><span /><span /><span /></div>
            <span className="mono" style={{ color: 'var(--fg-muted)', fontSize: 11, marginLeft: 12 }}>
              app.forgeflow.io · console
            </span>
            <span className="status-bar" style={{ marginLeft: 'auto' }}>
              <span className="dot live" /> 12 runs streaming
            </span>
            <a href={CONSOLE_HREF} className="btn sm" style={{ marginLeft: 12 }}>
              Open live console →
            </a>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', minHeight: 520 }}>
            <aside style={{ borderRight: '1px solid var(--border-subtle)', padding: '18px 14px', background: 'var(--bg-page)' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--fg-muted)', letterSpacing: '.12em', textTransform: 'uppercase', margin: '6px 0 10px' }}>
                WORKSPACE
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px', background: 'var(--bg-elevated)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                <div style={{ width: 18, height: 18, borderRadius: 4, background: 'linear-gradient(135deg, var(--blue-4), var(--purple-4))' }} />
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: 12.5, fontWeight: 500 }}>Acme · Sales Ops</span>
                  <span className="mono" style={{ fontSize: 10, color: 'var(--fg-muted)' }}>prod-us-east-1</span>
                </div>
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--fg-muted)', letterSpacing: '.12em', textTransform: 'uppercase', margin: '24px 0 8px' }}>
                RUN VIEW
              </div>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 2, fontSize: 12.5 }}>
                <li style={{ padding: '5px 8px', borderRadius: 5, background: 'var(--bg-elevated)', color: 'var(--fg-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--blue-4)' }} /> Live timeline
                </li>
                <li style={{ padding: '5px 8px', color: 'var(--fg-secondary)' }}>Agent communication map</li>
                <li style={{ padding: '5px 8px', color: 'var(--fg-secondary)' }}>Tool invocation trace</li>
                <li style={{ padding: '5px 8px', color: 'var(--fg-secondary)' }}>Memory recall</li>
                <li style={{ padding: '5px 8px', color: 'var(--fg-secondary)' }}>Cost breakdown</li>
                <li style={{ padding: '5px 8px', color: 'var(--fg-secondary)' }}>Eval scores</li>
              </ul>
            </aside>
            <main style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: 17, fontWeight: 500, letterSpacing: 'var(--tracking-tight)', display: 'flex', alignItems: 'center', gap: 10 }}>
                    Stripe Series E expansion
                    <span className="badge amber">● Awaiting approval</span>
                  </div>
                  <div className="mono" style={{ fontSize: 11.5, color: 'var(--fg-muted)', marginTop: 4 }}>
                    wf_8K42n · sales_ops · started 12.4s ago
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn sm">Replay</button>
                  <button className="btn sm primary">Approve</button>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 1, background: 'var(--border-subtle)', border: '1px solid var(--border-subtle)', borderRadius: 8, overflow: 'hidden' }}>
                <PreviewKpi label="Cost" value="$0.184" />
                <PreviewKpi label="Tokens" value="14,892" />
                <PreviewKpi label="Wall time" value="12.4s" />
                <PreviewKpi label="Hops" value="8" />
                <PreviewKpi label="Eval (judge)" value={<>9.1<span style={{ color: 'var(--fg-muted)', fontSize: 13 }}>/10</span></>} valueColor="var(--emerald-4)" />
              </div>

              <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '18px 20px', background: 'var(--bg-page)', flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 14 }}>
                  <div style={{ fontSize: 13, color: 'var(--fg-secondary)', fontWeight: 500 }}>Execution timeline</div>
                  <div className="mono" style={{ fontSize: 10, color: 'var(--fg-muted)' }}>Gantt · 12.4s window</div>
                </div>
                <div style={{ display: 'grid', gridTemplateRows: 'repeat(7, 24px)', gap: 6 }}>
                  <PreviewGantt who="supervisor" left="0" width="5%" />
                  <PreviewGantt who="researcher" left="5%" width="28%" tone="purple" />
                  <PreviewGantt who="supervisor" left="33%" width="4%" />
                  <PreviewGantt who="analyzer" left="37%" width="18%" tone="emerald" />
                  <PreviewGantt who="supervisor" left="55%" width="4%" />
                  <PreviewGantt who="executor" left="59%" width="23%" tone="amber" />
                  <PreviewGantt who="human_loop" left="82%" width="14%" tone="running" />
                </div>
              </div>
            </main>
          </div>
        </div>
      </div>
    </section>
  )
}

function PreviewKpi({ label, value, valueColor }: { label: string; value: React.ReactNode; valueColor?: string }) {
  return (
    <div style={{ background: 'var(--bg-canvas)', padding: '12px 14px' }}>
      <div style={{ fontSize: 10, color: 'var(--fg-muted)', fontFamily: 'var(--font-mono)', letterSpacing: '.1em', textTransform: 'uppercase' }}>{label}</div>
      <div className="mono" style={{ fontSize: 20, color: valueColor ?? 'var(--fg-primary)', marginTop: 4 }}>{value}</div>
    </div>
  )
}

function PreviewGantt({ who, left, width, tone }: { who: string; left: string; width: string; tone?: 'purple' | 'emerald' | 'amber' | 'running' }) {
  const bgMap: Record<string, string> = {
    purple: 'linear-gradient(90deg, var(--purple-3), var(--purple-4))',
    emerald: 'linear-gradient(90deg, var(--emerald-3), var(--emerald-4))',
    amber: 'linear-gradient(90deg, var(--amber-2), var(--amber-4))',
    running: 'linear-gradient(90deg, var(--blue-3), var(--blue-4))',
  }
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '130px 1fr', gap: 12, alignItems: 'center' }}>
      <div className="mono" style={{ fontSize: 11, color: 'var(--fg-secondary)' }}>▷ {who}</div>
      <div style={{ position: 'relative', height: 14, background: 'var(--bg-inset)', borderRadius: 4 }}>
        <div
          style={{
            position: 'absolute',
            left,
            width,
            top: 0,
            bottom: 0,
            background: tone ? bgMap[tone] : 'linear-gradient(90deg, var(--blue-3), var(--blue-4))',
            borderRadius: 4,
            animation: tone === 'running' ? 'stream 1.6s var(--ease-out) infinite alternate' : undefined,
          }}
        />
      </div>
    </div>
  )
}

function Developers() {
  const code = `# pip install forgeflow
from forgeflow import Workflow, Supervisor, Agent
from forgeflow.tools import mcp

researcher = Agent("researcher", tools=mcp("http://mcp:8001"))
analyzer   = Agent("analyzer",   structured=LeadScore)
executor   = Agent("executor",   approval=True)

wf = Workflow(
    supervisor=Supervisor(model="gpt-4o"),
    workers=[researcher, analyzer, executor],
    checkpoint="postgres://forgeflow",
)

async for event in wf.stream({"company": "Stripe"}):
    print(event.agent, event.cost, event.tokens)
#  supervisor   $0.0008   72
#  researcher   $0.0241   2,431
#  analyzer     $0.0094   941
#  ...`

  return (
    <section id="developers">
      <div className="wrap">
        <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 80, alignItems: 'center' }}>
          <div>
            <div className="section-eyebrow">Developers</div>
            <h2>Five lines from import to a streaming production run.</h2>
            <p className="sub">
              A typed Python SDK, a graph builder that's mostly declarative, and an OpenAPI surface your
              frontend team can actually generate clients against.
            </p>
            <div className="hero-cta" style={{ marginTop: 28 }}>
              <a href="#" className="btn primary">Read the docs →</a>
              <a href="#" className="btn">SDK reference</a>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, marginTop: 36 }}>
              <DxFeature title="Local-first dev loop" body="Ollama + Postgres in compose. No keys to commit." />
              <DxFeature title="Replay any run" body="Fork from any checkpoint with one CLI command." />
              <DxFeature title="Typed everything" body="Pydantic state + structured outputs end to end." />
              <DxFeature title="OTel native" body="Spans, metrics, logs. Pipe to your stack." />
            </div>
          </div>

          <pre className="code">{code}</pre>
        </div>
      </div>
    </section>
  )
}

function DxFeature({ title, body }: { title: string; body: string }) {
  return (
    <div>
      <h4 style={{ fontSize: 13, fontWeight: 500, margin: '0 0 4px', color: 'var(--fg-primary)' }}>{title}</h4>
      <p style={{ margin: 0, color: 'var(--fg-muted)', fontSize: 12.5 }}>{body}</p>
    </div>
  )
}

function Enterprise() {
  return (
    <section id="enterprise">
      <div className="wrap">
        <div className="section-eyebrow">Enterprise</div>
        <h2>Built for the security review.</h2>
        <p className="sub">
          SAML, SCIM, OPA-based policy, immutable audit. Run on your own VPC, your own Kubernetes, or fully
          air-gapped against a local Ollama daemon.
        </p>

        <div className="trust-grid">
          <div style={{ position: 'relative', aspectRatio: '1', borderRadius: 'var(--r-5)', border: '1px solid var(--border-default)', background: 'var(--bg-canvas)', display: 'grid', placeItems: 'center', overflow: 'hidden' }}>
            <div className="spotlight" />
            <svg viewBox="0 0 200 200" width={180} height={180} style={{ position: 'relative', zIndex: 1 }}>
              <g fill="none" stroke="var(--border-strong)" strokeWidth="0.6">
                <circle cx="100" cy="100" r="40" />
                <circle cx="100" cy="100" r="58" />
                <circle cx="100" cy="100" r="76" />
                <circle cx="100" cy="100" r="94" />
              </g>
              <g fontFamily="var(--font-mono)" fontSize="9" fill="var(--fg-muted)" letterSpacing="2">
                <text x="14" y="105">SOC 2</text>
                <text x="150" y="105">ISO</text>
                <text x="80" y="14">HIPAA</text>
                <text x="76" y="198">GDPR</text>
              </g>
              <polygon points="100,55 130,75 130,115 100,140 70,115 70,75" fill="oklch(0.20 0.013 250)" stroke="var(--blue-3)" strokeWidth="1.4" />
              <path d="M85 100 l10 10 l22 -22" stroke="var(--blue-4)" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>

          <div className="trust-list">
            <TrustItem title="Identity & access" body="SAML / OIDC SSO, SCIM provisioning, fine-grained RBAC, scoped API tokens with workload identity." badges={['SAML 2.0', 'SCIM 2.0', 'OIDC']} />
            <TrustItem title="Policy & governance" body="OPA policy bundles enforced at the supervisor. Block models, tools, or data classes per tenant." badges={['OPA', 'Cedar', 'Custom rules']} />
            <TrustItem title="Audit & retention" body="Immutable append-only log, partitioned by tenant + day. Export to S3 or SIEM. WORM-compatible." badges={['SOC 2 Type II', 'HIPAA', 'GDPR']} />
            <TrustItem title="Air-gapped deployment" body="Run end-to-end against a local Ollama daemon. No keys, no egress, no third-party services. Offline bundle ships in 4.2 GB." badges={['Ollama', 'vLLM', 'On-prem']} />
          </div>
        </div>
      </div>
    </section>
  )
}

function TrustItem({ title, body, badges }: { title: string; body: string; badges: string[] }) {
  return (
    <div className="trust-item">
      <h4>{title}</h4>
      <p>{body}</p>
      <div className="badge-row">
        {badges.map((b) => (
          <span key={b} className="badge">{b}</span>
        ))}
      </div>
    </div>
  )
}

function CallToAction() {
  const cliBlock = `# clone + boot
$ git clone github.com/forgeflow/forgeflow
$ cd forgeflow && cp .env.example .env

# bring up the stack
$ docker compose up
→ api      :8000  ready
→ mcp      :8001  14 tools registered
→ postgres :5432  migrated · pgvector OK
→ dash     :8501  ready`

  return (
    <section>
      <div className="wrap">
        <div className="cta">
          <div>
            <div className="section-eyebrow">Get started</div>
            <h2>Ship the AI system. Not the plumbing.</h2>
            <p>
              Run the open core today. Move to managed when you outgrow your laptop. Talk to us when you need
              SSO, OPA, and a four-nines SLA.
            </p>
            <div className="ctas">
              <a href={CONSOLE_HREF} className="btn primary">
                Open the console →
              </a>
              <a href="#" className="btn">Talk to engineering</a>
            </div>
          </div>
          <pre className="code" style={{ background: 'oklch(0.125 0.010 250 / 0.6)' }}>{cliBlock}</pre>
        </div>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer>
      <div className="wrap">
        <div className="grid">
          <div>
            <Link to="/" className="brand">
              <span className="brand-mark" />
              <span className="brand-name">ForgeFlow</span>
            </Link>
            <p style={{ marginTop: 14, maxWidth: '32ch' }}>
              The operating system for production AI agents. Open-core, Apache 2.0.
            </p>
            <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
              <span className="badge">Apache 2.0</span>
              <span className="badge">v3.4.1</span>
              <span className="badge emerald">
                <span className="dot live" /> All systems normal
              </span>
            </div>
          </div>
          <FooterCol title="Product" items={['Console', 'Agents', 'Workflows', 'Memory', 'Evaluations']} />
          <FooterCol title="Developers" items={['Docs', 'SDK · Python', 'SDK · TypeScript', 'CLI', 'OpenAPI']} />
          <FooterCol title="Enterprise" items={['Security', 'SLA', 'Air-gap deploy', 'Pricing', 'Contact']} />
          <FooterCol title="Company" items={['About', 'Customers', 'Careers', 'Brand', 'Status']} />
        </div>
        <div className="hairline" style={{ marginTop: 40 }} />
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 18, fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '.04em' }}>
          <span>© 2026 ForgeFlow Labs, Inc.</span>
          <span>Built in San Francisco · Apache 2.0</span>
        </div>
      </div>
    </footer>
  )
}

function FooterCol({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h5>{title}</h5>
      <ul>
        {items.map((i) => (
          <li key={i}>
            <a href="#">{i}</a>
          </li>
        ))}
      </ul>
    </div>
  )
}
