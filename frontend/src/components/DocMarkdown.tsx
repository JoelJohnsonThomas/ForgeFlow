import type { ReactElement, ReactNode } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Link } from '@tanstack/react-router'
import { Mermaid } from './Mermaid'
import { resolveHref, resolveImg, slugify } from '../docs/manifest'

// Recursively extract plain text from a node tree (for heading anchor ids).
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
    return <Tag id={id}>{children}</Tag>
  }
}

/**
 * Renders one docs/*.md page. Rewrites intra-doc links to in-app /docs routes,
 * resolves images and same-page anchors, and renders ```mermaid blocks as SVG.
 * `file` is the page's path under docs/ (needed to resolve relative links).
 */
export function DocMarkdown({ source, file }: { source: string; file: string }) {
  return (
    <div className="doc-prose">
      <Markdown
        remarkPlugins={[remarkGfm]}
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
              const code = String(child?.props?.children ?? '').replace(/\n$/, '')
              return <Mermaid chart={code} />
            }
            return <pre className="doc-code">{children}</pre>
          },
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
