import { useCallback, useEffect, useRef, useState } from 'react'
import { createReview, getDemoTopics, getReview } from './api/client'
import { subscribeToJob } from './api/sse'
import type { ReviewResult, StageEvent } from './api/types'
import { TopBar, type ViewMode } from './components/TopBar'
import { HomePage } from './pages/HomePage'
import { ResultsPage } from './pages/ResultsPage'
import { RunPage } from './pages/RunPage'

type Phase = 'home' | 'running' | 'results'

const FOOTER = 'LitLens Study Desk · autonomous arXiv preprint extraction & citation-verified review builder'

export default function App() {
  const [phase, setPhase] = useState<Phase>('home')
  const [jobId, setJobId] = useState<string | null>(null)
  const [topic, setTopic] = useState('')
  const [events, setEvents] = useState<StageEvent[]>([])
  const [review, setReview] = useState<ReviewResult | null>(null)
  const [mode, setMode] = useState<ViewMode>('minimalist')
  const [demoTopics, setDemoTopics] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)

  const closeStream = useRef<(() => void) | null>(null)

  useEffect(() => {
    let alive = true
    getDemoTopics()
      .then((d) => alive && setDemoTopics(d.topics))
      .catch(() => {
        /* non-fatal */
      })
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    return () => {
      closeStream.current?.()
    }
  }, [])

  const goHome = useCallback(() => {
    closeStream.current?.()
    closeStream.current = null
    setRunError(null)
    setPhase('home')
  }, [])

  const start = useCallback(
    async (t: string, deck: number) => {
      setBusy(true)
      setRunError(null)
      setEvents([])
      setReview(null)
      setTopic(t)
      try {
        const job = await createReview({ topic: t, max_papers: deck })
        setJobId(job.job_id)
        setPhase('running')

        closeStream.current = subscribeToJob(job.job_id, {
          onEvent: (e) => setEvents((prev) => [...prev, e]),
          onEnd: async () => {
            try {
              const result = await getReview(job.job_id)
              setReview(result)
              setPhase('results')
            } catch {
              setRunError('Could not load the finished review.')
              setPhase('home')
            }
          },
          onError: (message) => {
            setRunError(message)
            setPhase('home')
          },
        })
      } catch (e) {
        setRunError(e instanceof Error ? e.message : 'Failed to start the review.')
        setPhase('home')
      } finally {
        setBusy(false)
      }
    },
    [],
  )

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar mode={mode} onModeChange={setMode} onHome={goHome} />

      <div className="flex-1">
        {phase === 'home' && (
          <>
            {runError && (
              <div className="mx-auto mt-4 w-full max-w-3xl px-5">
                <p className="rounded-lg border-l-4 border-[#fb7185] bg-[#fca5a5]/20 px-4 py-3 text-sm text-[#b91c1c]">
                  {runError}
                </p>
              </div>
            )}
            <HomePage demoTopics={demoTopics} onStart={start} busy={busy} />
          </>
        )}

        {phase === 'running' && <RunPage topic={topic} events={events} />}

        {phase === 'results' && review && <ResultsPage review={review} mode={mode} />}
      </div>

      <footer className="border-t border-slate-200 px-5 py-4 text-center text-xs text-slate-400">
        {FOOTER} · job {jobId ? jobId.slice(0, 8) : '—'}
      </footer>
    </div>
  )
}
