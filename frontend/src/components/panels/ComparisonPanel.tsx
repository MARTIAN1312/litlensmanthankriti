import { useMemo, useState } from 'react'
import type { ReviewResult } from '../../api/types'
import { TableIcon } from '../icons'
import { SectionLabel } from '../ui'

type Row = {
  ref: number
  title: string
  method: string
  datasets: string
  key_result: string
  limitations: string
}

type ColKey = 'ref' | 'title' | 'method' | 'datasets' | 'key_result' | 'limitations'

const COLS: { key: ColKey; label: string }[] = [
  { key: 'ref', label: 'Ref' },
  { key: 'title', label: 'Paper' },
  { key: 'method', label: 'Method' },
  { key: 'datasets', label: 'Dataset(s)' },
  { key: 'key_result', label: 'Key Result' },
  { key: 'limitations', label: 'Limitations' },
]

function isNotReported(v: string) {
  return v.trim().toLowerCase() === 'not reported' || v.trim() === ''
}

export function ComparisonPanel({ review }: { review: ReviewResult }) {
  const [sortKey, setSortKey] = useState<ColKey>('ref')
  const [asc, setAsc] = useState(true)

  const rows = useMemo<Row[]>(() => {
    const byRef = new Map(review.papers.map((p) => [p.ref, p]))
    return review.extractions.map((e) => ({
      ref: e.ref,
      title: byRef.get(e.ref)?.title ?? `[${e.ref}]`,
      method: e.method,
      datasets: e.datasets.join(', '),
      key_result: e.key_result,
      limitations: e.limitations,
    }))
  }, [review])

  const sorted = useMemo(() => {
    const copy = [...rows]
    copy.sort((a, b) => {
      let cmp = 0
      if (sortKey === 'ref') cmp = a.ref - b.ref
      else cmp = String(a[sortKey]).localeCompare(String(b[sortKey]))
      return asc ? cmp : -cmp
    })
    return copy
  }, [rows, sortKey, asc])

  const toggle = (key: ColKey) => {
    if (key === sortKey) setAsc((v) => !v)
    else {
      setSortKey(key)
      setAsc(true)
    }
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <SectionLabel className="inline-flex items-center gap-2">
          <TableIcon className="h-3.5 w-3.5 text-amb-dot" /> Extraction table
        </SectionLabel>
        <span className="font-mono text-[11px] text-faint">{rows.length} studies</span>
      </div>

      <div className="overflow-x-auto rounded-xl border border-edge bg-card">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-edge bg-field">
              {COLS.map((c) => (
                <th key={c.key} className="whitespace-nowrap px-3 py-2.5 text-left">
                  <button type="button" onClick={() => toggle(c.key)} className="inline-flex items-center gap-1 font-mono text-[11px] font-semibold uppercase tracking-wider text-faint hover:text-amb">
                    {c.label}
                    {sortKey === c.key ? <span className="text-amb">{asc ? '↑' : '↓'}</span> : <span className="text-faint">↕</span>}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-edge2">
            {sorted.map((r) => (
              <tr key={r.ref} className="transition hover:bg-amb-soft/30">
                <td className="whitespace-nowrap px-3 py-2.5 font-mono text-xs font-bold text-amb">[{r.ref}]</td>
                <td className="max-w-xs px-3 py-2.5">
                  <span className="font-semibold text-ink">{r.title}</span>
                </td>
                <td className="px-3 py-2.5 text-mut">{r.method}</td>
                <td className="px-3 py-2.5 text-mut">{r.datasets}</td>
                <td className={`px-3 py-2.5 font-medium ${isNotReported(r.key_result) ? 'italic text-faint' : 'text-txt'}`}>
                  {r.key_result}
                </td>
                <td className={`px-3 py-2.5 ${isNotReported(r.limitations) ? 'italic text-faint' : 'text-mut'}`}>
                  {r.limitations}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
