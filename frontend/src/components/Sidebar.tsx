import type { ReactNode } from 'react'
import {
  IconAgents,
  IconCheck,
  IconCost,
  IconEvals,
  IconGrid,
  IconList,
  IconMemory,
  IconShield,
  IconTools,
  IconWorkflow,
} from './icons'

export type ViewId =
  | 'overview'
  | 'runs'
  | 'approvals'
  | 'agents'
  | 'memory'
  | 'cost'
  | 'evals'
  | 'workflows'
  | 'tools'
  | 'audit'
  | 'clusters'
  | 'rbac'
  | 'marketplace'

type NavItem = { id: ViewId; label: string; icon: ReactNode; count?: number; countColor?: 'amber' }

// Counts are intentionally omitted rather than hardcoded — a fabricated "12"
// would misrepresent live state. Wire `count` to the real queries when a
// per-view count endpoint is available.
const OBSERVE: NavItem[] = [
  { id: 'overview', label: 'Overview', icon: <IconGrid /> },
  { id: 'runs', label: 'Live runs', icon: <IconList /> },
  { id: 'approvals', label: 'Approvals', icon: <IconCheck /> },
  { id: 'agents', label: 'Agents', icon: <IconAgents /> },
  { id: 'memory', label: 'Memory', icon: <IconMemory /> },
  { id: 'cost', label: 'Cost & spend', icon: <IconCost /> },
  { id: 'evals', label: 'Evaluations', icon: <IconEvals /> },
]

const BUILD: NavItem[] = [
  { id: 'workflows', label: 'Workflows', icon: <IconWorkflow /> },
  { id: 'tools', label: 'Tools · MCP', icon: <IconTools /> },
  { id: 'marketplace', label: 'Marketplace', icon: <IconGrid /> },
]

const OPERATE: NavItem[] = [
  { id: 'clusters', label: 'Clusters', icon: <IconAgents /> },
  { id: 'audit', label: 'Audit log', icon: <IconShield /> },
  { id: 'rbac', label: 'RBAC & secrets', icon: <IconCheck /> },
]

type SidebarProps = {
  active: ViewId
  onSelect: (id: ViewId) => void
}

export function Sidebar({ active, onSelect }: SidebarProps) {
  return (
    <aside className="sidebar" aria-label="Console sections">
      <Group title="Observe" items={OBSERVE} active={active} onSelect={onSelect} />
      <Group title="Build" items={BUILD} active={active} onSelect={onSelect} />
      <Group title="Operate" items={OPERATE} active={active} onSelect={onSelect} />
    </aside>
  )
}

function Group({
  title,
  items,
  active,
  onSelect,
}: {
  title: string
  items: NavItem[]
  active: ViewId
  onSelect: (id: ViewId) => void
}) {
  return (
    <div className="group">
      <div className="group-title">{title}</div>
      {items.map((item) => {
        const isActive = item.id === active
        const countStyle =
          item.countColor === 'amber'
            ? {
                background: 'oklch(0.30 0.06 75 / 0.45)',
                borderColor: 'oklch(0.50 0.12 75 / 0.5)',
                color: 'var(--amber-4)',
              }
            : undefined
        return (
          <a
            key={item.id}
            className={`navlink${isActive ? ' active' : ''}`}
            onClick={(e) => {
              e.preventDefault()
              onSelect(item.id)
            }}
            href={`#${item.id}`}
            aria-current={isActive ? 'page' : undefined}
          >
            {item.icon}
            {item.label}
            {item.count !== undefined && (
              <span className="count" style={countStyle} aria-hidden="true">
                {item.count}
              </span>
            )}
          </a>
        )
      })}
    </div>
  )
}
