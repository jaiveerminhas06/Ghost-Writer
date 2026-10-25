# Frontend plan

## What the app does
Ghost Writer decides whether a student essay was written by a person or an AI, and shows why.
Today the only interface is a Streamlit demo (`demo/app.py`). A separate React frontend would replace it
as the polished face of the project; the Streamlit app stays as the working fallback.

## Backend today
- Python. No web API exists: the Streamlit app calls Python functions directly.
- Run: `streamlit run demo/app.py` (port 8501). Needs a GPU for the detector and the T5 paraphraser.

## Screens needed (one page, four panels, same as the demo)
1. Essay input (paste, or load one of 3 examples) and strictness setting.
2. Verdict: score, flag threshold, AI-like / not flagged, plus the warning text.
3. Sentence highlights (which sentences pushed the score up), with a per-sentence table.
4. "Most similar training sources" (flagged essays only, always with the 0-28% warning).
5. "Try to fool it": typos or T5 paraphrase, then re-score.

## Endpoints a thin API would need (does not exist yet; needs your approval)
| Endpoint | Does | Uses |
|---|---|---|
| POST /score | text, strictness -> score, threshold, flagged, token count | `Detector.score` |
| POST /explain | text -> sentence spans + contributions + method | `src/explain.py` |
| POST /attribution | text -> top 3 families | `src/attribution.py` |
| POST /rewrite | text, attack -> edited text, new score, words changed | `src/paraphraser.py` |
| GET /samples | the 3 built-in examples | `demo/samples.json` |

## Status (2026-10-25)
- FastAPI layer exists (`api/main.py`, `uvicorn api.main:app --port 8000`); the five endpoints above are live under `/api`.
- Node is available through nvm (v24); the earlier blocker was stale.
- `frontend/` is a Vite + React app: one page, all panels (examples, strictness, verdict, highlights, attribution, try to fool it).
  Run: `uvicorn api.main:app --port 8000` from the repo root, then `npm run dev` in `frontend/` (http://localhost:5173).
- Tested end to end in headless Chromium (analyse, highlights, typo attack). First score takes ~10 s while models load.
- Not-flagged path and a 390 px phone width checked (fixed a sideways scroll caused by long example names).
- Redesign done (2026-10-25), following `FRONTEND_REDESIGN.md` and the prototype `docs/redesign/ghost-writer-demo.html`: "examination bench" layout (essay left, sticky readout right), dark-first with a light theme, essay painted with sentence highlights plus a per-sentence fingerprint strip, spectrum with the real threshold, per-essay "before you trust this" list, closed attribution drawer, try-to-fool-it with a word diff, WebGL ghost-ink wordmark (plain h1 fallback). `frontend/src/` is now `App.jsx`, `api.js`, `samples.js`, `components/*`, `lib/*`.
- Checked: examples 1-3 show the right panels; switching examples mid-run never shows the old result; 390 px has no sideways scroll; keyboard reaches the bars; highlight text contrast 5.46:1 (dark, strongest paint) and 11.7:1 (light); reduced motion gives a still wordmark; production build served by FastAPI at :8000 works.
- Known: the rate-limit middleware in `api/main.py` sits outside the CORS middleware, so a 429 has no CORS headers and a cross-origin page (Vite dev) sees a network error. The page shows a friendly message for it. A one-line fix (add the CORS middleware after the rate limiter) is waiting for approval.
- Not done: replacing `images/demo_screenshot.png` (needs the owner's OK); `/impeccable critique` and `review-animations` passes.

## Hosting on Hugging Face Spaces (Docker, free CPU)
Code is ready; the Docker image has NOT been built or run (no Docker on this machine), and nothing is pushed.
- CPU support: `Detector`, `explain.py` and T5 pick GPU or CPU automatically. Measured on this laptop with the GPU hidden:
  score 0.5 s, attribution 3 s, typo attack 0.5 s, T5 paraphrase 17 s, highlights 43 s (integrated gradients, 32 steps).
  A 2-vCPU Space will likely be slower.
- `GW_IG_STEPS=32` on the host (128 locally). Sentence ranking matched 128 steps on 3 essays (Spearman 1.0): a small check.
- Weights live in a Hub model repo named by `GW_MODEL_REPO`; `model_path()` downloads them on first start.
- API guards: 20 POSTs/min per visitor (429 after), one model call at a time, 30,000-character cap. Essay text is not logged.
- The page shows the verdict at once and fills in highlights when ready.
- Steps (the account and token are yours): 1) create a Hugging Face account and a write token; 2) `python deploy/upload_models.py <you>/ghost-writer-models`;
  3) create a Docker Space and set the variable `GW_MODEL_REPO`; 4) `bash deploy/push_space.sh https://huggingface.co/spaces/<you>/<name>`.
- Still to check before going public: the DAIGT-V2 licence (the repo already publishes `train_deduped.csv`), and the real speed on the Space.

## Owner's answers
(to be filled in)
