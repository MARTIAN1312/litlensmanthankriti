import { useState } from 'react'
import type { ReviewResult } from '../api/types'
import { StatsBar } from '../components/StatsBar'
import type { ViewMode } from '../components/TopBar'
import { AskPanel } from '../components/panels/AskPanel'
import { ComparisonPanel } from '../components/panels/ComparisonPanel'
import { ExportPanel } from '../components/panels/ExportPanel'
import { PapersPanel } from '../components/panels/PapersPanel'
import { ReviewPanel } from '../components/panels/ReviewPanel'
import { ChatIcon, DownloadIcon, PenIcon, TableIcon, TargetIcon } from '../components/icons'

type TabKey = 'review' | 'comparison' | 'papers' | 'ask' | 'export'

const TABS: { key: TabKey; label: string; icon: typeof PenIcon }[] = [
  { key: 'review', label: 'Review', icon: PenIcon },
  { key: 'comparison', label: 'Comparison', icon: TableIcon },
  { key: 'papers', label: 'Papers', icon: TargetIcon },
  { key: 'ask', label: 'Ask', icon: ChatIcon },
  { key: 'export', label: 'Export', icon: DownloadIcon },
]

export function ResultsPage({ review, mode }: { review: ReviewResult; mode: ViewMode }) {
  const [tab, setTab] = useState<TabKey>('review')

  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-6 md:px-8">
      <div className="mb-4">
        <p className="font-mono text-[11px] font-semibold uppercase tracking-widest text-slate-400">review</p>
        <h1 className="mt-1 text-xl font-bold tracking-tight text-slate-900 md:text-2xl">{review.topic}</h1>
      </div>

      <div className="mb-5">
        <StatsBar review={review} />
      </div>

      <div className="mb-5 flex flex-wrap gap-1.5">
        {TABS.map((t) => {
          const Icon = t.icon
          const active = tab === t.key
          return (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              aria-pressed={active}
              className={`inline-flex items-center gap-2 rounded-lg border-[1.5px] px-3.5 py-2 text-sm font-semibold transition ${
                active
                  ? 'border-slate-900 bg-[#fef08a] text-slate-900 shadow-[2px_2px_0px_0px_rgba(15,23,42,0.2)]'
                  : 'border-slate-300 bg-white text-slate-500 hover:border-slate-900 hover:text-slate-900'
              }`}
            >
              <Icon className="h-4 w-4" />
              {t.label}
            </button>
          )
        })}
      </div>

      {tab === 'review' && <ReviewPanel review={review} mode={mode} />}
      {tab === 'comparison' && <ComparisonPanel review={review} />}
      {tab === 'papers' && <PapersPanel review={review} />}
      {tab === 'ask' && <AskPanel review={review} />}
      {tab === 'export' && <ExportPanel review={review} />}
    </main>
  )
}
