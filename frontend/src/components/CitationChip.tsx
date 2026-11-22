import type { Paper } from '../api/types'
import { shortAuthors } from '../lib/format'
import { LinkIcon } from './icons'

/**
 * A `[n]` citation marker rendered as a highlighter chip. On hover it shows a
 * preview index-card with the paper's title, authors, year and arXiv link.
 * When the referenced paper is known, the chip itself links to the arXiv page.
 */
export function CitationChip({ ref, paper }: { ref: number; paper?: Paper }) {
  const inner = (
    <span className="inline-flex items-center rounded bg-[#fef08a] px-1.5 py-0.5 font-mono text-xs font-bold leading-none text-slate-900 ring-1 ring-inset ring-[#fde047] transition group-hover:brightness-95">
      [{ref}]
    </span>
  )

  return (
    <span className="group relative inline-flex align-middle">
      {paper ? (
        <a
          href={paper.url_abs}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex"
          aria-label={`Open paper ${ref}: ${paper.title}`}
        >
          {inner}
        </a>
      ) : (
        inner
      )}

      {paper && (
        <span className="pointer-events-none absolute bottom-full left-1/2 z-40 mb-2 hidden w-72 -translate-x-1/2 group-hover:block">
          <span className="block rounded-lg border-[1.5px] border-slate-900 bg-white p-3 shadow-[4px_6px_0px_0px_rgba(15,23,42,0.14)]">
            <span className="mb-1 block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              REF {ref} · arXiv:{paper.arxiv_id}
            </span>
            <span className="block text-sm font-semibold leading-snug text-slate-900">{paper.title}</span>
            <span className="mt-1 block text-xs text-slate-500">
              {shortAuthors(paper.authors)} · {paper.year}
            </span>
            <span className="mt-2 inline-flex items-center gap-1.5 font-mono text-[11px] font-medium text-slate-700">
              <LinkIcon className="h-3 w-3" /> arxiv.org/abs/{paper.arxiv_id}
            </span>
          </span>
        </span>
      )}
    </span>
  )
}
