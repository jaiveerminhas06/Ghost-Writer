I want to replace the Streamlit demo (`demo/app.py`) with a proper web front end for Ghost Writer, built to a finished design. Read `CLAUDE.md` first: this is my CSE472 project, there is a viva, and I need to be able to explain every part of it, so explain what each step does and why as you go.

## The design

Everything is in `design/`:
- `design/DESIGN_SPEC.md` — tokens, motion, states and the rules for copy and numbers. Read it fully before anything else.
- `design/artboards/*.dc.html` — the screens and reference sheets. They were made in a design-canvas tool, so they are reference, not code to copy: the spec explains how to read them (`{{holes}}`, `<sc-for>`, `<sc-if>`, and the `renderVals()` method at the bottom of each file).

Match the artboards closely: same layout, type, colours, spacing, copy and states. Where something isn't drawn, follow the spec and the existing components rather than inventing a new look. Do not drift towards generic defaults: no Tailwind, no component library, no Inter, no gradients, no emoji, no coloured left-border stripes, no ALL-CAPS labels.

## Stack

- **Backend:** FastAPI in `api/`, wrapping the existing code in `src/` (`Detector` in `src/detector.py`, `occlusion` / `integrated_gradients` in `src/explain.py`, `attribution.load` / `most_similar` in `src/attribution.py`, `inject_typos` / `words_changed` / `T5Paraphraser` in `src/paraphraser.py`). Reuse the logic in `demo/app.py` (for example its `explain()` fallback from occlusion to integrated gradients, and the 40-word minimum) instead of rewriting it. Load models once, lazily (T5 only on first use), one worker, `HF_HUB_OFFLINE=1`. My GPU has 4 GB.
- **Frontend:** Vite + React + TypeScript in `web/`, plain CSS with the spec's custom properties (CSS modules or one stylesheet per component), React Router for the three pages. Self-host the two fonts via @fontsource so it works offline in the viva room.
- In development, Vite proxies `/api` to FastAPI; for the demo, FastAPI serves the built `web/dist`. One command should start everything; put it in the README.
- Keep `demo/app.py` working as a fallback. Don't delete it.

If you think a different stack would be clearly better for this project, say so in your plan before building.

## API (adjust names if you have a good reason, but tell me)

- `GET /api/meta` → thresholds `{strict, standard}` from `results/09_thresholds.csv`, the unseen-prompt false-positive rates from `results/09_threshold_rates.csv`, max tokens, and the built-in examples from `demo/samples.json` with their known labels.
- `POST /api/score {text}` → logit, word count, token count, whether it was truncated, and the character index where reading stopped.
- `POST /api/explain {text}` → sentence spans, per-sentence scores, which method was used.
- `POST /api/attribution {text}` → top 3 families with shares. The UI only calls this for flagged essays.
- `POST /api/rewrite {text, method: "typos5" | "typos10" | "t5", seed}` → rewritten text, which words changed, share of words changed, new logit.
- `POST /api/batch` (multipart, .txt / .docx / .pdf) → one result per file: name, words, logit, or an error such as "no text found" or "too short". This is a new feature; ask me before adding new dependencies for reading files.
- A not-English check before scoring. Keep it light (no big new dependency) and tell me how it works.

Errors return clear messages the UI can show as-is. Add pytest tests for every endpoint using a small fake detector, so the tests run without the GPU.

## Build order (stop after each phase so I can check it)

1. **Plan.** Read the spec, the artboards and the code in `src/` and `demo/`. Write the plan: folder structure, API shapes, component list, and anything in the design you think can't be built as drawn. Wait for my OK.
2. **API** and its tests.
3. **Frontend shell:** tokens, fonts, header and navigation, and the components from `Components.dc.html` in every drawn state. Make a simple `/components` page that shows them all so I can compare it with the artboard.
4. **Check an essay** (`Main.dc.html`, phone layout from `Phone.dc.html`), wired to the API: score ruler, Strict/Standard switch, highlights, margin notes, flag-line popover, "Which AI" panel.
5. **Try to fool it** (`Fool.dc.html`).
6. **Check a class** (`Class.dc.html`).
7. **States and motion:** every state in `States.dc.html` and every motion spec in the spec, including reduced motion.
8. **Polish and check** (below), then update the README's demo section and add a short "Front end" section to the model card if anything about behaviour changed.

## Rules

- **Never show an invented number.** Every score, rate and count must come from the model or a results file. The margin notes must be generated from real data as the spec describes; the hand-written ones in the artboard were for one example only. The 28-student class in `Class.dc.html` is placeholder data; don't ship it.
- Accessibility: real buttons, links and labels; visible focus rings; 44 px hit areas; colour is never the only signal; `aria-live` for the verdict and errors.
- Small, focused commits with clear messages. Don't commit `node_modules`, `web/dist` or model weights.

## Checking your work

Before saying a phase is done:
- Run the tests and the type check.
- Run the app and open each page at 1440 px and 390 px wide. If you can take screenshots (for example with Playwright), compare them side by side with the matching artboard and list every difference you find, then fix them.
- Go through this checklist and tell me the result: Would a designer think this was AI-generated, and why? Are nested radii concentric and shadows layered and tinted? Are all numbers tabular, and do big headings have tightened tracking? Are any neutrals pure grey? Does every screen have one primary action and an obvious reading order? Are all states from `States.dc.html` reachable? Is all spacing on the scale?
- Tell me anything you skipped or couldn't match, and why.
