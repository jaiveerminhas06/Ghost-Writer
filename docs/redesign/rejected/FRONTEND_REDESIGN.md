> **Rejected direction:** this was the "marked script" redesign. It was superseded on 1 Nov 2026 by `design/` ("paper and margin"). Kept for history; do not build from it.

# Frontend redesign v2, "the marked script": handoff for Claude Code

> **For Jaiveer (read only this box):**
> 1. Open `docs/redesign/ghost-writer-demo.html` in your browser (it needs internet for React and the fonts). That is the new target. It runs on demo scores, not the model.
> 2. In VS Code, on the `frontend` branch, tell Claude Code:
>    **`Read FRONTEND_REDESIGN.md and restyle the frontend to match docs/redesign/ghost-writer-demo.html, step by step.`**
> 3. It will change one piece at a time, commit after each, and tell you what to open. Ask it to explain anything you'll need for the viva.
>
> Everything below is written for Claude Code.

---

## 0. The job

**This replaces the first redesign** (dark "UV lamp" bench, WebGL wordmark, amber highlights). The owner found it generic: it was the stock look that AI tools default to. The new direction was chosen by the owner: **the detector marks the essay the way an examiner marks an answer script.**

You already built the first redesign in `frontend/src/` (App, Wordmark, Spectrum, Verdict, AnalysisLog, Fingerprint, AnnotatedEssay, Attribution, FoolIt, lib/diff, lib/format, samples). **Keep the logic and rework the presentation:**

- the `runId` stale-run guard, `?sample=`, the `booted` ref, the API calls and their order, and `lib/diff.js` all stay as they are;
- the components are renamed, split or deleted as listed in §3.

**No backend changes and no new dependencies.** The owner has a viva and must be able to explain every line: build in small steps and explain each one before writing it (see `CLAUDE.md`).

Read first: the whole prototype file, then `frontend/src/App.jsx` and the components, `CLAUDE.md`, `PRODUCT.md`.

---

## 1. The concept, and why it fits this project

The human essays in DAIGT-V2 are **US grade 6–12 school essays**, and the ethical warning is "do not use this to judge a real student". So the page borrows the one setting every visitor knows, an examiner marking a script, and lets the detector play the examiner. Every result becomes a familiar marking convention:

| Result | Was (v1) | Becomes (v2) |
|---|---|---|
| Page intro | WebGL wordmark + facts | **Answer-booklet cover sheet**: boxed Candidate/Examiner/Scheme fields, instructions, a printed "marks awarded" table with the headline numbers written in red pen |
| Example picker | 4 pill cards | **Script tabs**: Script A, B, C and Blank sheet, as folder tabs joined to the paper |
| Essay | Textarea on a dark sheet | **Ruled answer paper**: feint blue rules every 32 px, text sitting on the rules, double red margin line; the textarea is ruled too |
| Verdict | Big serif word + chip | **Rubber stamp**: FLAGGED (red) / NOT FLAGGED (blue), with "NOT PROOF" on the stamp itself, plus the score **circled in red** like a mark |
| Score scale | Spectrum bar | **School ruler**: logit −10…+10, ticks every 0.5, the flag line ruled in red pen, the score marked by a hand-drawn arrow |
| Sentence evidence | Amber highlights + bar strip | **Red-pen underlines**: double line = biggest push, single line = medium, dotted pencil line = slight; **marks in the right margin** level with each sentence (+1.9 "biggest push"); a pencil ✓ for clearly student-like sentences |
| Doubts | Icon list | **Yellow sticky note** "Before you trust this…", stuck on the desk beside the script (inside the paper on smaller screens) |
| Attribution | Drawer | **Paper-clipped slip**, folded shut, labelled "not who wrote it" |
| Progress | 4-step log | One **handwritten line** in the script header: "Marking… scoring 0.6 s", then "Marked in 3.2 s" |
| Try to fool it | Buttons + diff | **Resubmission sheet**: tick-box choices, then the rewrite comes back with **proofreading marks** (struck words, caret insertions in red) and a red-pen comment |
| Method section | Pipeline + numbers | **Examiner's report**: numbered paragraphs 1.1–3.1; "100% accuracy" struck through in red with "not real" |

**Paper never changes colour; only the desk does.** Paper is paper in both themes: only the desk underneath (pale green-grey lino in light, near-black blotter green in dark) follows the theme. So all paper tokens are defined once, and only the `--desk*` tokens are redefined for dark.

## 2. Tokens, type, motion

### Tokens

Replace the token blocks in `frontend/src/index.css` with the prototype's `:root` block and its two dark blocks, copied verbatim. They redefine **only** `--desk --desk-ink --desk-muted --desk-line --tab-idle` and `color-scheme`. Then replace the rest of `index.css` with the prototype's rules. Nothing from the v1 CSS survives except the reset basics.

Contrast already checked on paper `#fbfbf7`: ink 15:1, red pen 5.6:1, pencil 5.9:1.

### Type (update the Google Fonts `<link>` in `frontend/index.html`)

| Role | Family | Used for |
|---|---|---|
| Printed form | Archivo (variable: `wdth` 62–125, `wght` 400–900) | title at 62% width / 900 weight, headings, labels, buttons, body UI |
| The essay | Source Serif 4 | essay text, instructions, the examiner's report paragraphs |
| The examiner's hand | Kalam 400/700 | every red-pen mark, the circled score, the sticky note, progress line, comments |
| Figures | IBM Plex Mono | word/token counts, table numbers, ruler numbers |

The link is in the prototype's head. Also replace the favicon: a red handwritten-looking "G" in a circle on paper colour fits better than the violet one.

### Motion (all off under `prefers-reduced-motion`)

1. **Stamp lands** (260 ms): scale 1.55 → 1 with a slight rotation settle. It replays when the verdict changes, because the element is re-keyed.
2. **Circle draws** around the score (700 ms, `pathLength=1` + `stroke-dashoffset`).
3. **Underlines draw left to right** (900 ms, staggered 70 ms per sentence). How: each underlined sentence has two background layers, a paper-coloured cover over a hand-drawn SVG stroke, and `.lit` slides the cover off. This needs no JavaScript animation.
4. **Margin marks fade in** after the underlines; the **sticky note** slaps on (420 ms, from a slight rotation).
5. **Ruler arrow glides** to the score (650 ms). On a resubmission it glides from the old score.

## 3. Component map: what to do with each existing file

| Existing file | Action | New file(s) | Notes |
|---|---|---|---|
| `components/Wordmark.jsx` | **Delete** | `components/CoverSheet.jsx` | The cover sheet: band, `<h1>`, the red "but who wrote it?" aside with its hand-drawn arrow, the three boxes, instructions, marks table. Remove the liquid-logo line from `THIRD_PARTY_NOTICES.md` (nothing is ported from it any more). |
| `components/Spectrum.jsx` | Replace | `components/Ruler.jsx` | Same props (`score`, `threshold`, `before`, `label`), same pin-glide trick, same `aria-label` sentence. |
| `components/Verdict.jsx` | Split | `components/Stamp.jsx`, `components/Grade.jsx`, `components/StickyNote.jsx`, `lib/doubts.js` | `doubtsFor` moves to `lib/doubts.js`. Its rules are the same as v1, with shorter wording plus one always-on last line ("A flag is a reason to ask questions…"); still at most 4 items. |
| `components/AnalysisLog.jsx` | **Delete** | (in `App.jsx`) | Replace `steps` with one `phase` state: `idle → scoring → tracing → done`, plus `elapsed` and `took`. The handwritten progress line renders from it. |
| `components/Fingerprint.jsx` | **Delete** | `components/Margin.jsx` | The bar strip is replaced by margin marks. Keep the "show as numbers" idea: a "Marks as a table" toggle swaps the ruled page for the table, so colour is never the only carrier of meaning. |
| `components/AnnotatedEssay.jsx` | Replace | `components/MarkedEssay.jsx`, `lib/marks.js` | `markOf()` decides line style and margin mark (§4.2). Inline marks (`.inline-note`) are rendered after each marked sentence and shown only below 820 px, where the margin column is hidden. |
| `components/Attribution.jsx` | Restyle | `components/Slip.jsx` | `<details>` closed by default; the warning comes before the bars, as before. |
| `components/FoolIt.jsx` | Replace | `components/Resubmission.jsx` | Four radio tick-boxes plus one "Rewrite and re-mark" button (v1 ran on click). The rest of the logic is the same; the diff renders as proofreading marks. |
| `components/Icon.jsx` | Delete if unused | | |
| `samples.js` | Edit | | Tags become `Script A` / `Script B` / `Script C`; the notes are in the prototype's `SAMPLE_META`. |
| `lib/diff.js`, `lib/format.js` | Keep | | |
| `App.jsx` | Rework layout | | Keep `runId`, `booted`, `?sample=`, `load`, `edit`, `changeStrictness`, `jump`. The layout is in §4.1. |

Delete from the prototype when porting: `mockApi` and everything it uses (`heuristicScore`, `CANNED_SCORE`, `THRESHOLDS`, `injectTypos`, `mockParaphrase`, `splitSentences`), the "Prototype: demo scores" line, and the CDN/Babel `<script>` tags.

## 4. Behaviour spec (only what changed; the rest of v1's behaviour stands)

### 4.1 Layout

```
desk
├─ desk-top: links (Examiner's report · Model card · GitHub)
├─ CoverSheet (paper)
├─ script-wrap  (≥1180 px: grid  [script column | 236 px side];  below: one column)
│   ├─ script column
│   │   ├─ "Choose a script to mark" + tabs (4 across; 2×2 below 720 px)
│   │   ├─ answer script (paper)
│   │   │   ├─ head: meta row (Script X · Words · Tokens read) · progress line · "Edit the essay"
│   │   │   │        verdict zone: Stamp + Grade (empty placeholders before marking)
│   │   │   ├─ ruler zone: Ruler + one-line caption
│   │   │   ├─ sticky-slot (below 1180 px only)
│   │   │   ├─ toolrow: method note + "Marks as a table"   (flagged only)
│   │   │   ├─ page: ruled lines [MarkedEssay | Margin 150 px (≥820 px)]   or the table
│   │   │   ├─ Slip (flagged only)
│   │   │   └─ foot: word count · Scheme tick-boxes · "Mark this script"
│   │   └─ Resubmission (paper; only once a verdict exists)
│   └─ side: StickyNote (position: sticky; ≥1180 px only)
├─ Examiner's report (paper, id="report")
└─ footer
```

The sticky note is rendered twice (in the side column and in the sticky slot), and CSS shows exactly one of them. `display: none` also hides the other from screen readers, so it isn't read twice.

### 4.2 Marking rules (`lib/marks.js` → `markOf(c, maxPos, maxNeg)`)

`share = contribution ÷ strongest positive contribution`, the same base rule as `demo/app.py`:

| Condition | Line | Margin |
|---|---|---|
| `c == null` (beyond 512 tokens) | none, text in pencil grey | none (tooltip says why) |
| share ≥ 0.6 | **double** red line (`u2`) | red mark, e.g. `+1.9` |
| 0.3 ≤ share < 0.6 | single red line (`u1`) | red mark |
| 0.1 ≤ share < 0.3 | dotted pencil line (`u0`) | none |
| share < 0.1 | none | none |
| negative, ≥ 50% of the most negative and ≥ 10% of maxPos | none | pencil `✓ −0.40` (toward student-like) |

The strongest sentence's mark gets a second line: "biggest push" (occlusion) or "style, not one line" (integrated gradients). Numbers use 2 decimals below 1 and 1 decimal above.

Not flagged: no lines and no margin. The progress line says highlights are only drawn on flagged essays, the same rule as v1.

### 4.3 Margin placement (`Margin.jsx`)

In `useLayoutEffect`: for each mark, take the sentence span's first line box (`getClientRects()[0]`) relative to the page container, and place the mark at that `top`. If it would overlap the previous mark, push it down (`floor = y + height + 4`). Recompute in a `ResizeObserver` on the container and after `document.fonts.ready`, because the web fonts change line breaks. The marks are `<button>`s: hover or focus highlights the sentence, and click scrolls to it (the old `jump`).

### 4.4 Ruled paper

`--line: 32px` is the essay line height and `--rule-y: 24px` is where the blue rule falls inside each line. With Source Serif 4 at 17.5 px the text sits on the rule. **Check this in the browser with the real fonts and adjust `--rule-y` (±2 px) if needed**: the prototype was tuned with the fonts loaded locally.

### 4.5 Stamp

Inline SVG: a double border plus two text lines. The ink filter `#ink` (feTurbulence + feDisplacementMap for rough edges, a second turbulence for speckle holes) is what makes it read as rubber, so keep it. The filter `id` must be unique on the page: there is only one stamp. Re-key the Stamp and the Grade with **different** prefixes (`stamp-…`, `grade-…`). Both sit in the same parent, so sharing a key leaves the old stamp on screen. The prototype hit exactly that bug.

### 4.6 Resubmission

The proofreading marks come from `diffByParagraph` (unchanged). `<del>` = red strike-through over pencil-grey text; `<ins>` = red Kalam text with a CSS caret (`::before`, a rotated corner). Keep the "Clean copy" / "Show marks" toggle. The four comment sentences are the same as v1, reworded in the examiner's voice; copy them from the prototype.

## 5. Build order (commit after each, on `frontend`)

1. Fonts + tokens + desk/paper base CSS; delete `Wordmark.jsx` and add `CoverSheet.jsx`.
2. Script tabs + ruled answer paper in edit mode + foot controls (tick-box scheme).
3. `phase`-based progress line; delete `AnalysisLog.jsx`.
4. `Stamp`, `Grade`, `Ruler` (delete `Spectrum.jsx`, split `Verdict.jsx`).
5. `StickyNote` + `lib/doubts.js`, in both placements.
6. `MarkedEssay` + `lib/marks.js` + `Margin` + the table toggle (delete `Fingerprint.jsx` and `AnnotatedEssay.jsx`).
7. `Slip`.
8. `Resubmission` (delete `FoolIt.jsx`).
9. Examiner's report + footer + favicon.
10. Quality pass (§6). Then update `docs/frontend-plan.md` and the Status section of `CLAUDE.md`.

Run it with `uvicorn api.main:app --port 8000` (repo root) and `npm run dev` (in `frontend/`). Don't run the Streamlit demo at the same time.

## 6. Acceptance checks

- [ ] `npm run build` and `npm run lint` are clean; no console errors against the real API.
- [ ] Script A: flagged (its score is near the ceiling, so expect the integrated-gradients note). Script B: NOT FLAGGED blue stamp, no lines. Script C: flagged, occlusion, strongest line on the conclusion (as in `images/demo_screenshot.png`). Blank sheet: empty ruled textarea, stamp and grade placeholders.
- [ ] Switching scripts mid-marking never shows the old result, and exactly one stamp is ever on screen.
- [ ] Text sits on the rules with the real fonts (adjust `--rule-y`).
- [ ] At ≥820 px, margin marks line up with their sentences and never overlap. Below 820 px they appear inline. At ≥1180 px the sticky note sits beside the script.
- [ ] 390 px: no sideways scroll; the ruler numbers are readable (the CSS enlarges them below 560 px).
- [ ] Desk is dark under dark mode while the paper stays paper; the light desk is checked too.
- [ ] Keyboard: tabs, tick-boxes, margin marks, the slip and every button are reachable with visible focus.
- [ ] `prefers-reduced-motion`: no stamp, circle, underline, sticky or arrow animation.
- [ ] The production build served by FastAPI at `http://localhost:8000` works.
