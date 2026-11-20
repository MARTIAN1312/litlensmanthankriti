# LitLens

A multi-agent AI literature review assistant: type a research topic and get a cited review built from real arXiv papers, a comparison table, and Q&A over the full-text PDFs.

- What to build: [SRS.md](SRS.md)
- How it's built: [DESIGN.md](DESIGN.md)
- Security rules: [SECURITY.md](SECURITY.md)

> Status: **M3 synthesis + API**. Full review pipeline (plan → search → rank → extract → write → verify) runs through the API with a live progress stream and Markdown/BibTeX export. Full-text Q&A arrives in M4 (`/ask` returns 409 until then). The frontend can be built in full against the mock fixtures.

## Prerequisites
- Python **3.14**
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
py -3.14 -m venv .venv                 # create an isolated Python environment in .venv
.\.venv\Scripts\Activate.ps1           # activate it (if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)
pip install -r requirements.txt        # install pinned dependencies
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### macOS (zsh)
```bash
cd backend
python3.14 -m venv .venv
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

### Try a full review through the API (M3)
With the backend running, in a second terminal:
```powershell
curl.exe -s -X POST http://127.0.0.1:8000/api/reviews -H "Content-Type: application/json" -d '{\"topic\":\"graph neural networks for drug discovery\"}'
```
This returns `{"job_id": "...", "status": "queued"}`. Then:
- live progress: `curl.exe -N http://127.0.0.1:8000/api/reviews/<job_id>/events`
- result: open `http://127.0.0.1:8000/api/reviews/<job_id>` in a browser
- exports: `.../<job_id>/export?format=md` or `?format=bib`

Or use the interactive docs at http://127.0.0.1:8000/docs (dev only). Finished reviews are saved in `data/reviews/` and survive a restart.

### Try the retrieval pipeline from the command line (M2)
Needs `GROQ_API_KEY` in `.env`. From `backend/` with the venv active:
```bash
python -m scripts.extract "crop disease detection using deep learning"
python -m scripts.extract "graph neural networks" --papers 6 --year-from 2022
```
This plans queries, searches arXiv, ranks the results with local embeddings, extracts facts with Groq, and prints a table. Results are cached in `data/cache.sqlite`, so running the same topic again uses no API quota. The first run downloads the embedding model (about 90 MB) from Hugging Face.

On Windows you may see a Hugging Face "symlinks" warning. It's harmless: the model cache just uses a little more disk space.

## 3. Frontend
```bash
cd frontend
npm install
npm run dev            # http://localhost:5173 ; /api is proxied to the backend on :8000
```

**Mock mode** (no backend needed): copy `frontend/.env.example` to `frontend/.env.local`, which sets `VITE_USE_MOCKS=true`, and restart `npm run dev`. All API calls then return the fixtures in `frontend/src/mocks/`, and the progress stream replays `events.json`.

## Repo layout
See [DESIGN.md §8](DESIGN.md). The API contract lives in three places that must stay in sync: `backend/app/models/schemas.py`, `frontend/src/api/types.ts` and `frontend/src/mocks/*.json`. `backend/tests/test_mocks_match_schemas.py` checks the mocks against the backend models.
