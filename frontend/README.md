# Ghost Writer front end

Vite + React 19, plain JavaScript (JSX) with JSDoc types checked by `tsc --checkJs`. It talks to the FastAPI app in `../api/` and was built to the design in `../design/`.

```
npm ci            # once
npm run dev       # dev server on :5173 (proxies /api to :8000; start the API first)
npm run build     # writes dist/, which the API then serves on its own port
npm run check     # lint (oxlint), types (tsc) and unit tests
```

The normal way to run everything is `bash scripts/demo.sh` from the repo root. Pages: `/` Check an essay, `/fool` Try to fool it, `/class` Check a class, `/components` the component sheet. Shared state lives in `src/state/` (tab-scoped sessionStorage only); every figure shown comes from `/api/meta`. The API is explained in `../docs/api.md`.
