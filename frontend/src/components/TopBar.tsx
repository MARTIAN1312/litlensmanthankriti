import type { ReactNode } from 'react'
import { BookIcon, LayersIcon, PenIcon } from './icons'

export type ViewMode = 'minimalist' | 'detailed'

const MODES: { key: ViewMode; label: string; icon: ReactNode }[] = [
  { key: 'minimalist', label: 'Minimalist', icon: <PenIcon className="h-3.5 w-3.5" /> },
  { key: 'detailed', label: 'Detailed Lab', icon: <LayersIcon className="h-3.5 w-3.5" /> },
]

export function ModeToggle({
  mode,
  onChange,
  disabled = false,
}: {
  mode: ViewMode
  onChange: (m: ViewMode) => void
  disabled?: boolean
}) {
  return (
    <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-1 text-xs font-medium">
      {MODES.map((m) => {
        const active = mode === m.key
        return (
          <button
            key={m.key}
            type="button"
            onClick={() => onChange(m.key)}
            disabled={disabled}
            aria-pressed={active}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 transition disabled:cursor-not-allowed ${
              active
                ? 'bg-white font-semibold text-slate-900 shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            {m.icon}
            {m.label}
          </button>
        )
      })}
    </div>
  )
}

export function TopBar({
  mode,
  onModeChange,
  onHome,
  showMode = true,
}: {
  mode: ViewMode
  onModeChange: (m: ViewMode) => void
  onHome: () => void
  showMode?: boolean
}) {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-paper/90 px-5 py-3 backdrop-blur md:px-8">
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <button onClick={onHome} className="group flex items-center gap-3" aria-label="LitLens home">
          <span className="flex items-center gap-2 rounded-lg bg-slate-900 px-2.5 py-1.5 font-bold tracking-tight text-white shadow-[2px_2px_0px_0px_rgba(15,23,42,0.2)] transition group-hover:-translate-x-px group-hover:-translate-y-px">
            <BookIcon className="h-4 w-4 text-[#fef08a]" />
            <span className="text-sm">LitLens</span>
          </span>
          <span className="hidden rounded border border-yellow-200 bg-yellow-100 px-2 py-0.5 font-mono text-[11px] font-semibold text-yellow-800 sm:inline">
            study desk #04
          </span>
        </button>

        {showMode && <ModeToggle mode={mode} onChange={onModeChange} />}
      </div>
    </header>
  )
}
