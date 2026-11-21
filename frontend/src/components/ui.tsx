import type { ReactNode } from 'react'

/* ---------- Highlighter tone map (functional semantic markers) ---------- */
const HL = {
  yellow: 'bg-[#fef08a] border-[#fde047] text-[#0f172a]',
  mint: 'bg-[#86efac] border-[#4ade80] text-[#0f172a]',
  coral: 'bg-[#fca5a5] border-[#fb7185] text-[#0f172a]',
  sky: 'bg-[#7dd3fc] border-[#38bdf8] text-[#0f172a]',
  lilac: 'bg-[#d8b4fe] border-[#c084fc] text-[#0f172a]',
} as const

export type Tone = keyof typeof HL

export function Chip({
  tone = 'yellow',
  dot = false,
  children,
  className = '',
}: {
  tone?: Tone
  dot?: boolean
  children: ReactNode
  className?: string
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-wide ring-1 ring-inset ${HL[tone]} ${className}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  )
}

/** Grey/ink pill badge (neutral metadata). */
export function Badge({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-slate-100 px-2.5 py-0.5 font-mono text-[11px] font-medium text-slate-600 ${className}`}
    >
      {children}
    </span>
  )
}

export function IndexCard({
  children,
  lift = false,
  overlay = false,
  className = '',
}: {
  children: ReactNode
  lift?: boolean
  overlay?: boolean
  className?: string
}) {
  const shadow = overlay ? 'index-card--overlay' : lift ? 'index-card--lift' : ''
  return (
    <div className={`index-card ${shadow} ${className}`}>
      {children}
    </div>
  )
}

export function InkButton({
  children,
  onClick,
  disabled = false,
  type = 'button',
  className = '',
}: {
  children: ReactNode
  onClick?: () => void
  disabled?: boolean
  type?: 'button' | 'submit'
  className?: string
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-lg border-[1.5px] border-slate-900 bg-slate-900 px-5 py-2 text-sm font-semibold text-white shadow-[2px_2px_0px_0px_rgba(15,23,42,0.2)] transition enabled:hover:-translate-x-px enabled:hover:-translate-y-px enabled:hover:shadow-[3px_3px_0px_0px_rgba(15,23,42,0.2)] enabled:active:translate-x-0 enabled:active:translate-y-0 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
    >
      {children}
    </button>
  )
}

export function GhostButton({
  children,
  onClick,
  disabled = false,
  className = '',
}: {
  children: ReactNode
  onClick?: () => void
  disabled?: boolean
  className?: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center gap-2 rounded-lg border-[1.5px] border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-900 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
    >
      {children}
    </button>
  )
}

export function Spinner({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <span
      className={`inline-block animate-spin-slow rounded-full border-2 border-slate-400 border-t-slate-900 ${className}`}
      role="status"
      aria-label="working"
    />
  )
}

export function ProgressBar({ current, total }: { current: number; total: number }) {
  const pct = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0
  return (
    <span className="inline-flex items-center gap-2 font-mono text-[11px] text-slate-500">
      <span className="relative h-1.5 w-24 overflow-hidden rounded-full bg-slate-200">
        <span className="absolute inset-y-0 left-0 bg-slate-900 transition-all" style={{ width: `${pct}%` }} />
      </span>
      {current}/{total}
    </span>
  )
}

export function SectionLabel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <span className={`font-mono text-[11px] font-semibold uppercase tracking-widest text-slate-500 ${className}`}>
      {children}
    </span>
  )
}

export function PinnedNotice({ children }: { children: ReactNode }) {
  return (
    <div className="border-l-4 border-[#fca5a5] bg-[#fca5a5]/15 px-4 py-3 text-sm text-ink">
      {children}
    </div>
  )
}
