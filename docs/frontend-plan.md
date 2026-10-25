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
- Not done: visual design pass.

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
