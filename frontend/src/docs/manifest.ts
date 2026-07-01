// The in-app /docs route renders the repo's docs/*.md as the single source of
// truth. This manifest defines which pages appear, their order, and grouping.
// `file` is the path under docs/ (e.g. "tutorials/01-first-workflow.md").

export type DocGroup = 'Getting started' | 'Guides' | 'Reference' | 'Operations'

export type DocEntry = {
  slug: string
  file: string
  title: string
  group: DocGroup
  summary?: string
}

export const DOC_GROUPS: DocGroup[] = ['Getting started', 'Guides', 'Reference', 'Operations']

export const DOCS: DocEntry[] = [
  // Getting started
  { slug: 'tutorials', file: 'tutorials/README.md', title: 'Tutorials', group: 'Getting started', summary: 'Guided, step-by-step walkthroughs.' },
  { slug: 'tutorials-first-workflow', file: 'tutorials/01-first-workflow.md', title: 'Your first workflow', group: 'Getting started', summary: 'Boot the stack and run sales_ops end to end.' },
  { slug: 'tutorials-ollama', file: 'tutorials/02-run-offline-with-ollama.md', title: 'Run offline with Ollama', group: 'Getting started', summary: 'Execute workflows with a local LLM.' },
  { slug: 'tutorials-streaming', file: 'tutorials/03-streaming-and-debugging.md', title: 'Stream & debug a run', group: 'Getting started', summary: 'SSE, per-agent traces, failure modes.' },
  { slug: 'tutorials-memory', file: 'tutorials/04-semantic-memory.md', title: 'Semantic memory', group: 'Getting started', summary: 'Store and recall context with pgvector.' },
  { slug: 'faq', file: 'faq.md', title: 'FAQ', group: 'Getting started', summary: 'Quick answers; what is and isn\'t implemented.' },
  { slug: 'glossary', file: 'glossary.md', title: 'Glossary', group: 'Getting started', summary: 'Every term, defined.' },
  { slug: 'troubleshooting', file: 'troubleshooting.md', title: 'Troubleshooting', group: 'Getting started', summary: 'Common first-run failures and fixes.' },
  { slug: 'configuration', file: 'configuration.md', title: 'Configuration', group: 'Getting started', summary: 'Every environment variable, with defaults.' },

  // Guides
  { slug: 'examples', file: 'examples.md', title: 'Examples', group: 'Guides', summary: 'Runnable curl, Python, and streaming patterns.' },
  { slug: 'connectors', file: 'connectors.md', title: 'Connectors', group: 'Guides', summary: 'Enterprise connector credentials and setup.' },
  { slug: 'sales-ops-production', file: 'sales-ops-production.md', title: 'Sales-ops runbook', group: 'Guides', summary: 'A real HubSpot pipeline on Fly.io.' },

  // Reference
  { slug: 'api-reference', file: 'api-reference.md', title: 'API reference', group: 'Reference', summary: 'Endpoints, auth, roles, error semantics.' },
  { slug: 'architecture', file: 'architecture.md', title: 'Architecture', group: 'Reference', summary: 'System design with Mermaid diagrams.' },
  { slug: 'database', file: 'database.md', title: 'Database', group: 'Reference', summary: 'Schema, ER diagram, migrations.' },
  { slug: 'auth', file: 'auth.md', title: 'Authentication', group: 'Reference', summary: 'Tokens, refresh rotation, MFA, OIDC, RBAC.' },
  { slug: 'testing', file: 'testing.md', title: 'Testing', group: 'Reference', summary: 'Running and writing tests.' },

  // Operations
  { slug: 'operations-backup-dr', file: 'operations/backup-dr.md', title: 'Backup & disaster recovery', group: 'Operations', summary: 'Backup, restore, RPO/RTO, DR runbook.' },
  { slug: 'deployment-airgapped', file: 'deployment/AIRGAPPED.md', title: 'Air-gapped deployment', group: 'Operations', summary: 'Offline bundle builder.' },
]

export const DOCS_BY_SLUG: Record<string, DocEntry> = Object.fromEntries(DOCS.map((d) => [d.slug, d]))
export const DOCS_BY_FILE: Record<string, DocEntry> = Object.fromEntries(DOCS.map((d) => [d.file, d]))

export function prevNext(slug: string): { prev?: DocEntry; next?: DocEntry } {
  const i = DOCS.findIndex((d) => d.slug === slug)
  if (i === -1) return {}
  return { prev: DOCS[i - 1], next: DOCS[i + 1] }
}

const GH_BLOB = 'https://github.com/JoelJohnsonThomas/forgeflow/blob/main'
const GH_RAW = 'https://raw.githubusercontent.com/JoelJohnsonThomas/forgeflow/main'

// Resolve a relative path against a doc file, tracking escapes above docs/.
function resolve(fromFile: string, href: string): { path: string; escaped: boolean } {
  const dir = fromFile.includes('/') ? fromFile.slice(0, fromFile.lastIndexOf('/')).split('/') : []
  const stack = [...dir]
  let up = 0
  for (const seg of href.split('/')) {
    if (seg === '' || seg === '.') continue
    if (seg === '..') {
      if (stack.length) stack.pop()
      else up++
    } else {
      stack.push(seg)
    }
  }
  return { path: stack.join('/'), escaped: up > 0 }
}

export type ResolvedHref =
  | { kind: 'internal'; to: string; hash?: string }
  | { kind: 'anchor'; hash: string }
  | { kind: 'external'; url: string }

// Turn a markdown link href (as authored in docs/) into an in-app route,
// same-page anchor, or external GitHub link.
export function resolveHref(fromFile: string, href: string): ResolvedHref {
  if (/^https?:\/\//i.test(href) || href.startsWith('mailto:')) return { kind: 'external', url: href }
  if (href.startsWith('#')) return { kind: 'anchor', hash: href }

  const [rawPath, hash] = href.split('#')
  const { path, escaped } = resolve(fromFile, rawPath)

  if (escaped) return { kind: 'external', url: `${GH_BLOB}/${path}` }

  const entry = DOCS_BY_FILE[path]
  if (entry) return { kind: 'internal', to: `/docs/${entry.slug}`, hash: hash ? `#${hash}` : undefined }

  // A docs page that isn't in the in-app manifest (or docs/README.md) → GitHub.
  return { kind: 'external', url: `${GH_BLOB}/docs/${path}` }
}

// Resolve an <img src> in a doc to a GitHub raw URL so assets load without
// bundling binaries into the SPA.
export function resolveImg(fromFile: string, src: string): string {
  if (/^https?:\/\//i.test(src) || src.startsWith('data:')) return src
  const [rawPath] = src.split('#')
  const { path, escaped } = resolve(fromFile, rawPath)
  return escaped ? `${GH_RAW}/${path}` : `${GH_RAW}/docs/${path}`
}

// GitHub-style heading slug for in-page anchors.
export function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
}
