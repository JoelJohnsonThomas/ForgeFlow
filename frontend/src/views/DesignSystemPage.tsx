import { useEffect } from 'react'
import { Link } from '@tanstack/react-router'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import '../styles/design-system.css'

export function DesignSystemPage() {
  useDocumentTitle('Design system')
  useEffect(() => {
    document.body.classList.add('design-system')
    return () => document.body.classList.remove('design-system')
  }, [])

  return (
    <>
      <DsNav />
      <div className="ds-page">
        <DsHero />
        <ColorSection />
        <TypeSection />
        <SpaceSection />
        <ComponentsSection />
        <MotionSection />
        <ImplementationSection />
      </div>
    </>
  )
}

function DsNav() {
  return (
    <header className="ds-nav">
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
            <li><a href="/architecture">Architecture</a></li>
            <li><a href="/design-system" className="active">Design system</a></li>
          </ul>
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-muted)' }}>
          ds · v1.0
        </div>
      </div>
    </header>
  )
}

function DsHero() {
  return (
    <section className="ds-hero">
      <div className="section-eyebrow">DESIGN SYSTEM · v1.0</div>
      <h1>The language we built ForgeFlow in.</h1>
      <p className="lede">
        Tokens, type, components, motion. The same surface every team — landing, console, marketing, docs,
        internal tools — composes from. Optimized for high information density without visual noise; for
        operators and engineers; for dark rooms at 2am.
      </p>
      <div className="ds-toc">
        <a href="#color"><span className="label">01</span><span className="name">Color &amp; signal</span></a>
        <a href="#type"><span className="label">02</span><span className="name">Typography</span></a>
        <a href="#space"><span className="label">03</span><span className="name">Space, radii, grid</span></a>
        <a href="#components"><span className="label">04</span><span className="name">Components</span></a>
        <a href="#motion"><span className="label">05</span><span className="name">Motion</span></a>
      </div>
    </section>
  )
}

const SURFACE_SWATCHES = [
  { name: 'bg-page', hex: 'oklch(0.145 0.012 250)', bg: 'var(--bg-page)' },
  { name: 'bg-canvas', hex: 'oklch(0.165 0.012 250)', bg: 'var(--bg-canvas)' },
  { name: 'bg-elevated', hex: 'oklch(0.205 0.013 250)', bg: 'var(--bg-elevated)' },
  { name: 'bg-overlay', hex: 'oklch(0.235 0.014 250)', bg: 'var(--bg-overlay)' },
  { name: 'bg-inset', hex: 'oklch(0.125 0.010 250)', bg: 'var(--bg-inset)' },
  { name: 'border', hex: 'oklch(0.305 0.012 250)', bg: 'var(--border-default)' },
]

const FOREGROUND_SWATCHES = [
  { name: 'fg-primary', hex: 'oklch(0.965)', bg: 'var(--fg-primary)' },
  { name: 'fg-secondary', hex: 'oklch(0.82)', bg: 'var(--fg-secondary)' },
  { name: 'fg-muted', hex: 'oklch(0.62)', bg: 'var(--fg-muted)' },
  { name: 'fg-subtle', hex: 'oklch(0.48)', bg: 'var(--fg-subtle)' },
  { name: 'fg-faint', hex: 'oklch(0.36)', bg: 'var(--fg-faint)' },
]

const SIGNAL_RAMPS = [
  { name: 'Blue · primary', color: 'var(--blue-4)', sub: 'action · supervisor · routing', stops: ['var(--blue-1)', 'var(--blue-2)', 'var(--blue-3)', 'var(--blue-4)', 'var(--blue-5)'] },
  { name: 'Purple · research', color: 'var(--purple-4)', sub: 'enrichment · A2A', stops: ['var(--purple-1)', 'var(--purple-2)', 'var(--purple-3)', 'var(--purple-4)'] },
  { name: 'Emerald · success', color: 'var(--emerald-4)', sub: 'healthy · completed', stops: ['var(--emerald-1)', 'var(--emerald-2)', 'var(--emerald-3)', 'var(--emerald-4)'] },
  { name: 'Amber · warning', color: 'var(--amber-4)', sub: 'approval · degraded', stops: ['var(--amber-1)', 'var(--amber-2)', 'var(--amber-3)', 'var(--amber-4)'] },
  { name: 'Red · critical', color: 'var(--red-4)', sub: 'failed · breach · halt', stops: ['var(--red-1)', 'var(--red-2)', 'var(--red-3)', 'var(--red-4)'] },
]

function Swatch({ name, hex, bg }: { name: string; hex: string; bg: string }) {
  return (
    <div className="swatch">
      <div className="color" style={{ background: bg }} />
      <div className="meta">
        <div className="name">{name}</div>
        <div className="hex">{hex}</div>
      </div>
    </div>
  )
}

function ColorSection() {
  return (
    <section className="ds-section" id="color">
      <h2><span className="num">01</span>Color &amp; signal</h2>
      <p className="lede">
        Deep graphite canvas, warm-white foreground, five signal hues tuned to the same chroma so they read at
        the same visual weight. Authored in oklch.
      </p>

      <div className="section-eyebrow" style={{ marginTop: 8 }}>SURFACE</div>
      <div className="palette" style={{ marginTop: 14 }}>
        {SURFACE_SWATCHES.map((s) => <Swatch key={s.name} {...s} />)}
      </div>

      <div className="section-eyebrow" style={{ marginTop: 28 }}>FOREGROUND</div>
      <div className="palette" style={{ marginTop: 14 }}>
        {FOREGROUND_SWATCHES.map((s) => <Swatch key={s.name} {...s} />)}
      </div>

      <div className="section-eyebrow" style={{ marginTop: 28 }}>SIGNAL</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16, marginTop: 14 }}>
        {SIGNAL_RAMPS.map((r) => (
          <div className="swatch" key={r.name}>
            <div style={{ display: 'grid', gridTemplateRows: `repeat(${r.stops.length}, 1fr)`, aspectRatio: '1.4' }}>
              {r.stops.map((stop, i) => <div key={i} style={{ background: stop }} />)}
            </div>
            <div className="meta">
              <div className="name" style={{ color: r.color }}>{r.name}</div>
              <div className="hex">{r.sub}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function TypeSection() {
  return (
    <section className="ds-section" id="type">
      <h2><span className="num">02</span>Typography</h2>
      <p className="lede">
        Two faces: Geist for everything UI, JetBrains Mono for IDs, code, numbers, and any time we want to
        whisper "this is data." Tabular numerals everywhere they live in a table.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 64 }}>
        <div>
          <div className="section-eyebrow">DISPLAY · Geist</div>
          <div style={{ marginTop: 8 }}>
            <div style={{ fontSize: 60, fontWeight: 500, letterSpacing: '-0.035em', lineHeight: 1.05, color: 'var(--fg-primary)' }}>
              Aa Bb Cc 123
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-muted)', marginTop: 8 }}>
              Geist · 300 · 400 · 500 · 600 · 700
            </div>
          </div>
        </div>
        <div>
          <div className="section-eyebrow">MONO · JetBrains Mono</div>
          <div style={{ marginTop: 8 }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 48, fontWeight: 500, color: 'var(--fg-primary)' }}>
              Aa Bb 0123 ≠
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-muted)', marginTop: 8 }}>
              JetBrains Mono · 400 · 500 · 600 · with zero-slash
            </div>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 36, background: 'var(--bg-canvas)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--r-3)', padding: '8px 24px' }}>
        <TypeSpec lbl="Display / 72" spec="geist · 500 · -3.5% · 1.0">
          <span style={{ fontSize: 72, fontWeight: 500, letterSpacing: '-0.035em', lineHeight: 1, color: 'var(--fg-primary)' }}>
            Production AI agents
          </span>
        </TypeSpec>
        <TypeSpec lbl="H1 / 48" spec="geist · 500 · -3% · 1.05">
          <span style={{ fontSize: 48, fontWeight: 500, letterSpacing: '-0.03em', lineHeight: 1.05, color: 'var(--fg-primary)' }}>
            Operate AI like the rest of your stack.
          </span>
        </TypeSpec>
        <TypeSpec lbl="H2 / 24" spec="geist · 500 · -1.8% · 1.2">
          <span style={{ fontSize: 24, fontWeight: 500, letterSpacing: '-0.018em', lineHeight: 1.2, color: 'var(--fg-primary)' }}>
            Approval queue
          </span>
        </TypeSpec>
        <TypeSpec lbl="Body / 14" spec="geist · 400 · 1.55">
          <span style={{ fontSize: 14, lineHeight: 1.55, color: 'var(--fg-secondary)', maxWidth: '56ch' }}>
            ForgeFlow orchestrates teams of specialized agents across your business — with human-in-the-loop
            approvals, semantic memory, and audit trail.
          </span>
        </TypeSpec>
        <TypeSpec lbl="Caption / 11" spec="jbmono · 500 · +12% · uppercase">
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '.12em', textTransform: 'uppercase', color: 'var(--fg-muted)' }}>
            RUN · WF_8K42N · 12.4S
          </span>
        </TypeSpec>
        <TypeSpec lbl="Numeric / 24" spec="jbmono · tabular · 0.04">
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 24, color: 'var(--fg-primary)', fontVariantNumeric: 'tabular-nums' }}>
            $4,148.20 · 99.992%
          </span>
        </TypeSpec>
      </div>
    </section>
  )
}

function TypeSpec({ lbl, spec, children }: { lbl: string; spec: string; children: React.ReactNode }) {
  return (
    <div className="type-spec">
      <div className="lbl">{lbl}</div>
      <div>{children}</div>
      <div className="spec">{spec}</div>
    </div>
  )
}

const SPACING_SCALE = [
  { size: 4, label: '4 · s-1' },
  { size: 8, label: '8 · s-2' },
  { size: 12, label: '12 · s-3' },
  { size: 16, label: '16 · s-4' },
  { size: 24, label: '24 · s-6' },
  { size: 32, label: '32 · s-8' },
  { size: 48, label: '48 · s-12' },
  { size: 64, label: '64 · s-16' },
  { size: 96, label: '96 · s-24' },
]
const RADII = [
  { r: 3, label: '3 · r-1' },
  { r: 5, label: '5 · r-2' },
  { r: 8, label: '8 · r-3' },
  { r: 12, label: '12 · r-4' },
  { r: 16, label: '16 · r-5' },
  { r: 999, label: '∞ · pill' },
]
const ELEVATIONS = [
  { shadow: 'var(--shadow-sm)', label: 'SHADOW-SM', desc: 'cards · inputs · low-elevation panels' },
  { shadow: 'var(--shadow-md)', label: 'SHADOW-MD', desc: 'popovers · menus · raised panels' },
  { shadow: 'var(--shadow-lg)', label: 'SHADOW-LG', desc: 'modals · command palette · drawers', overlay: true },
  { shadow: 'var(--shadow-glow-blue)', label: 'GLOW · BLUE', desc: 'primary CTA · live status · focus ring', glow: true },
]

function SpaceSection() {
  return (
    <section className="ds-section" id="space">
      <h2><span className="num">03</span>Space, radii, grid</h2>
      <p className="lede">
        A 4px base. Touch surfaces sit on multiples of 8. Hairlines at 1px. Radii small to medium; we never
        round above 16px in product UI — soft is the wrong vibe.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 64, alignItems: 'start' }}>
        <div>
          <div className="section-eyebrow">SPACING SCALE</div>
          <div className="spacing-row">
            {SPACING_SCALE.map((s) => (
              <div className="sp-cell" key={s.label}>
                <div className="box" style={{ width: s.size, height: s.size }} />
                <div className="lbl">{s.label}</div>
              </div>
            ))}
          </div>

          <div className="section-eyebrow" style={{ marginTop: 32 }}>RADII</div>
          <div className="radii" style={{ marginTop: 14 }}>
            {RADII.map((r) => (
              <div className="ra-cell" key={r.label}>
                <div className="box" style={{ borderRadius: r.r }} />
                <div className="lbl">{r.label}</div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="section-eyebrow">ELEVATION</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 14 }}>
            {ELEVATIONS.map((e) => (
              <div
                key={e.label}
                style={{
                  background: e.overlay ? 'var(--bg-overlay)' : 'var(--bg-canvas)',
                  border: e.glow ? '1px solid var(--blue-3)' : (e.overlay ? '1px solid var(--border-default)' : '1px solid var(--border-subtle)'),
                  borderRadius: 8,
                  padding: 14,
                  boxShadow: e.shadow,
                }}
              >
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '.12em', textTransform: 'uppercase', color: e.glow ? 'var(--blue-4)' : 'var(--fg-muted)' }}>
                  {e.label}
                </div>
                <div style={{ marginTop: 4, fontSize: 12.5, color: 'var(--fg-secondary)' }}>{e.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

const AGENTS = [
  { color: 'blue', initials: 'SU', name: 'supervisor', role: 'router · structured' },
  { color: 'purple', initials: 'RS', name: 'researcher', role: 'web · scrape' },
  { color: 'emerald', initials: 'AN', name: 'analyzer', role: 'score · ICP' },
  { color: 'amber', initials: 'EX', name: 'executor', role: 'write · email' },
  { color: 'muted', initials: 'HL', name: 'human_loop', role: 'interrupt' },
  { color: 'red', initials: 'SE', name: 'security_gate', role: 'policy · pii' },
]

function ComponentsSection() {
  return (
    <section className="ds-section" id="components">
      <h2><span className="num">04</span>Components</h2>
      <p className="lede">
        The building blocks the console and landing surface compose from. Tokens above, components below —
        change a token, every component shifts.
      </p>

      <div className="section-eyebrow" style={{ marginBottom: 14 }}>BUTTONS</div>
      <div className="demo-grid">
        <div className="demo">
          <div className="hd"><div className="title">Primary &amp; secondary</div><div className="meta">.btn .btn.primary</div></div>
          <div className="body">
            <button className="btn primary">Approve · resume</button>
            <button className="btn">Replay</button>
            <button className="btn ghost">Cancel</button>
            <button className="btn primary sm">Confirm</button>
            <button className="btn sm">Filter</button>
          </div>
        </div>
        <div className="demo">
          <div className="hd"><div className="title">States</div><div className="meta">hover · disabled · loading</div></div>
          <div className="body">
            <button className="btn primary">Default</button>
            <button className="btn primary" style={{ filter: 'brightness(1.08)' }}>Hover</button>
            <button className="btn primary" style={{ opacity: 0.5, pointerEvents: 'none' }}>Disabled</button>
            <button className="btn">
              <svg width="13" height="13" viewBox="0 0 13 13">
                <circle cx="6.5" cy="6.5" r="4" stroke="currentColor" strokeWidth="1.4" fill="none" strokeDasharray="6 4">
                  <animateTransform attributeName="transform" type="rotate" from="0 6.5 6.5" to="360 6.5 6.5" dur="1s" repeatCount="indefinite" />
                </circle>
              </svg>
              Running…
            </button>
          </div>
        </div>
      </div>

      <div className="section-eyebrow" style={{ marginTop: 32, marginBottom: 14 }}>BADGES &amp; STATUS</div>
      <div className="demo">
        <div className="body">
          <span className="badge"><span className="dot live" /> live</span>
          <span className="badge emerald">● completed</span>
          <span className="badge amber">● awaiting approval</span>
          <span className="badge red">● failed</span>
          <span className="badge blue">● running</span>
          <span className="badge purple">● air-gapped</span>
          <span className="badge">sales_ops</span>
          <span className="badge mono">wf_8K42n</span>
          <span className="status-bar"><span className="dot live" /> 12 runs · 1.8k events/s</span>
        </div>
      </div>

      <div className="section-eyebrow" style={{ marginTop: 32, marginBottom: 14 }}>AGENT AVATARS</div>
      <p style={{ color: 'var(--fg-muted)', fontSize: 12.5, marginBottom: 14 }}>
        Two-letter monospace marks colored by role. Persistent across the console — same researcher reads as
        the same researcher in the topology, timeline, audit, and approval cards.
      </p>
      <div className="agent-grid">
        {AGENTS.map((a) => (
          <div key={a.name} className="agent-card">
            <div className={`av-lg ${a.color}`}>{a.initials}</div>
            <div className="name">{a.name}</div>
            <div className="role">{a.role}</div>
          </div>
        ))}
      </div>

      <div className="section-eyebrow" style={{ marginTop: 32, marginBottom: 14 }}>KPI &amp; PANELS</div>
      <div className="kpi-strip">
        <div className="kpi"><span className="label">Runs · 24h</span><span className="val">2,418</span><span className="delta up">▲ 14.2%</span></div>
        <div className="kpi"><span className="label">Success</span><span className="val">99.3<span className="u">%</span></span><span className="delta">stable</span></div>
        <div className="kpi"><span className="label">Spend</span><span className="val">$184.20</span><span className="delta down">▼ 8%</span></div>
        <div className="kpi"><span className="label">p50 wall</span><span className="val">11.8<span className="u">s</span></span><span className="delta">p95: 28.4s</span></div>
        <div className="kpi"><span className="label">Judge</span><span className="val" style={{ color: 'var(--emerald-4)' }}>8.9<span className="u">/10</span></span><span className="delta">hall 0.08%</span></div>
      </div>
    </section>
  )
}

function MotionSection() {
  return (
    <section className="ds-section" id="motion">
      <h2><span className="num">05</span>Motion</h2>
      <p className="lede">
        Motion is a state pointer, not a delight system. Three durations, three curves. Animations resolve in
        under 320ms; live indicators pulse at 1.6s; never bounce, never decorate.
      </p>

      <div className="motion-grid">
        <div className="motion-card ease-out">
          <div className="label">EASE-OUT · UI</div>
          <div className="desc">
            Default for hover, panel slides, focus transitions.<br />
            <span className="mono" style={{ color: 'var(--blue-4)' }}>cubic-bezier(0.16, 1, 0.3, 1)</span> · 180ms
          </div>
          <div className="stage"><div className="ball" /></div>
        </div>
        <div className="motion-card ease-spring">
          <div className="label">SPRING · DATA</div>
          <div className="desc">
            For data viz — bars settling, gauges updating, chart re-renders.<br />
            <span className="mono" style={{ color: 'var(--blue-4)' }}>cubic-bezier(0.2, 0.8, 0.2, 1)</span> · 320ms
          </div>
          <div className="stage"><div className="ball" /></div>
        </div>
        <div className="motion-card ease-linear">
          <div className="label">LINEAR · STREAM</div>
          <div className="desc">
            Streaming indicators, packet paths in topology, shimmer on running tasks.<br />
            <span className="mono" style={{ color: 'var(--blue-4)' }}>linear</span> · 1.6s loop
          </div>
          <div className="stage"><div className="ball" /></div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24, marginTop: 36 }}>
        <Principle eyebrow="PRINCIPLE 01" body={<>Use motion to communicate state, not personality. A pulsing dot says "alive"; an animated bar says "still working."</>} />
        <Principle eyebrow="PRINCIPLE 02" body={<>Honor <span className="mono">prefers-reduced-motion</span>. Replace movement with opacity changes; never gate functionality on animation.</>} />
        <Principle eyebrow="PRINCIPLE 03" body={<>Latency budget. UI transitions ≤ 200ms. Data viz updates ≤ 400ms. Anything longer needs a progress hint, not a wait.</>} />
      </div>
    </section>
  )
}

function Principle({ eyebrow, body }: { eyebrow: string; body: React.ReactNode }) {
  return (
    <div>
      <div className="section-eyebrow">{eyebrow}</div>
      <p style={{ marginTop: 6, fontSize: 13, color: 'var(--fg-secondary)' }}>{body}</p>
    </div>
  )
}

function ImplementationSection() {
  return (
    <section className="ds-section" style={{ borderBottom: 'none' }}>
      <h2><span className="num">06</span>Implementation</h2>
      <p className="lede">How the tokens land in code, and the stack we use for the console.</p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24 }}>
        <div>
          <div className="section-eyebrow">RUNTIME</div>
          <table className="kv" style={{ marginTop: 8 }}>
            <tbody>
              <tr><td>UI</td><td>React 19 · TS</td></tr>
              <tr><td>Styling</td><td>tokens.css · oklch CSS vars</td></tr>
              <tr><td>State</td><td>TanStack Query · component state</td></tr>
              <tr><td>Realtime</td><td>SSE via nginx · /workflows/{`{id}`}/stream</td></tr>
            </tbody>
          </table>
        </div>
        <div>
          <div className="section-eyebrow">GRAPHS &amp; CHARTS</div>
          <table className="kv" style={{ marginTop: 8 }}>
            <tbody>
              <tr><td>Workflow nodes</td><td>Hand-rolled SVG</td></tr>
              <tr><td>Topology</td><td>SVG + animateMotion packets</td></tr>
              <tr><td>Charts</td><td>Inline SVG paths · CSS gradients</td></tr>
              <tr><td>Trace flame</td><td>Stacked div bars</td></tr>
            </tbody>
          </table>
        </div>
        <div>
          <div className="section-eyebrow">QUALITY</div>
          <table className="kv" style={{ marginTop: 8 }}>
            <tbody>
              <tr><td>A11y target</td><td>WCAG 2.2 AA</td></tr>
              <tr><td>Perf budget</td><td>LCP &lt; 1.2s · INP &lt; 100ms</td></tr>
              <tr><td>Tokens</td><td>Single source: tokens.css</td></tr>
              <tr><td>Visual review</td><td>Playwright screenshots</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
