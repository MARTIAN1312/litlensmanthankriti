import type { ReviewResult } from '../api/types'
import { formatMs, percent01, totalTokens } from '../lib/format'
import { ClockIcon, LayersIcon, ShieldCheckIcon, SparkleIcon, TargetIcon } from './icons'
import { Badge } from './ui'

export function StatsBar({ review }: { review: ReviewResult }) {
  const s = review.stats
  const providerNames = (s.providers_used ?? []).map((p) => p).join(' · ')
  const validity = review.verification ? percent01(review.verification.citation_validity) : null

  return (
    <div className="rounded-lg border-[1.5px] border-slate-200 bg-white/80 p-3">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <span className="inline-flex items-center gap-1.5 font-mono text-[12px] font-medium text-slate-600">
          <TargetIcon className="h-3.5 w-3.5" />
          {s.papers_selected}/{s.papers_considered} papers
        </span>
        <span className="inline-flex items-center gap-1.5 font-mono text-[12px] font-medium text-slate-600">
          <LayersIcon className="h-3.5 w-3.5" />
          {totalTokens(s.tokens).toLocaleString()} tokens
        </span>
        <span className="inline-flex items-center gap-1.5 font-mono text-[12px] font-medium text-slate-600">
          <ClockIcon className="h-3.5 w-3.5" />
          {formatMs(s.total_ms)}
        </span>
        {providerNames && <Badge>{providerNames}</Badge>}
        {validity !== null && (
          <Badge className="border-[#4ade80] bg-[#86efac]/50 text-[#166534]">
            <ShieldCheckIcon className="h-3 w-3" /> {validity} citations verified
          </Badge>
        )}
        <span className="ml-auto inline-flex items-center gap-1.5 font-mono text-[12px] font-medium text-slate-500">
          <SparkleIcon className="h-3.5 w-3.5 text-[#ca8a04]" />
          {review.qa_ready ? 'Q&A ready' : 'Q&A indexing…'}
        </span>
      </div>
    </div>
  )
}
