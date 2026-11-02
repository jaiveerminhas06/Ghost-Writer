# Plan: build the "paper and margin" front end (phase 1)

Status: **approved 2026-11-01 with the answers listed at the end.** Phase 2 (API) in progress. Source of truth: `design/DESIGN_SPEC.md` and `design/artboards/*.dc.html`.

## 1. Ground rules (from the owner's answers)

- Build on the existing `api/` and `frontend/`. No new `web/` folder, no new `api/` folder.
- `frontend/` stays **plain JavaScript (JSX)**. API response shapes get JSDoc types, checked with `tsc --checkJs`.
- `demo/app.py` (Streamlit) stays working.
- Python deps approved: `python-docx`, `pypdf` (to `requirements.txt`). Anything else is asked first (see section 8).
- The "marked script" files are archived in `docs/redesign/rejected/`.

## 2. What is reused and what is replaced

| Existing | Verdict | Why |
|---|---|---|
| `api/main.py`: lazy `detector()`, `attribution_model()`, `t5()` loaders | **keep** | Already load once, lazily, one worker. |
| `one_at_a_time` lock, `GW_*` env settings, static mount of `frontend/dist` | **keep** | Same hosting story. |
| Occlusion-then-integrated-gradients rule in `/api/explain` (`SATURATED`, `MAX_SENTENCES`, `IG_STEPS`) | **keep** | It is the `demo/app.py` rule. |
| Rate-limit middleware | **change** | 20 POSTs/min would block a 28-file class. Weight batch requests by file count; fix the middleware order (a 429 currently has no CORS headers). |
| `/api/samples`, `/api/score`, `/api/rewrite` shapes | **replace** | Brief: score takes only text and returns word/token/truncation info; the flag is decided in the browser from `/api/meta`. |
| `/api/explain`, `/api/attribution` | **keep, trim** | Same logic; drop the strictness field and the repeated sentence text. |
| `frontend/src/lib/diff.js`, `lib/format.js` | **keep** | Word diff for Fool; `fmt`, `clamp`, `reduceMotion`. |
| `frontend/src/api.js` | **rewrite** | New shapes, timeouts, JSDoc types. |
| `index.css` (UV-lamp tokens), `App.jsx`, `Spectrum`, `Verdict`, `AnnotatedEssay`, `Fingerprint`, `Wordmark`, `AnalysisLog`, `FoolIt`, `Attribution`, `Icon` | **delete / replace** | A different design; nothing visual carries over. |
| `THIRD_PARTY_NOTICES.md` | **update** | liquid-logo is gone; add the font licences. |
| `deploy/` | **update** | Add the new Python deps to `requirements-space.txt`. Hosting stays parked. |

## 3. API (all under `/api`; messages are written for the UI to show as-is)

| Endpoint | In | Out |
|---|---|---|
| `GET /meta` | none | `thresholds {strict, standard}` (09_thresholds.csv); `rates` per setting: unseen-topics average (09_threshold_rates.csv) and the worst single topic (derived from 14_errors.csv: 5.2% strict, 7.7% standard); `attacks` (13_attack.csv: caught after typos 10% and T5 heavy, human flag rate before/after T5 light); `max_tokens`, `min_words`, `max_chars`, `trained_on` (28,006, counted from splits.csv); `examples [{id, name, label, words, text}]` from `demo/samples.json`. |
| `POST /score` | `{text}` | `{logit, words, tokens, tokens_read, truncated, read_chars}` |
| `POST /explain` | `{text}` | `{method, sentences:[{start, end, score\|null}], list_truncated}` |
| `POST /attribution` | `{text}` | `{families:[{family, share}], heldout_accuracy}` (top 3) |
| `POST /rewrite` | `{text, method: typos5\|typos10\|t5, seed}` | `{edited, words_changed, words_changed_share, logit, tokens, tokens_read}` |
| `POST /batch` | multipart `.txt/.docx/.pdf` | `[{name, words, logit, text, error}]`, one per file |

- Errors: HTTP 422/413/503 with `{detail, code}`; codes `too_short`, `not_english`, `too_long`, `no_text`, `unsupported_file`, `busy`.
- **Not-English check, no new dependency** (`api/language.py`): (1) if under 60% of letters are Latin, refuse; (2) otherwise count hits against short stopword lists (about 40 words each) for English, French, Spanish, German, Italian, Portuguese. Refuse when English scores clearly lower than another language, and name that language ("looks like French"); otherwise score. Pure Python, unit-tested, and its limits go in the model card (it can miss very short or mixed-language text).
- Batch reads files with python-docx / pypdf; a PDF with no extractable text (scans) returns `no_text`, under 40 words returns `too_short`. Each file is scored independently, so one bad file never fails the rest. Extracted text is returned so "open this essay" works without storing anything on the server.
- Tests (`tests/test_api.py`): a `FakeDetector` (word-count-based logit, fake tokenizer offsets) replaces `detector()`; every endpoint, every error code, the rate limiter and the CORS headers on a 429. No GPU.

## 4. Front end structure (`frontend/src/`)

```
main.jsx            router + providers
App.jsx             shell: header/nav, toast area, route outlet
api.js, types.js    fetch wrappers with timeouts; JSDoc typedefs for every response
pages/              CheckEssay, TryToFoolIt, CheckClass, ComponentsSheet (/components)
components/         Header, Button, Segmented (Strict/Standard), Ruler, ExampleList, EssayPaper,
                    MarginNote, FlagPopover, WhichAi, MethodCards, AttemptsList, CompareTwo,
                    ClassStrip, EssayRows, Toast, Skeleton, Spinner, Field (textarea + count)
lib/                diff.js, format.js (kept) + tiers.js, notes.js, bins.js, flip.js, spring.js, language-copy.js
styles/             tokens.css, base.css; one CSS module per component
```

- **Shared state** (one React context, persisted in `sessionStorage`): the current essay and its score, the Strict/Standard choice, the Fool attempts, the class results. "Scores are kept on this computer and cleared when you close the tab" is then literally true.
- **Routes:** `/` check an essay, `/fool`, `/class`, `/components`. FastAPI gets a catch-all that serves `index.html`, so deep links work.
- **Fonts** self-hosted through `@fontsource-variable/atkinson-hyperlegible-next` and `@fontsource/tinos`.
- **Styling:** plain CSS custom properties exactly as in the spec (OKLCH, relative colour syntax needs a current browser; fine for the viva laptop). No Tailwind, no component library, no gradients, no emoji, no coloured stripes, no all-caps labels.
- **Motion:** only `transform` and `opacity`. The marker spring uses a CSS `linear()` easing curve generated once from the spec's stiffness and damping, so no animation library. List reordering uses a 30-line FLIP helper. All of it falls back to 120 ms opacity under reduced motion.
- **Checks:** `tsc --checkJs` on the JSDoc types; `node --test` for the pure functions (tiers, notes, bins, diff, language copy) so no test framework is added; pytest for the API.

## 5. How each screen is generated from real data

- **Ruler:** `score` from `/score`, `thresholds` from `/meta`. The flag line moves on Strict/Standard with no request.
- **Verdict sentence, popover and false-flag text:** wording from the artboard; every percentage read from `/meta`.
- **Highlights:** three tiers by share of the strongest contribution: under 10% none, 10-40% light, 40-75% medium, 75% and above dark. The legend ("small / larger / largest drop") is the occlusion wording; when `method` is integrated gradients the legend and note say the style runs through the whole essay.
- **Margin notes (only these, from real data):** the strongest sentence; a one-time note explaining the yellow; "I stopped reading here, at 512 tokens." at `read_chars`; "This example was written by a student." for built-in examples whose label is known. No misspelling note.
- **Class screen:** headline counts and strip from `/batch` results; "expected false flags" = scored essays x the rate chosen in decision 4, rounded the way the artboard words it ("up to one", "about two"); histogram bins of 0.5 past 60 essays; 50 rows per page. The 28-student placeholder is not shipped.

## 6. Build order

1. This plan (done) -> wait for OK.
2. API + tests.
3. Shell: tokens, fonts, header, `/components` sheet with every state.
4. Check an essay (desktop + phone).
5. Try to fool it.
6. Check a class.
7. States and motion, including reduced motion.
8. Polish, check against the artboards, README demo section, short "Front end" part in the model card.

Each phase ends with the checks from the brief (tests, type check, screenshots at 1440 and 390 px, the designer checklist). Small commits. No `node_modules`, `dist`, or weights.

## 7. Things the design asks for that I would change, or can't match exactly

1. **The artboards cannot be opened as they are**: `support.js` (the canvas runtime) is not in the zip. To compare side by side I'll write a small throwaway renderer (replaces `{{holes}}`, `<sc-for>`, `<sc-if>` using each file's own `renderVals()`), kept outside the repo.
2. **Typos on the client side (spec):** I would keep typos on the server. The notebooks' attack used `inject_typos` in Python; a JS copy could behave differently and the numbers on the page (13_attack.csv) would no longer describe what the button does. It takes about 0.5 s, so it still "appears at once".
3. **"Meaning: unchanged" in the Fool result** is true by construction only for typos. For T5 the row will say "Check it still says what the student meant", as the T5 card already advises.
4. **One T5 card in the design, two settings in the model.** The attack results have light (T=1.0, 15% of words changed, no effect) and heavy (T=1.5, 43% changed, 96.4% still caught). The artboard's own claims mix them: "96.4% after heavy T5" and "0.7% to 2.7% for students" (that last one is light). Needs a choice (decision 3).
5. **Misspelling note and wavy underline:** need a real spell check; the notebook used a GloVe vocabulary lookup as a proxy. Left out, as the spec allows.
6. **False-positive wording is inconsistent in the artboard:** Strict quotes the average over two unseen topics (2.3%), Standard quotes the worst single topic (7.7%). Decision 4.
7. **Artboard footer links** point to `AI-Generated-Text-Detection`; the real repo is `Ghost-Writer`. I will link to the real one.
8. **Class screen placeholder line** ("Grade 10, set B. Prompt: ...") has no data source; the app will show only "N files, M scored".
9. **Detector timeouts:** the error state says "stopped answering after 30 seconds". Score gets a 30 s client timeout; explain and rewrite-T5 get longer ones (they can take about a minute on a CPU).
10. **Old API shapes disappear in phase 2**, so the current `frontend/` page stops working until phase 4. The Streamlit demo keeps working throughout.

## 8. Decisions needed

1. **New dependencies** (beyond python-docx and pypdf): `python-multipart` (FastAPI cannot read file uploads without it; not installed); npm `react-router-dom`, `@fontsource-variable/atkinson-hyperlegible-next`, `@fontsource/tinos`, and dev-only `typescript` (for `tsc --checkJs`). Alternative: a 30-line hand-written router instead of react-router.
2. **Typos on the server** (my recommendation) or in the browser as the spec says?
3. **Fool methods:** keep three cards as drawn with T5 at T=1.0, or add a fourth "Heavier T5 paraphrase" card (T=1.5)? I recommend four: the heavy one is the only one that ever changes a verdict.
4. **False-flag figures:** show the average over both unseen topics (2.3% strict, 3.9% standard) with the worst topic (5.2%, 7.7%) as a second sentence? The class estimate would use the average. Or one figure only.
5. **Highlight tier cut-offs** as in section 5.
6. **"ISEP Paris"** appears in the artboard; keep it?
7. **Class of fewer than 5 essays:** show the "You added N essays" card, rows still listed below.
8. **Rate limit:** default 60 requests a minute, with a batch request counting one per ten files.

## 9. Owner's answers (2026-11-01)

1. Dependencies approved: python-multipart, python-docx, pypdf; react-router-dom, @fontsource-variable/atkinson-hyperlegible-next, @fontsource/tinos, typescript (dev only). Use react-router-dom, not a hand-written router.
2. Typos on the server with `inject_typos` and a fixed seed (notebook 13 uses `SEED = 42`, typos seeded `SEED + i`; one essay on the page is `i = 0`, so 42). The hollow "after" marker waits at the old score and springs when the response arrives.
3. Four Fool cards. "Heavy T5" says it is the only rewrite that changed verdicts in notebook 13. Cards aligned with `subgrid`.
4. False-flag figures: lead with the average over both unseen topics (2.3% strict, 3.9% standard), then the worst topic (5.2%, 7.7%). The class estimate uses the average. Every figure read from the results files.
5. Highlight tiers as proposed; the legend uses the same cut-offs.
6. Remove "ISEP Paris".
7. Fewer than 5 essays: the "You added N essays" card with the rows below.
8. Rate limit 60 requests a minute, a batch counting one per ten files, set in one place (`api/settings.py`).
Also agreed: throwaway artboard renderer outside the repo; "Meaning: unchanged" wording only for typos; no misspelling note; links point to `Ghost-Writer`.

## 10. Added requirements (2026-11-01, after phase 2)

- **Fool page (phase 5):** a "Try different typos" action that re-runs the same method with a new seed; each row of the attempts list records its seed. If repeated runs on the same essay land on both sides of the flag line, say so in one plain sentence. Reuse the existing button and list styles; no new components for it. Reason: seed 0 gave +3.3 and seed 42 gave -6.6 for the same 5% typos on the "wrongly flags" example.
- **Timings:** warm, T5 light and heavy both take about 0.75-1.0 s on this GPU (5 runs each, three essays). The earlier "3 s vs 1 s" was model loading. The page shows no timings; cost labels stay qualitative.
- **`docs/api.md`:** plain-language API explanation for the viva (committed).

## 11. Status

- Phase 2 (API and tests): done, `3c51bae`.
- Phase 3 (tokens, fonts, shell, /components): done, `c01842a`.
- Phase 4 (Check an essay, desktop and phone, wired to the API): done, `f53fa80`. Pen colour set to `oklch(0.45 0.148 255)`, comparison removed, `b819c21`.
- Phase 5 (Try to fool it, with "Try different typos" and the seed recorded per attempt): done.
- Pre-phase-6 items: done, `bd06a19` (shared Strict/Standard switch on the Fool page, `api_version` in `/api/meta`, figures tolerated when missing, uploads kept off disk with tests).
- Phase 6 (Check a class: drop zone, summary with expected false flags, dot strip or histogram, sortable table with 50-row pages, class-of-one and fewer-than-five states): done.
- Demo class (30 held-out essays with known labels, `GET /api/demo-class`, button on the class page, known-authors sentence) and the Poisson range for expected false flags: done.
- Phase 7 (states and motion): done. Motion audit (recorded in a real browser, then confirmed against the stylesheets): every `@keyframes` changes only transform and opacity. Transitions that change anything else: colour, border and (method cards only) box-shadow on hover, press, focus and selection, 150 ms, which the spec's own timing table and the artboards' CSS call for; and `grid-template-rows` 0fr to 1fr, 240 ms, on the "Which AI" drawer, which the spec prescribes. With `prefers-reduced-motion: reduce`, 567 recorded animations were all opacity-only and at most 120 ms; the skeleton is still at 0.7 opacity.
- Second demo class ("Summer projects", same method, selection committed before scores were seen; 13 of 30 flagged: 2 of 19 student essays, 11 of 11 AI essays) and the motion audit script (`scripts/motion_audit.py`): done.
- Phase 8 (polish): `scripts/demo.sh` one-command start, `docs/viva-demo.md`, artboard comparison at 1440 and 390 for every page, designer checklist, README / MODEL_CARD / CLAUDE.md updated. One bug found and fixed in the comparison: highlighted sentences hid their text (animated paint layer painted over the text layer). Four off-scale spacing values snapped to the scale. Not merged into `main`: waiting for the owner's review of the diff.

