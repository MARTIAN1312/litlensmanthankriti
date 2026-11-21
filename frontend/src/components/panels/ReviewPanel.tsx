import type { ReviewResult, Paper } from '../../api/types'
import { leadFinding, percent01, shortAuthors } from '../../lib/format'
import type { ViewMode } from '../TopBar'
import { MarkdownReview } from '../MarkdownReview'
import { AlertIcon, LinkIcon, SparkleIcon } from '../icons'
import { Chip, Badge, IndexCard, SectionLabel } from '../ui'

function KeyFinding({ review }: { review: ReviewResult }) {
  return (
    <div className="rounded-xl border border-amber-200/80 bg-[#fef08a]/30 p-4">
      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-900">
        <SparkleIcon className="h-4 w-4" />
        Key synthesis finding
      </div>
      <p className="mt-2 text-sm leading-relaxed text-slate-800">{leadFinding(review.review_md)}</p>
    </div>
  )
}

function WeakClaims({ review }: { review: ReviewResult }) {
  const claims = review.verification?.weak_claims ?? []
  if (claims.length === 0) return null
  return (
    <div className="rounded-xl border-l-4 border-[#fb7185] bg-[#fca5a5]/15 p-4">
      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#b91c1c]">
        <AlertIcon className="h-4 w-4" /> Weakly supported claims
      </div>
      <ul className="mt-2 space-y-2">
        {claims.map((c, i) => (
          <li key={i} className="text-sm text-slate-700">
            <span className="mr-1 font-mono text-xs font-bold text-[#b91c1c]">[{c.ref}]</span>
            {c.sentence}
            <span className="ml-2 font-mono text-[11px] text-slate-500">support {percent01(c.score)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function GroundingTable({ review }: { review: ReviewResult }) {
  const byRef = new Map(review.papers.map((p) => [p.ref, p]))
  const rows = review.extractions.map((e) => ({ e, paper: byRef.get(e.ref) }))
  return (
    <IndexCard className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">
        <span className="font-mono text-xs font-semibold text-slate-700">Grounding verification summary</span>
        <span className="font-mono text-[11px] text-slate-400">{rows.length} studies</span>
      </div>
      <div className="divide-y divide-slate-100 text-sm">
        {rows.map(({ e, paper }) => (
          <div key={e.ref} className="flex flex-wrap items-center justify-between gap-2 p-3">
            <div>
              <span className="font-bold text-slate-900">[{e.ref}] {paper?.title ?? 'Paper'}</span>
              <p className="mt-0.5 text-xs text-slate-500">
                {paper ? `${shortAuthors(paper.authors)} (${paper.year})` : ''} · {e.method}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Chip tone="mint" dot>extracted</Chip>
              <span className="font-mono text-xs text-slate-600">{e.key_result}</span>
            </div>
          </div>
        ))}
        {rows.length === 0 && <p className="p-4 text-sm text-slate-400">No extraction data yet.</p>}
      </div>
    </IndexCard>
  )
}

function RunParams({ review }: { review: ReviewResult }) {
  const s = review.stats
  const indexed = review.papers.filter((p) => p.fulltext_status === 'indexed').length
  return (
    <IndexCard className="p-4">
      <div className="flex items-center justify-between border-b border-slate-100 pb-2">
        <span className="font-mono text-xs font-semibold text-slate-500">Run ID: {review.job_id.slice(0, 12)}</span>
        <span className="rounded px-2 py-0.5 font-mono text-xs font-bold text-[#166534] ring-1 ring-inset ring-[#4ade80] bg-[#86efac]/50">
          {percent01(review.verification?.citation_validity ?? 0)} corroborated
        </span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
        <div>
          <div className="text-slate-400">Selected</div>
          <div className="font-semibold text-slate-800">{s.papers_selected} of {s.papers_considered}</div>
        </div>
        <div>
          <div className="text-slate-400">Full text</div>
          <div className="font-semibold text-slate-800">{indexed} indexed</div>
        </div>
        <div>
          <div className="text-slate-400">Providers</div>
          <div className="font-semibold text-slate-800">{(s.providers_used ?? ['—']).join(' · ')}</div>
        </div>
        <div>
          <div className="text-slate-400">Time</div>
          <div className="font-semibold text-slate-800">{Math.round(s.total_ms / 1000)}s</div>
        </div>
      </div>
    </IndexCard>
  )
}

function BenchmarkMatrix({ review }: { review: ReviewResult }) {
  const byRef = new Map(review.papers.map((p) => [p.ref, p]))
  return (
    <IndexCard className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">
        <span className="font-mono text-xs font-semibold text-slate-800">Empirical benchmark matrix</span>
        <span className="font-normal text-slate-400">extracted metrics</span>
      </div>
      <table className="w-full text-left text-xs">
        <thead className="border-b border-slate-100 bg-slate-50/60 text-slate-500">
          <tr>
            <th className="p-3 font-mono font-semibold">Paper</th>
            <th className="p-3 font-mono font-semibold">Method</th>
            <th className="p-3 font-mono font-semibold">Reported</th>
            <th className="p-3 font-mono font-semibold">Rel.</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {review.extractions.map((e) => {
            const p = byRef.get(e.ref)
            const metric = e.metrics[0]
            return (
              <tr key={e.ref}>
                <td className="p-3 font-semibold text-slate-900">
                  [{e.ref}] {shortAuthors(p?.authors ?? [])}
                </td>
                <td className="p-3 text-slate-600">{e.method}</td>
                <td className="p-3 font-mono text-[#166534]">
                  {metric ? `${metric.name}: ${metric.value}` : e.key_result}
                </td>
                <td className="p-3 font-semibold text-[#166534]">{percent01(p?.relevance ?? 0)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </IndexCard>
  )
}

function ChunkInspector({ papers }: { papers: Paper[] }) {
  const top = [...papers].sort((a, b) => b.relevance - a.relevance).slice(0, 4)
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <SectionLabel>Retrieved source chunks &amp; PDF inspector</SectionLabel>
        <Badge>{top.length} chunks</Badge>
      </div>
      {top.map((p) => (
        <IndexCard key={p.ref} className="p-4">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-bold text-slate-900">[{p.ref}] {shortAuthors(p.authors)}</span>
            <span className="rounded bg-[#86efac]/50 px-2 py-0.5 font-mono text-[10px] font-semibold text-[#166534] ring-1 ring-inset ring-[#4ade80]">
              {(p.relevance * 100).toFixed(0)}% match
            </span>
          </div>
          <p className="mt-1 font-mono text-[10px] text-slate-400">arXiv:{p.arxiv_id} · {p.primary_category}</p>
          <p className="mt-2 rounded-lg border-l-2 border-[#fde047] bg-[#fef08a]/25 p-3 text-xs leading-relaxed text-slate-700">
            {p.abstract}
          </p>
          <a href={p.url_abs} target="_blank" rel="noopener noreferrer" className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900">
            <LinkIcon className="h-3.5 w-3.5" /> Open arXiv
          </a>
        </IndexCard>
      ))}
    </div>
  )
}

export function ReviewPanel({ review, mode }: { review: ReviewResult; mode: ViewMode }) {
  if (mode === 'detailed') {
    return (
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <section className="space-y-6 lg:col-span-7">
          <RunParams review={review} />
          <BenchmarkMatrix review={review} />
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <SectionLabel className="mb-3 block">Synthesized monograph</SectionLabel>
            <MarkdownReview markdown={review.review_md} papers={review.papers} />
            <WeakClaims review={review} />
          </div>
        </section>
        <aside className="lg:col-span-5">
          <ChunkInspector papers={review.papers} />
        </aside>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <KeyFinding review={review} />
      <IndexCard className="p-5">
        <MarkdownReview markdown={review.review_md} papers={review.papers} />
      </IndexCard>
      <WeakClaims review={review} />
      <GroundingTable review={review} />
    </div>
  )
}
