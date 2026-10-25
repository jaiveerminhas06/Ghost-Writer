# Frontend redesign: handoff for Claude Code

> **For Jaiveer (read only this box):**
> 1. Open `docs/redesign/ghost-writer-demo.html` in your browser (double-click it; it needs internet for React and the fonts). That is the target design. It runs on demo scores, not the model.
> 2. In VS Code, on the `frontend` branch, tell Claude Code:
>    **`Read FRONTEND_REDESIGN.md and rebuild the frontend to match docs/redesign/ghost-writer-demo.html, step by step.`**
> 3. It will build one piece at a time, commit after each, and tell you what to open. Ask it to explain anything you'll need in the viva.
>
> Everything below is written for Claude Code.

---

## 0. The job in one paragraph

Rebuild `frontend/` so it looks and behaves like the prototype in `docs/redesign/ghost-writer-demo.html`, wired to the existing FastAPI endpoints in `api/main.py`. **No backend changes are needed**: the prototype's mock API returns the same shapes as `api/main.py`. Keep the stack as it is (Vite + React 19, plain JSX, plain CSS, no new runtime dependencies). The owner has a viva and must be able to explain every line, so build in small steps and explain each one (see `CLAUDE.md`: "explain what each step does and why").

Read first: `CLAUDE.md`, `PRODUCT.md`, `docs/frontend-plan.md`, `api/main.py`, `frontend/src/api.js`, and the whole prototype file.

---

## 1. Why the current frontend is being replaced

The current `frontend/src/App.jsx` is correct and honest, but it reads as a plain form:

- **The essay, which is the actual object of study, is a small textarea.** The evidence (highlights) appears in a separate panel below the verdict, so the reader never sees the essay *as examined*.
- **The verdict is a small word and a thin bar.** The scale has no units, so "+9.1 vs +7.8" means nothing to a recruiter.
- **The caveats are grey paragraphs**, the same for every essay. The ones that apply to *this* essay (borderline score, long polished essay, unread tokens) are not singled out.
- **"Try to fool it" shows two numbers and a grey block of text.** You cannot see what changed or how far the score moved.
- **The look is the generic cream paper, system sans and serif-textarea default** that AI-built pages converge on, with nothing specific to the project.

## 2. What the research says (used in the design)

- **Commercial detectors moved away from a bare label.** GPTZero replaced its single human/AI verdict with a three-way result plus a separate certainty score that drops when a text is unlike its training data ([GPTZero help](https://support.gptzero.me/articles/7719430400-how-do-i-interpret-gptzero-s-new-ui-since-january-17-2024-with-confidence-scores-and-mixed-results)). Ghost Writer has the evidence for this already (sentence contributions, the threshold, the held-out error rates), so it should show it. → The essay becomes the main surface, with highlights painted on it and a per-sentence "fingerprint" strip above it.
- **A bare confidence number doesn't change behaviour; a short, specific list of what to doubt does.** Cap it at three to five items and anchor each one to something checkable ([Tian Pan, "Confidence strings, not scores"](https://tianpan.co/blog/2026-04-28-confidence-strings-not-scores-uncertainty-narrative)). → The "Before you trust this" list under the verdict, computed per essay.
- **Explainable-AI interfaces work best with progressive disclosure, counterfactual "what if" views and step-by-step status instead of spinners** ([Eleken, XAI UI patterns](https://www.eleken.co/blog-posts/explainable-ai-ui-design-xai); [Explanation User Interfaces review](https://arxiv.org/pdf/2505.20085)). → The analysis log with live timings (highlights take up to a minute on CPU), the attribution drawer that is closed by default, and "Try to fool it" as a visible before→after with a word diff.
- **Editorial, type-led layouts suit content that needs an authored point of view** ([daisyUI editorial trends](https://trends.daisyui.com/editorial-art-inspired-ui/)). → A strong display serif for the wordmark and verdict, a reading serif for the essay, and mono for every number.

## 3. The design

**Concept: a forensic document examiner's bench under a UV lamp.** In forensic work the essay is the "questioned document". It sits large on the left like a sheet of exam paper. The lab readout sits on the right and stays in view (sticky) while you scroll the essay. AI-like evidence glows amber, like UV-reactive ink. Student-like evidence is cool blue: a blue/orange pair stays readable for colour-blind viewers.

### 3.1 Tokens (copy verbatim)

Copy the whole `:root` block and the two light-theme blocks from the prototype's `<style>` into `frontend/src/index.css`, replacing the current tokens. The design is **dark-first**:

- bare `:root` holds the dark values plus `color-scheme: dark`;
- `@media (prefers-color-scheme: light) :root:not([data-theme="dark"])` and `:root[data-theme="light"]` hold the light values.

Key tokens: `--ground --surface --sheet --ink --muted --faint --line --lamp --glow --glow-text --cool --cool-text --zone-human --zone-ai --hl-max`. Every colour in the components comes from these. `--faint` is for rules and ticks only, never for text.

### 3.2 Type

| Role | Family | Where |
|---|---|---|
| Display | Gloock | wordmark, the verdict sentence, method headings, the big numbers |
| Reading | Literata | the essay, the lede, the rewritten text |
| UI | Geist | buttons, labels, body copy |
| Data | Geist Mono | every score, count and percentage (`tabular-nums`) |

Load them with the same Google Fonts `<link>` as the prototype, in `frontend/index.html`. Keep the fallback stacks from the tokens.

### 3.3 Layout

```
top bar ───────────── course label · prototype badge (REMOVE in real app) · links
hero ──────────────── WebGL wordmark · lede + 3 headline numbers
bench (≥1000px: 1.55fr | 1fr; below: stacked)
  ├─ doc ──────────── specimen picker (3 examples + "your own")
  │                   sheet: header (label, mini verdict on narrow screens, Edit text)
  │                          fingerprint strip (flagged essays only)
  │                          essay (textarea in edit mode, highlighted text in read mode)
  │                          footer (word count · strictness · Analyse essay)
  └─ readout (sticky) analysis log → verdict card → attribution drawer → try to fool it
method ────────────── 4-step pipeline · "What looked good and wasn't" · v1 100% vs now
footer ────────────── do-not-use-on-students note · source link
```

### 3.4 Motion (only these; all respect `prefers-reduced-motion`)

1. **Wordmark ghost ink**: slow WebGL noise flow on the wordmark, a sheen on the letter edges and a faint drifting copy behind it. The pointer stirs it.
2. **Lamp sweep**: when highlights arrive, a violet band sweeps down the sheet once, and the sentence highlights fade in top to bottom (45 ms stagger, capped at 1.3 s).
3. **Score pin glide**: the pin moves from the centre (or from the "before" score) to its value in 650 ms with `cubic-bezier(.2,.8,.2,1)`.
4. Small state transitions on buttons (≤160 ms). Nothing bounces; only `transform`, `opacity` and colour animate.

---

## 4. Component map: prototype → `frontend/src/`

The prototype is a single file of React components written in JSX. Each one moves into its own file almost unchanged. Delete the `mockApi` object and use the real `api.js`.

| Prototype piece | New file | Notes |
|---|---|---|
| CSS in `<style>` | `src/index.css` | Replace the whole file. |
| `SAMPLE_META` | `src/samples.js` | Tags for the 3 examples, matched **by order** to `GET /api/samples`. |
| `Wordmark` + `VERT`/`FRAG` + `cssColor` | `src/components/Wordmark.jsx` | Keep the fallback `<h1>`. Credit liquid-logo (see §7). |
| `Spectrum` | `src/components/Spectrum.jsx` | Uses the real thresholds from the API response. |
| `AnalysisLog` | `src/components/AnalysisLog.jsx` | |
| `doubtsFor` + `Verdict` | `src/components/Verdict.jsx` | See §5.3 for the rules. |
| `Attribution` | `src/components/Attribution.jsx` | Uses `heldout_accuracy` from the API. |
| `FoolIt` + `ATTACKS` | `src/components/FoolIt.jsx` | Attack keys already match `api/main.py`. |
| `diffWords`, `diffByParagraph` | `src/lib/diff.js` | Small LCS word diff, no library. |
| `Fingerprint`, `AnnotatedEssay` | `src/components/Fingerprint.jsx`, `src/components/AnnotatedEssay.jsx` | |
| `App` | `src/App.jsx` | Orchestrates runs (§5.1). |
| `mockApi`, `heuristicScore`, `injectTypos`, `mockParaphrase`, `CANNED_SCORE`, `THRESHOLDS` | **delete** | Mock only. The real thresholds come back from `/api/score`. |
| "Prototype · demo scores" badge | **delete** | |
| Babel/React `<script>` tags | **delete** | Vite already bundles React. |

`useId`, `useCallback` and the rest are standard React hooks and work as they are in React 19.

## 5. Behaviour spec

### 5.1 Running an analysis (`App.jsx`)

- Keep a `runId` ref. Every new run increments it. Each `await` checks `run === runId.current` before setting state, so an old run can't overwrite a new one (the user can switch examples mid-analysis).
- The steps are `read → score → explain + attribution (in parallel)`. Show the verdict **as soon as `/api/score` returns**; highlights and attribution fill in later.
- If not flagged, mark `explain` and `attrib` as **skipped** ("only for flagged essays") and do not call them. This matches `api`/Streamlit behaviour and notebook 14.
- Picking an example loads **and** analyses it. "Your own" clears the sheet and puts it in edit mode.
- Changing strictness re-runs the analysis if a result is showing.
- On first load, analyse example 3 (the false alarm). That shows every panel at once. Also support `?sample=0|1|2` like the Streamlit demo.
- After the run, the log collapses to one line: `Analysed in X s · N of M tokens read`. The timings are measured in the browser with `performance.now()`.
- Errors from the API (`detail` string, including the 429 rate-limit message) appear under the sheet with `role="alert"`, and the sheet returns to edit mode.

### 5.2 The essay in read mode

- Render the **original text** with `<span>`s at each sentence's `start`/`end` from `/api/explain`, and the text between spans as it is (`white-space: pre-wrap` keeps the paragraphs).
- Highlight strength = contribution ÷ strongest positive contribution. Below 10% gets no paint, the same rule as `demo/app.py` (`MIN_SHARE`). Paint uses `color-mix(in oklab, var(--glow) calc(var(--w) * var(--hl-max)), transparent)`; `--hl-max` is contrast-checked for each theme.
- `contribution === null` (beyond 512 tokens) → dotted underline and the tooltip "Beyond the 512 tokens the detector reads".
- Fingerprint strip: one button per sentence. Amber bars point up (toward AI-like), blue bars point down (toward student-like). Hovering or focusing a bar outlines its sentence; clicking scrolls it into view. "Show numbers" swaps to a table (colour is never the only carrier of meaning).
- The note text depends on `method` (`occlusion` vs `integrated_gradients`). Copy both strings from the prototype.
- Not flagged → no strip. Show the note explaining why there are no highlights.

### 5.3 "Before you trust this" (`doubtsFor`)

These are computed in the frontend from data already returned. Show at most 4, in this order:

| Condition | Message (copy from the prototype) | Source of the claim |
|---|---|---|
| flagged and `score − threshold < 2` | Borderline | demo observation, notebook 13/README |
| not flagged and `score − threshold > −2` | Close call | |
| flagged and more than 420 words | Long, polished essay (false alarms: median 489 words) | notebook 14 |
| `method === 'integrated_gradients'` | No single sentence decides it | notebook 14 |
| `tokens > tokens_read` | Only part was read | API |
| flagged | Topics shift the error rate: 0.5%→2.3% (strict), 1%→3.9% (standard) | notebook 09, README |
| not flagged | Not flagged is not proof | |

The rate for the standard setting on unseen prompts is **3.85%** (notebook 09); the prototype rounds it to 3.9%.

### 5.4 Spectrum

The scale is the real logit range (−10 to +10; the score saturates near +9.8). The flag line is the `threshold` from the API. It is drawn in a 320×112 viewBox so the labels stay legible in the readout column. Its `aria-label` describes the full state in words.

### 5.5 Try to fool it

- Four buttons: `typos_5`, `typos_10`, `paraphrase_light`, `paraphrase_heavy`. Clicking one runs it immediately.
- While running, show a skeleton. For paraphrase, warn "about 15 s on a CPU" (measured: 17 s in `docs/frontend-plan.md`).
- Result: a spectrum with a hollow "before" pin and the new pin gliding to the after score; `before → after`; words changed (from the API's `words_changed`); flagged chip; one outcome sentence (four cases, copy from the prototype); the rewritten text with a word diff (`<ins>`/`<del>`) and a "Hide changes" toggle.
- Reset the panel when the text or strictness changes.

### 5.6 Attribution

A `<details>` drawer, closed by default, and only for flagged essays. **The warning comes before the bars.** Wording: "Which training sources does it resemble?" with a "Not authorship" chip. Never say "model X wrote this" (decision of 2026-10-25 in `CLAUDE.md`).

### 5.7 Copy

Keep every caveat from the prototype word for word. They encode decisions already made in `CLAUDE.md` and `MODEL_CARD.md`. The hero and method numbers are the real ones from README/MODEL_CARD: 0.9998, 99.2%, 2.3%, 0.976 → 0–28%, 50% off-topic, 18% for GPT-2. If any of them changes in the README, change it here too.

## 6. Build order (commit after each, on `frontend`)

Explain each step to the owner in 2–3 plain sentences before writing it.

1. **Tokens and fonts**: replace `index.css` tokens and add the fonts `<link>`. Check both themes.
2. **Layout shell**: top bar, hero (static `<h1>` for now), bench grid, method, footer.
3. **Document column**: specimen picker, sheet in edit mode, footer controls, wired to `/api/samples`.
4. **Analysis flow**: the `runId` logic, the analysis log, verdict card + `Spectrum` + `doubtsFor`, wired to `/api/score`.
5. **Explanations**: `AnnotatedEssay` + `Fingerprint` + lamp sweep, wired to `/api/explain`.
6. **Attribution drawer**, wired to `/api/attribution`.
7. **Try to fool it** + `lib/diff.js`, wired to `/api/rewrite`.
8. **Wordmark** WebGL, last, because it's decoration. Ship with the fallback working first.
9. **Quality pass** (§8).

Commit messages follow `CLAUDE.md`: a one-line summary, then bullets for what was done and found.

Run (from `docs/frontend-plan.md`): `uvicorn api.main:app --port 8000` from the repo root, then `npm run dev` in `frontend/`. **Don't run the Streamlit demo at the same time** (4 GB GPU).

## 7. Constraints

- **No new runtime dependencies.** React only. The diff, the shader and the spectrum are each under 80 lines and explainable.
- **Credit**: the wordmark shader is inspired by [collidingScopes/liquid-logo](https://github.com/collidingScopes/liquid-logo) (MIT): edge detection, noise flow and a metallic sheen, rewritten small for text. Add a header comment in `Wordmark.jsx` and a line in `frontend/THIRD_PARTY_NOTICES.md`.
- **WebGL is optional.** If there is no WebGL context or the shader fails to compile, show the `<h1>` in Gloock. With reduced motion, draw one still frame. Pause when off-screen or when the tab is hidden. Device pixel ratio is capped at 1.5.
- **Text is never stored or logged**, and the sheet footer says so. Keep it that way.
- Don't change anything in `api/` or `src/`. If something seems to need a backend change, ask first.

## 8. Acceptance checks

- [ ] `npm run build` passes and `npm run lint` is clean. No console errors with the API running.
- [ ] All three examples render every panel they should (examples 1 and 3 flagged with highlights and attribution; example 2 not flagged, no highlights).
- [ ] Switching examples mid-analysis never shows the old essay's result.
- [ ] A 429 or 422 from the API shows its message.
- [ ] Light and dark both checked; highlight text keeps ≥4.5:1 contrast. Keyboard: every control is reachable, focus is visible, and the fingerprint bars are focusable.
- [ ] 390 px wide: no sideways scroll; the mini verdict appears in the sheet header.
- [ ] `prefers-reduced-motion`: no sweep, no glide, a still wordmark.
- [ ] The production build served by FastAPI (`frontend/dist`) works at `http://localhost:8000`.
- [ ] Screenshot the new page and replace `images/demo_screenshot.png` only if the owner agrees.
- [ ] Update `docs/frontend-plan.md` (Status) and the **Status** section of `CLAUDE.md`.
- [ ] Optional, if installed: `/impeccable critique` and Emil's `review-animations` on the result. Fix real findings, but don't drift from this design.
