// API contracts. Mirrors DESIGN.md §4 and backend/app/models/schemas.py EXACTLY.
// If you change anything here, change the backend schemas, the mocks and DESIGN.md too.

// ---------- §4.1 Request / Job ----------
export interface ReviewRequest {
  topic: string // 3–200 chars after trimming
  max_papers?: number // 4–12, default 8
  year_from?: number | null
}

export interface JobCreated {
  job_id: string
  status: 'queued'
}

// ---------- §4.2 SSE event ----------
export type Stage =
  | 'planning'
  | 'searching'
  | 'ranking'
  | 'extracting'
  | 'synthesizing'
  | 'verifying'
  | 'indexing'
  | 'done'
  | 'error'

export type EventStatus = 'started' | 'progress' | 'completed' | 'failed' | 'skipped'

export type Provider = 'groq' | 'gemini' | 'cache'

export interface Progress {
  current: number
  total: number
}

export interface StageEvent {
  job_id: string
  stage: Stage
  status: EventStatus
  message: string
  progress?: Progress
  elapsed_ms: number
  /** model id -> cumulative tokens for this stage */
  tokens?: Record<string, number>
  provider?: Provider
}

// ---------- §4.3 Review result ----------
export type FulltextStatus = 'pending' | 'indexed' | 'abstract_only' | 'failed'
export type ReviewStatus = 'running' | 'done' | 'error'

export interface Paper {
  ref: number
  arxiv_id: string
  title: string
  authors: string[]
  year: number
  published: string // YYYY-MM-DD
  primary_category: string
  abstract: string
  url_abs: string
  url_pdf: string
  relevance: number
  fulltext_status: FulltextStatus
}

export interface Metric {
  name: string
  value: string
}

export interface Extraction {
  ref: number
  problem: string
  method: string
  datasets: string[]
  metrics: Metric[]
  key_result: string
  limitations: string
}

export interface WeakClaim {
  sentence: string
  ref: number
  score: number
}

export interface Verification {
  citation_validity: number // 0..1
  invalid_refs: number[]
  weak_claims: WeakClaim[]
  uncited_sentences: number
}

export interface Stats {
  total_ms: number
  stage_ms: Record<string, number>
  tokens: Record<string, number>
  providers_used: Provider[]
  papers_considered: number
  papers_selected: number
}

export interface ReviewResult {
  job_id: string
  status: ReviewStatus
  topic: string
  created_at: string // ISO 8601, UTC
  queries: string[]
  papers: Paper[]
  extractions: Extraction[]
  review_md: string
  verification: Verification | null
  stats: Stats
  warnings: string[]
  qa_ready: boolean
}

// ---------- §4.4 Q&A ----------
export interface AskRequest {
  question: string // 3–500 chars
}

export interface QASource {
  ref: number
  arxiv_id: string
  page: number
  snippet: string
  score: number
}

export interface AskResponse {
  answer_md: string
  sources: QASource[]
}

// ---------- §4.5 Errors ----------
export type ErrorCode =
  | 'VALIDATION_ERROR'
  | 'NOT_FOUND'
  | 'NOT_READY'
  | 'RATE_LIMITED'
  | 'UPSTREAM_ERROR'
  | 'INTERNAL'

export interface ErrorResponse {
  error: { code: ErrorCode; message: string }
}

// ---------- §4.6 Misc ----------
export interface HealthResponse {
  status: 'ok'
  version: string
  env: 'dev' | 'prod'
  demo_mode: boolean
  providers: { groq: boolean; gemini: boolean }
}

export interface DemoTopicsResponse {
  topics: string[]
}

export type ExportFormat = 'md' | 'bib'
