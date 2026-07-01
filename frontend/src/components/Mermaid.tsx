import { useEffect, useRef, useState } from 'react'

// Lazy-load mermaid only when a diagram is actually rendered, so it stays out of
// the main bundle. Initialised once, dark theme to match the console.
let mermaidPromise: Promise<typeof import('mermaid').default> | null = null
function loadMermaid() {
  if (!mermaidPromise) {
    mermaidPromise = import('mermaid').then((m) => {
      m.default.initialize({
        startOnLoad: false,
        theme: 'dark',
        securityLevel: 'strict',
        fontFamily: 'var(--font-sans, system-ui)',
      })
      return m.default
    })
  }
  return mermaidPromise
}

let counter = 0

export function Mermaid({ chart }: { chart: string }) {
  const [svg, setSvg] = useState('')
  const [failed, setFailed] = useState(false)
  const idRef = useRef(`mermaid-${++counter}`)

  useEffect(() => {
    // State is set only from the async callbacks below (not synchronously in the
    // effect body), so a chart change re-renders without cascading renders.
    let cancelled = false
    loadMermaid()
      .then((mermaid) => mermaid.render(idRef.current, chart))
      .then(({ svg }) => {
        if (!cancelled) setSvg(svg)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [chart])

  // On failure, fall back to the diagram source rather than a blank space.
  if (failed) return <pre className="doc-code"><code>{chart}</code></pre>
  if (!svg) return <div className="doc-mermaid-loading">rendering diagram…</div>
  return <div className="doc-mermaid" role="img" dangerouslySetInnerHTML={{ __html: svg }} />
}
