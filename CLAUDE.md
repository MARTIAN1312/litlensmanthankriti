# CLAUDE.md — LitLens

## What this is
**LitLens**: a multi-agent AI literature review assistant. The user types a research topic; the app fetches real papers from arXiv, ranks them with local embeddings, extracts structured facts with an LLM, writes a cited review, verifies the citations, and answers follow-up questions over full-text PDFs (RAG).

It's a 3-day college group project that will be **demoed live to faculty**, who will type their own topics. Reliability and a polished demo matter more than extra features.

## Read first (source of truth)
- `SRS.md`: what to build (requirements, acceptance criteria). Requirement IDs such as FR-13 are referenced in code comments and commits.
- `DESIGN.md`: how to build it (architecture, pipeline, **data contracts §4**, repo layout).
- `SECURITY.md`: rules that must never be broken.

If these documents conflict with each other or with reality (e.g. a library API changed), **stop and tell me** instead of silently picking one.

## About me (the user)
- I know Python and Java and a little TypeScript. I'm learning, so **when you give me terminal commands, explain what each one does and why**, briefly. Don't just paste.
- I build and test on **Windows first (PowerShell)**, then run it on a **MacBook** for the demo. All code must work on both. Give both command variants where they differ.
- A teammate builds the React frontend. Keep `frontend/src/api/types.ts` and the mock fixtures in sync with DESIGN §4 at all times.

## Stack
Backend: Python 3.14, FastAPI, Pydantic v2, pydantic-settings, sse-starlette, `arxiv`, httpx, PyMuPDF, sentence-transformers (`all-MiniLM-L6-v2`), ChromaDB (NumPy fallback), `groq`, `google-genai`, tenacity, SQLite cache, pytest, ruff.
Frontend: React + Vite + TypeScript, Tailwind, react-markdown + remark-gfm.

## LLM limits (hard constraints)
Groq free tier per model: **30 RPM · 1K RPD · 8K TPM · 200K TPD**.
- `openai/gpt-oss-20b` → plan + extract. `openai/gpt-oss-120b` → synthesize + Q&A.
- Gemini is the fallback; its model ID comes from `.env` (`GEMINI_MODEL`).
- Never send whole PDFs to an LLM. Abstracts are used for extraction; full text only via top-k RAG chunks.
- Every LLM/arXiv call goes through the cache and the rate limiter. **Tests must never hit real APIs.**
- Verify current SDK details (Groq structured outputs, reasoning-effort parameter, google-genai usage) against official docs before relying on them.

## Commands

### Backend — Windows (PowerShell)
```powershell
cd backend
py -3.14 -m venv .venv                 # create isolated Python env
.\.venv\Scripts\Activate.ps1           # activate it (if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pytest -q
ruff check . ; ruff format .
```

### Backend — macOS (zsh)
```bash
cd backend
python3.14 -m venv .venv               # or: python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pytest -q
ruff check . && ruff format .
```

### Frontend (both)
```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api -> 127.0.0.1:8000
# mock mode: set VITE_USE_MOCKS=true in frontend/.env.local
```

### Utilities
```bash
python -m scripts.prewarm "topic one" "topic two"   # from backend/, fills cache for demo mode
python -m scripts.smoke "some topic"                # one real end-to-end run (uses quota)
python ../eval/run_eval.py                          # writes eval/results.md + .csv
```

## Build order (follow it; each milestone must run before the next starts)
1. **M1 Scaffold:** repo layout (DESIGN §8), `.gitignore` + `.env.example` **before the first commit**, `config.py`, `schemas.py` (all DESIGN §4 models), `/api/health`, **mock fixtures + `types.ts` for the frontend**, Vite app with proxy.
2. **M2 Retrieval core:** arXiv client (cached, 3s delay), ranker with embeddings, LLM layer (providers, rate limiter, router, cache), planner, extractor. CLI script prints the extraction table for a topic.
3. **M3 Synthesis:** synthesizer, verifier, orchestrator + jobs + SSE, all review endpoints, Markdown/BibTeX export.
4. **M4 RAG:** PDF download (SECURITY §6), chunker, Chroma store (NumPy fallback), background indexer, `/ask`.
5. **M5 Frontend live:** switch from mocks to the API, timeline, citation chips, table, papers, Ask, Export, stats bar, all loading/error states.
6. **M6 Demo hardening:** demo mode + pre-warm, Gemini fallback tested by forcing a 429, eval harness, Mac run-through, README with setup for both OSes, pre-demo checklist (SECURITY §11).

## Conventions
- Paths via `pathlib.Path`, rooted at a `DATA_DIR` setting. No hard-coded `/` or `\\` paths, no OS-specific shell scripts in the app.
- Type hints everywhere. Pydantic models for every boundary (API, LLM output, agent I/O).
- Agents are pure-ish functions: `async def extract(papers: list[Paper], ctx: RunContext) -> list[Extraction]`. Side effects (events, cache, rate limits) go through `ctx`.
- Blocking work (embeddings, PyMuPDF, arxiv client) goes in `asyncio.to_thread`.
- Prompts live in `app/llm/prompts/`, with a `PROMPT_VERSION` that is part of the cache key.
- Every user-visible failure degrades gracefully (DESIGN §9). Never 500 on a partial failure.
- Small, focused commits referencing requirement IDs, e.g. `feat(extractor): schema-validated batch extraction (FR-13)`.

## Never
- Commit `.env`, keys, `data/` or `.venv/`. Print or log secrets.
- Use `dangerouslySetInnerHTML` or `rehype-raw`.
- Fetch a URL not built from a validated arXiv ID or the allowlisted API hosts.
- Call real LLM or arXiv APIs in tests.
- Add a dependency without telling me what it's for. Prefer the stack above.
- Change the DESIGN §4 contracts without updating `types.ts`, the mocks and DESIGN.md together.

## Definition of done (per feature)
Code + unit test (mocked) + passes `ruff` and `pytest` + works on Windows + mentioned in README if it changes setup. At the end: the SRS §8 acceptance criteria all pass.
