// M1 placeholder: proves the wiring (mocks or live API) works.
// The real screens (DESIGN §6) are built by the frontend teammate.

import { useEffect, useState } from 'react'
import { ApiError, getHealth, USE_MOCKS } from './api/client'
import { subscribeToJob } from './api/sse'
import type { HealthResponse, StageEvent } from './api/types'

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [events, setEvents] = useState<StageEvent[]>([])

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e: unknown) => setError(e instanceof ApiError ? e.message : 'Unexpected error'))
  }, [])

  const replay = () => {
    setEvents([])
    subscribeToJob('mock', { onEvent: (e) => setEvents((prev) => [...prev, e]) })
  }

  return (
    <main className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="font-serif text-4xl text-slate-50">LitLens</h1>
      <p className="mt-2 text-slate-400">
        A cited literature review from live arXiv papers in about a minute.
      </p>

      <section className="mt-8 rounded-lg border border-slate-800 bg-slate-900 p-4 text-sm">
        <h2 className="mb-2 font-semibold text-slate-200">
          Backend status {USE_MOCKS && <span className="text-amber-400">(mock mode)</span>}
        </h2>
        {error && <p className="text-red-400">{error}</p>}
        {!error && !health && <p className="text-slate-400">Checking…</p>}
        {health && (
          <ul className="space-y-1 text-slate-300">
            <li>Version {health.version} · env {health.env}</li>
            <li>Groq: {health.providers.groq ? '✓ configured' : '✗ missing key'}</li>
            <li>Gemini fallback: {health.providers.gemini ? '✓ configured' : '– disabled'}</li>
            <li>Demo mode: {health.demo_mode ? 'on' : 'off'}</li>
          </ul>
        )}
      </section>

      {USE_MOCKS && (
        <section className="mt-6 text-sm">
          <button
            type="button"
            onClick={replay}
            className="rounded-md bg-indigo-500 px-3 py-1.5 font-medium text-white hover:bg-indigo-400"
          >
            Replay mock pipeline events
          </button>
          <ol className="mt-4 space-y-1 font-mono text-xs text-slate-400">
            {events.map((e, i) => (
              <li key={i}>
                {(e.elapsed_ms / 1000).toFixed(1)}s · {e.stage} · {e.status} · {e.message}
              </li>
            ))}
          </ol>
        </section>
      )}
    </main>
  )
}
