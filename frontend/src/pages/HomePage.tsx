import { useState } from 'react'
import { ArrowRightIcon, SparkleIcon } from '../components/icons'
import { InkButton, Spinner } from '../components/ui'

const DECKS = [
  { value: 4, label: '4 Quick' },
  { value: 8, label: '8 Standard' },
  { value: 12, label: '12 Deep' },
]

const PITCH =
  'Synthesize recent arXiv preprints into a cited review with verified references, extraction tables, and Q&A.'

export function HomePage({
  demoTopics,
  onStart,
  busy,
}: {
  demoTopics: string[]
  onStart: (topic: string, deck: number) => void
  busy: boolean
}) {
  const [topic, setTopic] = useState('')
  const [deck, setDeck] = useState(8)
  const trimmed = topic.trim()
  const canRun = trimmed.length >= 3 && trimmed.length <= 200 && !busy
  const tooLong = trimmed.length > 200

  const submit = () => {
    if (canRun) onStart(trimmed, deck)
  }

  return (
    <main className="mx-auto w-full max-w-3xl px-5 py-10 text-center">
      <div className="space-y-2">
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 md:text-4xl">
          What would you like to explore today?
        </h1>
        <p className="text-sm text-slate-500">{PITCH}</p>
      </div>

      <div className="mt-8 rounded-xl border-[1.5px] border-slate-300 bg-white p-4 text-left shadow-[2px_3px_0px_0px_rgba(15,23,42,0.08)]">
        <textarea
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          rows={3}
          placeholder="e.g. Graph neural networks for molecular property prediction and drug discovery…"
          className="w-full resize-none bg-transparent text-base text-slate-800 outline-none placeholder:text-slate-400"
        />
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3">
          <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1 text-xs">
            {DECKS.map((d) => (
              <button
                key={d.value}
                type="button"
                onClick={() => setDeck(d.value)}
                className={`rounded px-2.5 py-1 font-medium transition ${
                  deck === d.value ? 'bg-white font-semibold text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>

          <InkButton onClick={submit} disabled={busy}>
            {busy ? <Spinner className="h-4 w-4 border-slate-400 border-t-white" /> : <span>Run Review</span>}
            {!busy && <ArrowRightIcon className="h-4 w-4" />}
          </InkButton>
        </div>
        {tooLong && <p className="mt-2 text-xs text-[#b91c1c]">Topic is too long (max 200 characters).</p>}
      </div>

      <div className="mt-6">
        <p className="font-mono text-[11px] font-semibold uppercase tracking-widest text-slate-400">
          try a demo topic
        </p>
        <div className="mt-3 flex flex-wrap justify-center gap-2">
          {demoTopics.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTopic(t)}
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:-translate-y-px hover:border-slate-900 hover:text-slate-900"
            >
              <SparkleIcon className="h-3 w-3 text-[#ca8a04]" />
              {t}
            </button>
          ))}
        </div>
      </div>
    </main>
  )
}
