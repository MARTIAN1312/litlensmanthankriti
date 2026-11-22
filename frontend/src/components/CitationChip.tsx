import type { Paper } from '../api/types'
import { shortAuthors } from '../lib/format'
import { LinkIcon } from './icons'

/**
 * A `[n]` citation marker rendered as an accent chip. On hover it shows a
 * preview card with the paper's title, authors, year and arXiv link.
 */
export function CitationChip({ ref, paper }: { ref: number; paper?: Paper }) {
  const inner = (
    <span className="inline-flex items-center rounded bg-amb-soft px-1.5 py-0.5 font-mono text-xs font-bold leading-none text-amb ring-1 ring-inset ring-amb-line transition group-hover:bg-amb-soft/70">
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
          <span className="block rounded-xl border border-edge bg-card2 p-3 shadow-book-overlay">
            <span className="mb-1 block font-mono text-[10px] font-semibold uppercase tracking-wider text-faint">
              REF {ref} · arXiv:{paper.arxiv_id}
            </span>
            <span className="block text-sm font-semibold leading-snug text-ink">{paper.title}</span>
            <span className="mt-1 block text-xs text-mut">
              {shortAuthors(paper.authors)} · {paper.year}
            </span>
            <span className="mt-2 inline-flex items-center gap-1.5 font-mono text-[11px] font-medium text-amb">
              <LinkIcon className="h-3 w-3" /> arxiv.org/abs/{paper.arxiv_id}
            </span>
          </span>
        </span>
      )}
    </span>
  )
}
