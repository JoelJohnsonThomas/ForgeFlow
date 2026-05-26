import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>

export function IconGrid(props: IconProps) {
  return (
    <svg className="ic" viewBox="0 0 14 14" fill="none" {...props}>
      <rect x="2" y="2" width="4" height="4" rx="1" stroke="currentColor" strokeWidth="1.2" />
      <rect x="8" y="2" width="4" height="4" rx="1" stroke="currentColor" strokeWidth="1.2" />
      <rect x="2" y="8" width="4" height="4" rx="1" stroke="currentColor" strokeWidth="1.2" />
      <rect x="8" y="8" width="4" height="4" rx="1" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  )
}

export function IconList(props: IconProps) {
  return (
    <svg className="ic" viewBox="0 0 14 14" fill="none" {...props}>
      <path d="M3 4h8M3 7h8M3 10h5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}

export function IconCheck(props: IconProps) {
  return (
    <svg className="ic" viewBox="0 0 14 14" fill="none" {...props}>
      <path d="M3 7l3 3 5-6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function IconAgents(props: IconProps) {
  return (
    <svg className="ic" viewBox="0 0 14 14" fill="none" {...props}>
      <circle cx="7" cy="7" r="2" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="7" cy="2" r="1.2" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="7" cy="12" r="1.2" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="2" cy="7" r="1.2" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="12" cy="7" r="1.2" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  )
}

export function IconMemory(props: IconProps) {
  return (
    <svg className="ic" viewBox="0 0 14 14" fill="none" {...props}>
      <path d="M3 4c0-1 1.5-2 4-2s4 1 4 2v6c0 1-1.5 2-4 2s-4-1-4-2V4z" stroke="currentColor" strokeWidth="1.2" />
      <path d="M3 7c0 1 1.5 2 4 2s4-1 4-2" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  )
}

export function IconCost(props: IconProps) {
  return (
    <svg className="ic" viewBox="0 0 14 14" fill="none" {...props}>
      <path d="M2 11l3-3 2 2 5-5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M9 3h3v3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}

export function IconEvals(props: IconProps) {
  return (
    <svg className="ic" viewBox="0 0 14 14" fill="none" {...props}>
      <path d="M3 12V6m4 6V3m4 9V8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}

export function IconWorkflow(props: IconProps) {
  return (
    <svg className="ic" viewBox="0 0 14 14" fill="none" {...props}>
      <circle cx="3" cy="3" r="1.5" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="11" cy="3" r="1.5" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="7" cy="11" r="1.5" stroke="currentColor" strokeWidth="1.2" />
      <path d="M4 4l2.5 6M10 4l-2.5 6" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  )
}

export function IconTools(props: IconProps) {
  return (
    <svg className="ic" viewBox="0 0 14 14" fill="none" {...props}>
      <path d="M9 2l3 3-7 7H2v-3l7-7z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
    </svg>
  )
}

export function IconShield(props: IconProps) {
  return (
    <svg className="ic" viewBox="0 0 14 14" fill="none" {...props}>
      <path d="M7 1.5L2 3.5v4c0 3 2.2 5 5 5.5 2.8-.5 5-2.5 5-5.5v-4L7 1.5z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
    </svg>
  )
}

export function IconBell(props: IconProps) {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" {...props}>
      <path d="M3 11h9l-1.5-2V7a3 3 0 0 0-6 0v2L3 11z" stroke="currentColor" strokeWidth="1.2" />
      <path d="M6 12.5a1.5 1.5 0 0 0 3 0" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  )
}

export function IconHelp(props: IconProps) {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" {...props}>
      <circle cx="7.5" cy="7.5" r="6" stroke="currentColor" strokeWidth="1.2" />
      <path d="M6 6a1.5 1.5 0 0 1 3 0c0 1-1.5 1-1.5 2.2M7.5 10.5v.01" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}

export function IconSearch(props: IconProps) {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" {...props}>
      <circle cx="5.5" cy="5.5" r="3.5" stroke="currentColor" strokeWidth="1.4" />
      <path d="M8 8l3 3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}

export function IconChevronDown(props: IconProps) {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" {...props}>
      <path d="M2 4l3 3 3-3" stroke="currentColor" fill="none" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}
