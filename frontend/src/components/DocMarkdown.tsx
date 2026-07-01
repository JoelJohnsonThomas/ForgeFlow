import { useState } from 'react'
import type { ReactElement, ReactNode } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import langBash from 'highlight.js/lib/languages/bash'
import langIni from 'highlight.js/lib/languages/ini'
import langJson from 'highlight.js/lib/languages/json'
import langPython from 'highlight.js/lib/languages/python'
import langSql from 'highlight.js/lib/languages/sql'
import langYaml from 'highlight.js/lib/languages/yaml'
import { Link } from '@tanstack/react-router'
import { Mermaid } from './Mermaid'
import { resolveHref, resolveImg, slugify } from '../docs/manifest'

// Recursively extract plain text from a node tree (for heading anchor ids,
// copy-to-clipboard, and callout detection).
function textOf(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(textOf).join('')
  if (node && typeof node === 'object' && 'props' in node) {
    return textOf((node as ReactElement<{ children?: ReactNode }>).props.children)
  }
  return ''
}

type HeadingTag = 'h1' | 'h2' | 'h3' | 'h4'
function heading(Tag: HeadingTag) {
  return function H({ children }: { children?: ReactNode }) {
    const id = slugify(textOf(children))
    // h2/h3 get a hover anchor link for sharable deep links.
    if (Tag === 'h2' || Tag === 'h3') {
      return (
        <Tag id={id} className="doc-heading">
          {children}
          <a href={`#${id}`} className="doc-anchor" aria-label="Link to this section">
            #
          </a>
        </Tag>
      )
    }
    return <Tag id={id}>{children}</Tag>
  }
}

/** Code block with a copy-to-clipboard button. */
function CodeBlock({ children }: { children?: ReactNode }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    const text = textOf(children).replace(/\n$/, '')
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      // Clipboard API unavailable (permissions / non-secure context) —
      // fall back to a hidden textarea + execCommand.
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      try {
        document.execCommand('copy')
      } finally {
        ta.remove()
      }
    }
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1600)
  }
  return (
    <div className="doc-codeblock">
      <button type="button" className="doc-copy-btn" onClick={copy} aria-label="Copy code to clipboard">
        {copied ? 'Copied ✓' : 'Copy'}
      </button>
      <pre className="doc-code">{children}</pre>
    </div>
  )
}

const CALLOUT_KINDS = ['note', 'tip', 'important', 'warning', 'caution'] as const
type CalloutKind = (typeof CALLOUT_KINDS)[number]

// Docs use "> **Note:** …" / "> **Warning:** …" blockquotes — style them as
// typed callouts. Any other blockquote renders as a plain quote.
function Blockquote({ children }: { children?: ReactNode }) {
  const text = textOf(children).trim().toLowerCase()
  const kind = CALLOUT_KINDS.find((k) => text.startsWith(k)) as CalloutKind | undefined
  if (kind) {
    return <blockquote className={`doc-callout doc-callout-${kind}`}>{children}</blockquote>
  }
  return <blockquote>{children}</blockquote>
}

/**
 * Renders one docs/*.md page. Rewrites intra-doc links to in-app /docs routes,
 * resolves images and same-page anchors, renders ```mermaid blocks as SVG,
 * highlights code, and adds copy buttons + heading anchors.
 * `file` is the page's path under docs/ (needed to resolve relative links).
 */
export function DocMarkdown({ source, file }: { source: string; file: string }) {
  return (
    <div className="doc-prose">
      <Markdown
        remarkPlugins={[remarkGfm]}
        // Only the grammars the docs actually use are registered (keeps the
        // lazy docs chunk small). `mermaid` blocks must stay un-highlighted:
        // the <pre> component below hands their raw text to the Mermaid renderer.
        rehypePlugins={[
          [
            rehypeHighlight,
            {
              detect: false,
              languages: {
                bash: langBash,
                python: langPython,
                json: langJson,
                yaml: langYaml,
                sql: langSql,
                ini: langIni,
              },
              aliases: { bash: ['sh', 'shell'], ini: ['env', 'dotenv'] },
              plainText: ['mermaid', 'text', 'txt'],
            },
          ],
        ]}
        components={{
          a({ href, children }) {
            const r = resolveHref(file, href ?? '')
            if (r.kind === 'internal') {
              return (
                <Link to={r.to} hash={r.hash ? r.hash.slice(1) : undefined}>
                  {children}
                </Link>
              )
            }
            if (r.kind === 'anchor') return <a href={r.hash}>{children}</a>
            return (
              <a href={r.url} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            )
          },
          img({ src, alt }) {
            return <img src={resolveImg(file, typeof src === 'string' ? src : '')} alt={alt ?? ''} loading="lazy" />
          },
          pre({ children }) {
            const child = (Array.isArray(children) ? children[0] : children) as
              | ReactElement<{ className?: string; children?: ReactNode }>
              | undefined
            const cls = child?.props?.className ?? ''
            if (/language-mermaid/.test(cls)) {
              const code = textOf(child?.props?.children).replace(/\n$/, '')
              return <Mermaid chart={code} />
            }
            return <CodeBlock>{children}</CodeBlock>
          },
          blockquote: Blockquote,
          h1: heading('h1'),
          h2: heading('h2'),
          h3: heading('h3'),
          h4: heading('h4'),
        }}
      >
        {source}
      </Markdown>
    </div>
  )
}
