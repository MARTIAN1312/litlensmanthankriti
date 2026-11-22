import type { ReactNode } from 'react'
import type { Stage, StageEvent } from '../api/types'
import { formatMs, totalTokens } from '../lib/format'
import { BotIcon, CheckIcon, DotsIcon, FlaskIcon, LayersIcon, PenIcon, SearchIcon, ShieldCheckIcon, SparkleIcon, TableIcon, XIcon } from './icons'
import { Chip, ProgressBar, Spinner } from './ui'

type StageMeta = {
  key: Stage
  label: string
  hint: string
  icon: ReactNode
}

const STAGES: StageMeta[] = [
  { key: 'planning', label: 'Plan search', hint: 'Design arXiv queries', icon: <PenIcon className="h-4 w-4" /> },
  { key: 'searching', label: 'Search arXiv', hint: 'Fetch candidate papers', icon: <SearchIcon className="h-4 w-4" /> },
  { key: 'ranking', label: 'Rank papers', hint: 'Semantic relevance', icon: <LayersIcon className="h-4 w-4" /> },
  { key: 'extracting', label: 'Extract facts', hint: 'Structured per-paper facts', icon: <FlaskIcon className="h-4 w-4" /> },
  { key: 'synthesizing', label: 'Synthesize review', hint: 'Write the review', icon: <PenIcon className="h-4 w-4" /> },
  { key: 'verifying', label: 'Verify citations', hint: 'Ground every claim', icon: <ShieldCheckIcon className="h-4 w-4" /> },
  { key: 'indexing', label: 'Index full text', hint: 'Build Q&A corpus', icon: <TableIcon className="h-4 w-4" /> },
]

function lastEvent(events: StageEvent[], stage: Stage): StageEvent | undefined {
  return [...events].reverse().find((e) => e.stage === stage)
}

function stateFor(events: StageEvent[], stage: Stage): 'pending' | 'active' | 'done' | 'error' {
  const last = lastEvent(events, stage)
  if (!last) return 'pending'
  if (last.status === 'completed') return 'done'
  if (last.status === 'failed' || last.status === 'skipped') return 'error'
  return 'active'
}

function durationFor(events: StageEvent[], stage: Stage): number {
  const mine = events.filter((e) => e.stage === stage)
  if (mine.length === 0) return 0
  const started = mine[0].elapsed_ms
  const ended = mine[mine.length - 1].elapsed_ms
  return ended - started
}

function StatusIcon({ state }: { state: 'pending' | 'active' | 'done' | 'error' }) {
  if (state === 'done') return <CheckIcon className="h-4 w-4 text-[#166534]" />
  if (state === 'error') return <XIcon className="h-4 w-4 text-[#b91c1c]" />
  if (state === 'active') return <Spinner className="h-4 w-4" />
  return <DotsIcon className="h-4 w-4 text-slate-300" />
}

export function AgentTimeline({ events }: { events: StageEvent[] }) {
  const finished = stateFor(events, 'done') === 'done'
  const failed = stateFor(events, 'error') === 'error'

  return (
    <div>
      <div className="flex items-center justify-between">
        <h2 className="inline-flex items-center gap-2 text-sm font-bold text-slate-900">
          <BotIcon className="h-4 w-4" /> Agent pipeline
        </h2>
        <Chip tone={failed ? 'coral' : finished ? 'mint' : 'sky'} dot>
          {failed ? 'Run failed' : finished ? 'Pipeline complete' : 'In progress'}
        </Chip>
      </div>

      <ol className="mt-4 space-y-2">
        {STAGES.map((stage, i) => {
          const state = stateFor(events, stage.key)
          const last = lastEvent(events, stage.key)
          const duration = durationFor(events, stage.key)
          const provider = last?.provider
          const tokens = last ? totalTokens(last.tokens) : 0
          return (
            <li key={stage.key} className="flex items-start gap-3">
              <div className="flex flex-col items-center">
                <span
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border-[1.5px] ${
                    state === 'done'
                      ? 'border-[#4ade80] bg-[#86efac]/60 text-[#166534]'
                      : state === 'error'
                        ? 'border-[#fb7185] bg-[#fca5a5]/60 text-[#b91c1c]'
                        : state === 'active'
                          ? 'border-slate-900 bg-[#fef08a] text-slate-900'
                          : 'border-slate-300 bg-white text-slate-400'
                  }`}
                >
                  {stage.icon}
                </span>
                {i < STAGES.length - 1 && <span className="my-1 w-px flex-1 bg-slate-300" />}
              </div>

              <div className={`flex-1 rounded-lg border-[1.5px] p-3 ${state === 'active' ? 'index-card--lift border-slate-900 bg-white' : 'border-slate-200 bg-white/70'}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-slate-900">{stage.label}</span>
                    <StatusIcon state={state} />
                  </div>
                  <div className="flex items-center gap-3 font-mono text-[11px] text-slate-500">
                    {last?.message && <span className="text-slate-600">{last.message}</span>}
                    {duration > 0 && <span>{formatMs(duration)}</span>}
                    {provider && <Chip tone="sky">{provider}</Chip>}
                    {tokens > 0 && <span>{tokens.toLocaleString()} tok</span>}
                  </div>
                </div>
                {last?.progress && <ProgressBar current={last.progress.current} total={last.progress.total} />}
                <p className="mt-1 text-xs text-slate-400">{stage.hint}</p>
              </div>
            </li>
          )
        })}
        <li className="flex items-start gap-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border-[1.5px] border-slate-900 bg-slate-900 text-white">
            <SparkleIcon className="h-4 w-4" />
          </span>
          <div className="flex-1 rounded-lg border-[1.5px] border-slate-900 bg-white p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold text-slate-900">Review ready</span>
              {!finished && <Spinner className="h-3.5 w-3.5" />}
            </div>
            <p className="mt-1 text-xs text-slate-400">Markdown + verified citations + Q&A corpus</p>
          </div>
        </li>
      </ol>
    </div>
  )
}
