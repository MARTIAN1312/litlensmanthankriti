# LitLens frontend

React + Vite + TypeScript + Tailwind. Setup and commands are in the [root README](../README.md).

## Where things are
- `src/api/types.ts`: API types. Mirrors DESIGN §4 exactly; don't edit without updating the backend schemas and mocks.
- `src/api/client.ts`: typed fetch wrappers. Throws `ApiError` with the backend error `code`.
- `src/api/sse.ts`: `subscribeToJob(jobId, { onEvent, onEnd, onError })` for live progress.
- `src/mocks/`: fixtures used when `VITE_USE_MOCKS=true`. Paper titles are prefixed `[MOCK]` and the arXiv IDs are placeholders: the links open unrelated real papers.

## Rules (SECURITY §5)
- Never use `dangerouslySetInnerHTML`, and never add `rehype-raw` to `react-markdown`.
- Render titles and abstracts as plain text. Only make `https://arxiv.org/...` links clickable, with `target="_blank" rel="noopener noreferrer"`.
- Never put API keys in `VITE_*` variables: they ship to the browser.
