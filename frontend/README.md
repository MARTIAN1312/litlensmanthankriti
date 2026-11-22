# LitLens frontend

React + Vite + TypeScript + Tailwind. Setup and commands are in the [root README](../README.md).

## Where things are
- `src/api/types.ts`: API types. Mirrors DESIGN §4 exactly; don't edit without updating the backend schemas and mocks.
- `src/api/client.ts`: typed fetch wrappers. Throws `ApiError` with the backend error `code`.
- `src/api/sse.ts`: `subscribeToJob(jobId, { onEvent, onEnd, onError })` for live progress.
- `src/mocks/`: fixtures used when `VITE_USE_MOCKS=true`. Paper titles are prefixed `[MOCK]` and the arXiv IDs are placeholders: the links open unrelated real papers.

## Screens & components (Academic Research Companion design)
- `src/App.tsx`: flow state machine — Home → Run (agent timeline) → Results.
- `src/pages/HomePage.tsx`: study-desk home — topic textarea, deck-size selector (4/8/12), demo topic chips.
- `src/pages/RunPage.tsx` + `src/components/AgentTimeline.tsx`: live agent pipeline (planning → indexing).
- `src/pages/ResultsPage.tsx`: stats bar + tabs (Review / Comparison / Papers / Ask / Export).
- `src/components/panels/ReviewPanel.tsx`: renders the review Markdown with citation chips; minimalist vs. detailed-lab mode via the header toggle (`src/components/TopBar.tsx`).
- `src/components/MarkdownReview.tsx`: `react-markdown` (+ gfm) with safe inline `[n]` citation-chip splicing (no `dangerouslySetInnerHTML` / `rehype-raw`).
- `src/components/CitationChip.tsx`: hover preview card + arXiv link for a cited paper.
- `src/lib/format.ts`: shared formatting helpers (durations, tokens, authors, lead sentence).

## Rules (SECURITY §5)
- Never use `dangerouslySetInnerHTML`, and never add `rehype-raw` to `react-markdown`.
- Render titles and abstracts as plain text. Only make `https://arxiv.org/...` links clickable, with `target="_blank" rel="noopener noreferrer"`.
- Never put API keys in `VITE_*` variables: they ship to the browser.
