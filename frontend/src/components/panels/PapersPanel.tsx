import { useState } from 'react'
import type { FulltextStatus, Paper, ReviewResult } from '../../api/types'
import { percent01, shortAuthors } from '../../lib/format'
import { LinkIcon } from '../icons'
import { Badge, Chip, IndexCard, SectionLabel } from '../ui'

function statusTone(status: FulltextStatus): 'mint' | 'sky' | 'coral' | 'yellow' {
  switch (status) {
    case 'indexed':
      return 'mint'
    case 'abstract_only':
      return 'sky'
    case 'failed':
      return 'coral'
    default:
      return 'yellow'
  }
}

function statusLabel(status: FulltextStatus): string {
  switch (status) {
    case 'indexed':
      return 'Full text indexed'
    case 'abstract_only':
      return 'Abstract only'
    case 'failed':
      return 'Full text failed'
    default:
      return 'Pending'
  }
}

function PaperCard({ paper }: { paper: Paper }) {
  const [open, setOpen] = useState(false)
  return (
    <IndexCard className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold text-slate-400">[{paper.ref}]</span>
            <Chip tone={statusTone(paper.fulltext_status)} dot>
              {statusLabel(paper.fulltext_status)}
            </Chip>
            <Badge>{paper.primary_category}</Badge>
          </div>
          <h3 className="mt-2 text-sm font-bold leading-snug text-slate-900">{paper.title}</h3>
          <p className="mt-1 text-xs text-slate-500">
            {shortAuthors(paper.authors)} · {paper.year} · arXiv:{paper.arxiv_id}
          </p>
        </div>
        <div className="w-28 shrink-0">
          <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-wide text-slate-400">
            <span>relevance</span>
            <span className="font-semibold text-slate-600">{percent01(paper.relevance)}</span>
          </div>
          <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-slate-900"
              style={{ width: `${Math.round(paper.relevance * 100)}%` }}
            />
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="mt-3 text-xs font-medium text-slate-500 underline decoration-dotted underline-offset-2 hover:text-slate-900"
      >
        {open ? 'Hide abstract' : 'Show abstract'}
      </button>
      {open && <p className="mt-2 text-xs leading-relaxed text-slate-600">{paper.abstract}</p>}

      <div className="mt-3 flex items-center gap-4 border-t border-dashed border-slate-200 pt-3">
        <a href={paper.url_abs} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900">
          <LinkIcon className="h-3.5 w-3.5" /> Abstract
        </a>
        {paper.fulltext_status !== 'failed' && (
          <a href={paper.url_pdf} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900">
            <LinkIcon className="h-3.5 w-3.5" /> PDF
          </a>
        )}
      </div>
    </IndexCard>
  )
}

export function PapersPanel({ review }: { review: ReviewResult }) {
  const sorted = [...review.papers].sort((a, b) => b.relevance - a.relevance)
  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <SectionLabel>Pinned papers</SectionLabel>
        <span className="font-mono text-[11px] text-slate-400">ranked by relevance</span>
      </div>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {sorted.map((p) => (
          <PaperCard key={p.ref} paper={p} />
        ))}
      </div>
    </div>
  )
}
