# LitLens

A multi-agent AI literature review assistant: type a research topic and get a cited review built from real arXiv papers, a comparison table, and Q&A over the full-text PDFs.

- What to build: [SRS.md](SRS.md)
- How it's built: [DESIGN.md](DESIGN.md)
- Security rules: [SECURITY.md](SECURITY.md)

> Status: **M1 scaffold**. Only `/api/health` exists on the backend. The frontend can be built in full against the mock fixtures.

## Prerequisites
- Python **3.12**
- Node.js LTS (22+)
- A Groq API key (free tier). A Gemini key is optional and only used as a fallback.

## 1. Configure secrets (once)
Copy the example env file to `.env` in the repo root and fill in your keys. `.env` is gitignored: never commit it.

```powershell
Copy-Item .env.example .env     # Windows
```
```bash
cp .env.example .env            # macOS
```

## 2. Backend

### Windows (PowerShell)
```powershell
cd backend
py -3.12 -m venv .venv                 # create an isolated Python environment in .venv
.\.venv\Scripts\Activate.ps1           # activate it (if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)
pip install -r requirements.txt        # install pinned dependencies
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### macOS (zsh)
```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Check it: open http://127.0.0.1:8000/api/health. Interactive API docs are at http://127.0.0.1:8000/docs when `ENV=dev`.

Tests and lint (from `backend/` with the venv active):
```bash
pytest -q
ruff check .
ruff format .
```

## 3. Frontend
```bash
cd frontend
npm install
npm run dev            # http://localhost:5173 ; /api is proxied to the backend on :8000
```

**Mock mode** (no backend needed): copy `frontend/.env.example` to `frontend/.env.local`, which sets `VITE_USE_MOCKS=true`, and restart `npm run dev`. All API calls then return the fixtures in `frontend/src/mocks/`, and the progress stream replays `events.json`.

## Repo layout
See [DESIGN.md §8](DESIGN.md). The API contract lives in three places that must stay in sync: `backend/app/models/schemas.py`, `frontend/src/api/types.ts` and `frontend/src/mocks/*.json`. `backend/tests/test_mocks_match_schemas.py` checks the mocks against the backend models.
