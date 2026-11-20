// Typed API client. With VITE_USE_MOCKS=true every call returns the fixtures in src/mocks,
// so the UI can be built before the backend exists (DESIGN §6.3).

import askMock from '../mocks/ask.json'
import demoTopicsMock from '../mocks/demo-topics.json'
import healthMock from '../mocks/health.json'
import reviewMock from '../mocks/review.json'
import type {
  AskRequest,
  AskResponse,
  DemoTopicsResponse,
  ErrorCode,
  ErrorResponse,
  ExportFormat,
  HealthResponse,
  JobCreated,
  ReviewRequest,
  ReviewResult,
} from './types'

export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true'

/** Thrown for any non-2xx response; carries the backend error envelope (DESIGN §4.5). */
export class ApiError extends Error {
  readonly code: ErrorCode
  readonly status: number

  constructor(status: number, code: ErrorCode, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError(0, 'UPSTREAM_ERROR', 'Cannot reach the LitLens server. Is the backend running?')
  }
  if (!res.ok) {
    let body: ErrorResponse | undefined
    try {
      body = (await res.json()) as ErrorResponse
    } catch {
      /* not JSON */
    }
    throw new ApiError(
      res.status,
      body?.error?.code ?? 'INTERNAL',
      body?.error?.message ?? `Request failed (${res.status})`,
    )
  }
  return (await res.json()) as T
}

export function getHealth(): Promise<HealthResponse> {
  if (USE_MOCKS) return delay(150).then(() => healthMock as HealthResponse)
  return request<HealthResponse>('/api/health')
}

export function getDemoTopics(): Promise<DemoTopicsResponse> {
  if (USE_MOCKS) return delay(150).then(() => demoTopicsMock)
  return request<DemoTopicsResponse>('/api/demo-topics')
}

export function createReview(body: ReviewRequest): Promise<JobCreated> {
  if (USE_MOCKS) {
    return delay(300).then(() => ({ job_id: reviewMock.job_id, status: 'queued' as const }))
  }
  return request<JobCreated>('/api/reviews', { method: 'POST', body: JSON.stringify(body) })
}

export function getReview(jobId: string): Promise<ReviewResult> {
  if (USE_MOCKS) return delay(200).then(() => reviewMock as ReviewResult)
  return request<ReviewResult>(`/api/reviews/${encodeURIComponent(jobId)}`)
}

export function askQuestion(jobId: string, body: AskRequest): Promise<AskResponse> {
  if (USE_MOCKS) return delay(1200).then(() => askMock)
  return request<AskResponse>(`/api/reviews/${encodeURIComponent(jobId)}/ask`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

/** URL for an <a href download> link. Not available in mock mode. */
export function exportUrl(jobId: string, format: ExportFormat): string {
  return `/api/reviews/${encodeURIComponent(jobId)}/export?format=${format}`
}
