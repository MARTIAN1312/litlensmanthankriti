# Software Requirements Specification (SRS)
## LitLens — Multi-Agent AI Literature Review Assistant

| Field | Value |
|---|---|
| Version | 1.0 |
| Date | 2026-11-20 |
| Project type | College group project (3 members), 3-day build |
| Lead / Backend | Ashwin Kumar |
| Frontend | [Member 2 — React] |
| Evaluation, Docs & Presentation | [Member 3] |

---

## 1. Introduction

### 1.1 Purpose
This document specifies the requirements for **LitLens**, a web application that turns a research topic into a cited literature review in about a minute. It is the single source of truth for scope, features, constraints and acceptance criteria. Read it together with `DESIGN.md` (how it's built) and `SECURITY.md` (security rules).

### 1.2 Problem Statement
Before writing a paper, a thesis or a final-year project, researchers must read the existing work on their topic and write a **literature review**: what has been tried, which methods and datasets were used, what results were achieved, and what is still unsolved. Doing this by hand takes days to weeks. General chatbots are unreliable for it because they **invent papers and citations**.

### 1.3 Solution Summary
LitLens runs a **multi-agent pipeline** over **real papers fetched live from arXiv**:
1. **Planner agent** expands the topic into search queries.
2. **Searcher agent** fetches candidate papers from the arXiv API.
3. **Ranker** scores relevance using local semantic embeddings and keeps the top N.
4. **Extractor agent** pulls structured facts (problem, method, dataset, results, limitations) from each paper.
5. **Synthesizer agent** writes a literature review in which every claim cites a real paper by number.
6. **Verifier** checks that each citation exists and that the cited paper supports the sentence (hallucination guard).
7. **RAG Q&A** answers follow-up questions from the **full text** of the selected papers, with page-level sources.

### 1.4 Scope
**In scope:** topic → review, comparison table, paper list, follow-up Q&A, Markdown/BibTeX/print export, live progress view, demo/offline mode, evaluation harness.

**Out of scope (v1):** user accounts or login, paywalled or non-arXiv sources, uploading your own PDFs, cloud deployment, mobile app, non-English papers, writing original research.

**Stretch goals (only if time remains):** Semantic Scholar citation counts, year-range filter UI, light/dark theme toggle.

### 1.5 Definitions
| Term | Meaning |
|---|---|
| arXiv | A free, open repository of research papers (arxiv.org), with a public API |
| LLM | Large Language Model: the AI that reads and writes text |
| Agent | One LLM-driven step with a single responsibility in the pipeline |
| RAG | Retrieval-Augmented Generation: fetch relevant text chunks first, then make the LLM answer only from them |
| Embedding | A vector of numbers representing the meaning of a piece of text, used for semantic search |
| Vector store | A database that finds the most similar embeddings (ChromaDB) |
| TPM / RPD / TPD | Tokens per minute / requests per day / tokens per day (API rate limits) |
| SSE | Server-Sent Events: the server streams live progress updates to the browser |
| Job | One review run, identified by `job_id` |

### 1.6 References
- arXiv API User Manual and Terms of Use (arxiv.org/help/api)
- GroqCloud docs: models and rate limits (console.groq.com/docs)
- Google Gemini API docs (ai.google.dev)
- `DESIGN.md`, `SECURITY.md`, `CLAUDE.md` in this repository

---

## 2. Overall Description

### 2.1 Product Perspective
A standalone, locally run web application:
- **Backend:** Python FastAPI server on the presenter's laptop.
- **Frontend:** React single-page app served by Vite in development.
- **External services:** arXiv API (papers), Groq API (primary LLM), Gemini API (fallback LLM).
- **Local AI:** sentence-transformers embedding model and a ChromaDB vector store. These run offline at no cost.

### 2.2 Product Functions (summary)
| ID | Function |
|---|---|
| F1 | Accept a research topic and start a review job |
| F2 | Stream live, per-agent progress to the UI |
| F3 | Retrieve, rank and select relevant arXiv papers |
| F4 | Extract structured facts per paper |
| F5 | Generate a cited literature review with themes and research gaps |
| F6 | Show a comparison table (method / dataset / result) |
| F7 | Verify citations and flag weakly supported claims |
| F8 | Answer follow-up questions from full-text PDFs (RAG) with sources |
| F9 | Export as Markdown and BibTeX, and print to PDF |
| F10 | Demo mode: replay cached results offline |
| F11 | Evaluation harness producing accuracy and latency numbers |

### 2.3 User Classes
| User | Description | Needs |
|---|---|---|
| Student / researcher (primary) | Starting a project or paper | Fast overview of a field, real citations, research gaps |
| Faculty evaluator (demo audience) | Types their own topic live | Speed, credibility, visible AI pipeline, numbers |
| Developer (team) | Builds and maintains the app | Clear contracts, mocks, simple setup |

### 2.4 Operating Environment
- **Development and testing:** Windows 10/11 first, then macOS (Apple Silicon or Intel). The same codebase must run on both with no code changes.
- **Python** 3.14. **Node.js** current LTS.
- **Browser:** recent Chrome, Edge or Safari.
- **Network:** internet access is required for live runs. Demo mode must work fully offline.

### 2.5 Design and Implementation Constraints
| ID | Constraint |
|---|---|
| C1 | **Groq free tier** limits per model (as shown in the account's limits page): **30 RPM, 1K RPD, 8K TPM, 200K TPD** for `openai/gpt-oss-120b` and `openai/gpt-oss-20b`. The design must keep a full run within these limits. |
| C2 | Whole PDFs must **not** be sent to the LLM (8K TPM). Abstracts drive extraction; full text is used only through RAG retrieval of a few chunks. |
| C3 | The arXiv API must be called politely: **at most 1 request every 3 seconds**, single connection. |
| C4 | Embeddings must run **locally** (no embedding model on the free LLM tier). |
| C5 | No secrets in source code or Git history. Keys come from a `.env` file. |
| C6 | Cross-platform paths (`pathlib`), no OS-specific shell scripts in the core app. |
| C7 | 3-day build: prefer simple, well-supported libraries over custom infrastructure. |
| C8 | Preview LLM models (e.g. `qwen/qwen3.8-27b`) may be used only as an optional fallback, never as the default, because they can be withdrawn at short notice. |

### 2.6 Assumptions and Dependencies
- The Groq free tier and arXiv API remain available during the build and demo.
- The college network allows HTTPS to arxiv.org, api.groq.com and generativelanguage.googleapis.com. If not, demo mode is used.
- The presenter's laptop has at least 8 GB RAM and about 2 GB free disk (embedding model plus the PyTorch CPU build).

---

## 3. Functional Requirements

Priority: **M** = Must (needed for the demo), **S** = Should, **C** = Could.

### 3.1 Review Creation
| ID | Requirement | Priority |
|---|---|---|
| FR-1 | The user can enter a topic (3–200 characters) and start a review. | M |
| FR-2 | The user can choose the number of papers (4–12, default 8). | S |
| FR-3 | The user can optionally set a minimum publication year. | C |
| FR-4 | The home screen shows 3–5 one-click **demo topic chips**. | M |
| FR-5 | The system rejects empty, too-short or too-long topics with a clear message. | M |

### 3.2 Pipeline
| ID | Requirement | Priority |
|---|---|---|
| FR-10 | **Planner:** generate 2–3 diverse arXiv search queries from the topic (one LLM call, small model). If the LLM fails, use the raw topic as the only query. | M |
| FR-11 | **Searcher:** fetch up to 25 candidate papers across all queries from the arXiv API and de-duplicate them by arXiv ID. | M |
| FR-12 | **Ranker:** embed topic and abstracts locally, rank by cosine similarity and keep the top N. Store each paper's relevance score. | M |
| FR-13 | **Extractor:** for each selected paper, extract `problem`, `method`, `datasets[]`, `metrics[]` (name and value), `key_result` and `limitations` from title and abstract into **schema-validated JSON**. Unknown fields must be `"Not reported"`, never guessed. Papers are batched (about 4 per call) to respect TPM. | M |
| FR-14 | **Synthesizer:** produce a Markdown review with sections **Overview, Key Themes, Methods & Results Comparison, Research Gaps, Conclusion**. Every factual sentence must carry one or more citation markers `[n]` that refer **only** to selected papers. | M |
| FR-15 | **Verifier:** (a) flag any `[n]` outside 1..N as invalid and remove it; (b) compute a support score per cited sentence (embedding similarity between sentence and cited paper's abstract and extraction) and flag sentences below the threshold as **weakly supported**; (c) report the citation validity percentage. | M |
| FR-16 | **Indexer (background):** after the review is returned, download the PDFs of the selected papers (respecting C3), extract text per page, chunk it, embed it and store it in the vector store for that job. | S |
| FR-17 | If a PDF fails to download or parse, fall back to indexing its abstract and mark that paper as `abstract_only`. | S |

### 3.3 Progress and Results
| ID | Requirement | Priority |
|---|---|---|
| FR-20 | Stream SSE events for every stage: started, progress (e.g. "extracting 5/8") and completed or failed, with elapsed time. | M |
| FR-21 | The UI shows an **agent timeline** with each stage's status, duration and tokens used. | M |
| FR-22 | The UI shows the review with **clickable citation chips**: hovering or clicking `[n]` shows the paper's title, authors, year and arXiv link. | M |
| FR-23 | Weakly supported sentences are visibly marked (e.g. underline plus ⚠ tooltip with the score). | S |
| FR-24 | The UI shows a sortable **comparison table**: Ref, Title, Method, Dataset(s), Key Result, Limitations. | M |
| FR-25 | The UI shows a **paper list** with title, authors, year, relevance score, abstract (collapsible) and arXiv links. | M |
| FR-26 | A **stats bar** shows papers considered/selected, total time, tokens per model, provider and models used, and citation validity percentage. | S |

### 3.4 Follow-up Q&A (RAG)
| ID | Requirement | Priority |
|---|---|---|
| FR-30 | After indexing completes, the user can ask questions about the selected papers. | S |
| FR-31 | Answers use only the top 4 retrieved chunks and cite sources as `[n, p.X]` (paper ref and page). | S |
| FR-32 | If the retrieved chunks don't contain the answer, the system says so instead of guessing. | S |
| FR-33 | Each answer lists its source snippets with links. | S |

### 3.5 Export
| ID | Requirement | Priority |
|---|---|---|
| FR-40 | Export the review, comparison table and references as **Markdown**. | M |
| FR-41 | Export references as **BibTeX** generated from arXiv metadata. | S |
| FR-42 | A print-friendly view (browser print → PDF). | C |

### 3.6 Demo Mode and Caching
| ID | Requirement | Priority |
|---|---|---|
| FR-50 | Cache arXiv responses and LLM responses on disk, keyed by request content. A repeated identical run must use no API quota. | M |
| FR-51 | A pre-warm script runs the pipeline for a list of topics and stores the results. | M |
| FR-52 | With `DEMO_MODE=true`, cached topics replay with realistic simulated progress timing and **no network calls**. | M |
| FR-53 | If the primary provider returns a rate-limit or server error, automatically fall back to the secondary provider and show the switch in the timeline. | M |

### 3.7 Evaluation
| ID | Requirement | Priority |
|---|---|---|
| FR-60 | `eval/topics.yaml` holds at least 10 test topics across different CS fields. | M |
| FR-61 | `eval/run_eval.py` runs every topic and writes `eval/results.md` and `eval/results.csv` with: papers selected, stage latencies, total time, tokens per model, citation validity %, weak-claim %, extraction completeness % (fields not "Not reported"). | M |
| FR-62 | The results table includes an empty **human relevance (1–5)** column for manual scoring by Member 3. | S |

---

## 4. Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-1 | Performance | A live run with 8 papers returns the review in **≤ 90 s** on a normal connection (target ≤ 60 s). Q&A answers in ≤ 10 s. |
| NFR-2 | Quota | One run uses **≤ 15K LLM tokens in total**, so at least 13 full runs fit in one day's free quota per model. |
| NFR-3 | Rate-limit safety | A client-side token bucket keeps each model under 8K TPM and 30 RPM. HTTP 429 responses are retried using the server's retry-after value, then fall back to the other provider. |
| NFR-4 | Reliability | No single failure (one PDF, one LLM call, the fallback provider) crashes a run. Partial results are returned with warnings. |
| NFR-5 | Accuracy | Citation validity (refs within 1..N) is **100%** after verification. Extraction never invents values (enforced by prompt plus schema). |
| NFR-6 | Usability | A first-time user can start a review within 10 s of opening the app without instructions. All states (loading, empty, error) are handled visibly. |
| NFR-7 | Portability | Identical behaviour on Windows and macOS. Setup is documented for both. |
| NFR-8 | Security | As specified in `SECURITY.md` (secrets, input validation, prompt-injection handling, safe rendering, SSRF-safe downloads). |
| NFR-9 | Maintainability | Typed Python (type hints plus Pydantic), linted with ruff. TypeScript in the frontend. Unit tests for core logic with LLM and network mocked. |
| NFR-10 | Observability | Structured logs per stage with job_id, duration and token counts. No secrets in logs. |
| NFR-11 | Licensing / ethics | Papers are processed locally for analysis only and always linked to their arXiv page. Paper content is never redistributed. |

---

## 5. External Interface Requirements

### 5.1 User Interface
Single-page app: **Home** (topic input, paper count, demo chips) → **Run view** (agent timeline) → **Results** (tabs: Review · Comparison · Papers · Ask · Export) with the stats bar on top. See `DESIGN.md` §6.

### 5.2 Software Interfaces (backend REST API)
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health check plus which providers are configured |
| GET | `/api/demo-topics` | List cached/demo topics |
| POST | `/api/reviews` | Start a job → `{job_id}` |
| GET | `/api/reviews/{job_id}/events` | SSE progress stream |
| GET | `/api/reviews/{job_id}` | Full result (or current status) |
| POST | `/api/reviews/{job_id}/ask` | RAG question → answer with sources |
| GET | `/api/reviews/{job_id}/export?format=md\|bib` | Download export |

Full schemas are in `DESIGN.md` §4.

### 5.3 External Services
| Service | Use | Auth |
|---|---|---|
| arXiv API (`export.arxiv.org/api/query`) | Paper search and metadata | None |
| arXiv PDFs (`arxiv.org/pdf/{id}`) | Full text for RAG | None |
| Groq API | Primary LLM (`openai/gpt-oss-20b`, `openai/gpt-oss-120b`) | `GROQ_API_KEY` |
| Gemini API | Fallback LLM (current Flash model, configurable) | `GEMINI_API_KEY` |

---

## 6. Team Roles

| Member | Responsibility | Deliverables |
|---|---|---|
| Ashwin Kumar (lead) | Architecture, backend, agents, RAG, rate limiting, caching, integration, deployment on the demo laptop | Working backend, API contract and mock fixture by Day 1 noon, final integration |
| Member 2 (React) | Frontend against the mock fixture first, then the live API | All UI screens, SSE timeline, citation chips, table, Q&A, export buttons |
| Member 3 | Evaluation scoring, report, slides, demo script, screenshots | `eval/results.md` human scores, project report, 8–10 slide deck, backup demo recording |

Member 3's work is deliberately **off the critical path**: the demo must work even if it's late.

---

## 7. Schedule (3 days)

| Day | Milestones |
|---|---|
| Day 1 | M1: repo, settings, API contract and mock fixture published. M2: arXiv client, ranker, LLM layer (providers, rate limiter, router, cache), planner and extractor working from the CLI. Frontend: layout and mock-driven screens. |
| Day 2 | M3: synthesizer and verifier, SSE, full API, Markdown/BibTeX export. M4: PDF indexing and Q&A (RAG). M5: frontend switches from mocks to the live API. |
| Day 3 | M6: demo mode, pre-warm, Gemini fallback test, eval run, bug fixes, Mac run-through, README. Member 3: report, slides, backup recording, rehearsal. |

---

## 8. Acceptance Criteria (demo-ready definition)

1. A topic typed live by a faculty member produces a review with **≥ 6 papers** in **≤ 90 s**.
2. Every citation chip opens the correct real arXiv paper. Citation validity is 100%.
3. The comparison table is filled for all selected papers, with "Not reported" where the abstract lacks data.
4. The agent timeline shows every stage with timings and token usage.
5. At least one follow-up question is answered with page-level sources.
6. The Markdown and BibTeX exports download and open correctly.
7. Demo mode replays 3+ topics with networking disabled.
8. `eval/results.md` exists with numbers for 10 topics.
9. The same commit runs on Windows and macOS following the README.
10. No API key appears anywhere in the repository or its Git history.
