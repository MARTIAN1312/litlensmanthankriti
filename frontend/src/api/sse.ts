// Live progress stream (DESIGN §4.2). In mock mode, replays src/mocks/events.json
// using each event's elapsed_ms (sped up so a mock run takes a few seconds).

import eventsMock from '../mocks/events.json'
import { USE_MOCKS } from './client'
import type { StageEvent } from './types'

export interface StreamHandlers {
  onEvent: (event: StageEvent) => void
  /** Called once indexing finishes (or the job errors). The stream is closed by then. */
  onEnd?: () => void
  onError?: (message: string) => void
}

/** Subscribe to a job's events. Returns a function that closes the stream. */
export function subscribeToJob(jobId: string, handlers: StreamHandlers): () => void {
  return USE_MOCKS ? replayMock(handlers) : openEventSource(jobId, handlers)
}

function isFinal(e: StageEvent): boolean {
  if (e.stage === 'error') return true
  // Indexing continues after "done", so keep listening until it finishes (DESIGN §4.2).
  return e.stage === 'indexing' && (e.status === 'completed' || e.status === 'failed')
}

function openEventSource(jobId: string, h: StreamHandlers): () => void {
  // EventSource reconnects automatically; the backend replays history to late subscribers.
  const source = new EventSource(`/api/reviews/${encodeURIComponent(jobId)}/events`)
  let closed = false
  const close = () => {
    if (!closed) {
      closed = true
      source.close()
    }
  }

  source.addEventListener('stage', (msg) => {
    let event: StageEvent
    try {
      event = JSON.parse((msg as MessageEvent<string>).data) as StageEvent
    } catch {
      return
    }
    h.onEvent(event)
    if (isFinal(event)) {
      close()
      h.onEnd?.()
    }
  })

  source.onerror = () => {
    // CLOSED means the browser gave up reconnecting.
    if (source.readyState === EventSource.CLOSED && !closed) {
      closed = true
      h.onError?.('Lost connection to the progress stream.')
    }
  }

  return close
}

const MOCK_SPEEDUP = 8

function replayMock(h: StreamHandlers): () => void {
  const events = eventsMock as StageEvent[]
  const timers = events.map((event, i) =>
    setTimeout(() => {
      h.onEvent(event)
      if (i === events.length - 1) h.onEnd?.()
    }, event.elapsed_ms / MOCK_SPEEDUP),
  )
  return () => timers.forEach(clearTimeout)
}
