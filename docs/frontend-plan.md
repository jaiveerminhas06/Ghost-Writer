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

## Blockers
- Node.js / npm are not installed on this machine.
- A web API layer (FastAPI) must be added before any frontend can talk to the models.

## Owner's answers
(to be filled in)
