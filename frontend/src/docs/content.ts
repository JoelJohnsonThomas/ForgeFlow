// Eagerly import every docs/*.md as a raw string at build time. The repo's
// docs/ directory is the single source of truth — nothing is duplicated here.
// (vite.config.ts allows reading one level above the frontend root.)
const modules = import.meta.glob('../../../docs/**/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>

// Key by the path under docs/ (e.g. "tutorials/01-first-workflow.md").
const byFile: Record<string, string> = {}
for (const [key, value] of Object.entries(modules)) {
  const m = key.match(/\/docs\/(.+\.md)$/)
  if (m) byFile[m[1]] = value
}

export function getDocSource(file: string): string | undefined {
  return byFile[file]
}
