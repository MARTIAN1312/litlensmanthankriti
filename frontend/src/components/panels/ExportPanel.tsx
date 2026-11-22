import type { ReviewResult } from '../../api/types'
import { shortAuthors } from '../../lib/format'
import { DownloadIcon, PrinterIcon } from '../icons'
import { GhostButton, IndexCard, InkButton, SectionLabel } from '../ui'

function sanitizeFilename(s: string): string {
  return s.replace(/[^\w]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60)
}

function buildMarkdown(review: ReviewResult): string {
  const lines: string[] = []
  lines.push(`# Literature Review — ${review.topic}`)
  lines.push('')
  lines.push(review.review_md)
  lines.push('')
  lines.push('## References')
  lines.push('')
  review.papers.forEach((p) => {
    lines.push(`${p.ref}. ${p.title} — ${shortAuthors(p.authors)} (${p.year}). arXiv:${p.arxiv_id}. ${p.url_abs}`)
  })
  return lines.join('\n')
}

function buildBibtex(review: ReviewResult): string {
  return review.papers
    .map((p) => {
      const authors = p.authors.join(' and ')
      return [
        `@article{litlens_ref${p.ref},`,
        `  author = {${authors}},`,
        `  title = {${p.title}},`,
        `  year = {${p.year}},`,
        `  eprint = {${p.arxiv_id}},`,
        '  archiveprefix = {arXiv},',
        '}',
      ].join('\n')
    })
    .join('\n\n')
}

function triggerDownload(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export function ExportPanel({ review }: { review: ReviewResult }) {
  const base = sanitizeFilename(review.topic)
  const exportMd = () => triggerDownload(`${base}-litlens.md`, buildMarkdown(review), 'text/markdown;charset=utf-8')
  const exportBib = () => triggerDownload(`${base}-litlens.bib`, buildBibtex(review), 'application/x-bibtex;charset=utf-8')
  const print = () => window.print()

  return (
    <div className="space-y-5">
      <div>
        <SectionLabel>Export</SectionLabel>
        <p className="mt-1 text-sm text-mut">Download the review as Markdown or BibTeX, or print a PDF.</p>
      </div>

      <IndexCard className="grid grid-cols-1 gap-3 p-5 sm:grid-cols-3">
        <div className="rounded-xl border border-edge bg-field p-4">
          <div className="font-mono text-[11px] font-semibold uppercase tracking-wide text-faint">Markdown</div>
          <p className="mt-1 text-xs text-faint">Review text with citation markers, ready for your notes.</p>
          <InkButton onClick={exportMd} className="mt-3 w-full">
            <DownloadIcon className="h-4 w-4" /> .md
          </InkButton>
        </div>

        <div className="rounded-xl border border-edge bg-field p-4">
          <div className="font-mono text-[11px] font-semibold uppercase tracking-wide text-faint">BibTeX</div>
          <p className="mt-1 text-xs text-faint">Citation entries for your reference manager.</p>
          <InkButton onClick={exportBib} className="mt-3 w-full">
            <DownloadIcon className="h-4 w-4" /> .bib
          </InkButton>
        </div>

        <div className="rounded-xl border border-edge bg-field p-4">
          <div className="font-mono text-[11px] font-semibold uppercase tracking-wide text-faint">Print</div>
          <p className="mt-1 text-xs text-faint">Save the workspace as a PDF via your browser.</p>
          <GhostButton onClick={print} className="mt-3 w-full">
            <PrinterIcon className="h-4 w-4" /> Print
          </GhostButton>
        </div>
      </IndexCard>
    </div>
  )
}
