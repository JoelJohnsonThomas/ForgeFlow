// Client-side full-text search over the in-app docs. The index is built once
// from the same raw markdown sources the pages render, so results can never
// drift from the content. Scoring favors titles, then headings, then body.

import { DOCS, slugify, type DocEntry } from './manifest'
import { getDocSource } from './content'

export type TocItem = { id: string; text: string; level: 2 | 3 }

export type SearchHit = {
  entry: DocEntry
  score: number
  /** Plain-text snippet around the first body match (undefined for title-only hits). */
  snippet?: string
  /** First heading that matched the query, for deep-linking. */
  heading?: TocItem
}

// Strip markdown syntax that would pollute snippets: links → text, emphasis
// markers, inline-code backticks, table pipes, heading hashes.
function stripMd(line: string): string {
  return line
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/[*_`]/g, '')
    .replace(/^#{1,6}\s+/, '')
    .replace(/\|/g, ' ')
    .trim()
}

/** Extract h2/h3 headings (outside code fences) for ToC + search. */
export function extractToc(source: string): TocItem[] {
  const out: TocItem[] = []
  let inFence = false
  for (const line of source.split('\n')) {
    if (/^\s*(```|~~~)/.test(line)) {
      inFence = !inFence
      continue
    }
    if (inFence) continue
    const m = /^(#{2,3})\s+(.+)$/.exec(line)
    if (!m) continue
    const text = stripMd(m[2])
    out.push({ id: slugify(text), text, level: m[1].length as 2 | 3 })
  }
  return out
}

type IndexedDoc = {
  entry: DocEntry
  title: string
  summary: string
  headings: TocItem[]
  /** Body with markdown syntax stripped, single-spaced (original case, for snippets). */
  body: string
  /** Lowercased copies for matching. */
  lcTitle: string
  lcSummary: string
  lcBody: string
}

let index: IndexedDoc[] | undefined

function buildIndex(): IndexedDoc[] {
  return DOCS.map((entry) => {
    const source = getDocSource(entry.file) ?? ''
    // Keep fenced code in the body — users search for commands and endpoints.
    const body = source
      .split('\n')
      .filter((l) => !/^\s*(```|~~~)/.test(l))
      .map(stripMd)
      .filter(Boolean)
      .join(' ')
    const title = entry.title
    const summary = entry.summary ?? ''
    return {
      entry,
      title,
      summary,
      headings: extractToc(source),
      body,
      lcTitle: title.toLowerCase(),
      lcSummary: summary.toLowerCase(),
      lcBody: body.toLowerCase(),
    }
  })
}

const SNIPPET_RADIUS = 70

function makeSnippet(body: string, lcBody: string, term: string): string | undefined {
  const at = lcBody.indexOf(term)
  if (at === -1) return undefined
  const start = Math.max(0, at - SNIPPET_RADIUS)
  const end = Math.min(body.length, at + term.length + SNIPPET_RADIUS)
  return (start > 0 ? '…' : '') + body.slice(start, end).trim() + (end < body.length ? '…' : '')
}

/**
 * Rank docs against a query. Every whitespace-separated term must appear
 * somewhere in the page (title, summary, heading, or body).
 */
export function searchDocs(query: string, limit = 12): SearchHit[] {
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean)
  if (terms.length === 0) return []
  index ??= buildIndex()

  const hits: SearchHit[] = []
  for (const doc of index) {
    let score = 0
    let heading: TocItem | undefined
    let snippet: string | undefined
    let allMatch = true

    for (const term of terms) {
      let matched = false
      if (doc.lcTitle.includes(term)) {
        score += doc.lcTitle.startsWith(term) ? 12 : 8
        matched = true
      }
      const h = doc.headings.find((x) => x.text.toLowerCase().includes(term))
      if (h) {
        score += 4
        heading ??= h
        matched = true
      }
      if (doc.lcSummary.includes(term)) {
        score += 2
        matched = true
      }
      if (doc.lcBody.includes(term)) {
        score += 1
        snippet ??= makeSnippet(doc.body, doc.lcBody, term)
        matched = true
      }
      if (!matched) {
        allMatch = false
        break
      }
    }

    if (allMatch && score > 0) hits.push({ entry: doc.entry, score, snippet, heading })
  }

  return hits.sort((a, b) => b.score - a.score).slice(0, limit)
}

/** Split text into segments, marking the ones that match any query term. */
export function highlightSegments(text: string, query: string): { text: string; match: boolean }[] {
  const terms = query
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .sort((a, b) => b.length - a.length)
  if (terms.length === 0) return [{ text, match: false }]
  const pattern = new RegExp(`(${terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi')
  return text
    .split(pattern)
    .filter((s) => s !== '')
    .map((s) => ({ text: s, match: terms.includes(s.toLowerCase()) }))
}
