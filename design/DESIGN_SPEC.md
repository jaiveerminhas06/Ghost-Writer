# Ghost Writer front end: design spec

The visual source of truth is the eight artboards in `design/artboards/`. This file adds what the artboards can't show: how to read them, the token values, motion, states and the rules behind the copy. If this file and an artboard disagree, the artboard wins for looks and this file wins for behaviour.

## How to read the artboard files

Each `*.dc.html` file was made in a design-canvas tool. They are **reference, not code to ship**:

- `<script src="./support.js">`, `<x-dc>` and `<helmet>` are the canvas runtime. Don't copy them.
- `{{name}}` is a value computed in the `renderVals()` method of the `<script type="text/x-dc">` block at the bottom of each file. Read that method to see the data and the state logic (for example the Strict/Standard switch).
- `<sc-for list="{{items}}" as="item">` is a loop and `<sc-if value="{{cond}}">` is a conditional.
- All styling is inline `style="…"` plus one `<style>` block per file. Copy the values, not the structure: in the real app these become CSS classes that use the tokens below.

| Artboard | What it is | Width |
|---|---|---|
| `Main.dc.html` | Check an essay (the main screen) | Fluid page, designed at 1440 |
| `Fool.dc.html` | Try to fool it | Fluid page, designed at 1440 |
| `Class.dc.html` | Check a class (new feature, needs a new endpoint) | Fluid page, designed at 1440 |
| `Phone.dc.html` | Check an essay at phone width | 390 |
| `Tokens.dc.html` | Colour, type, space, radius, depth, motion | Reference sheet |
| `Components.dc.html` | Buttons, inputs, nav, segments, cards, rows, popover, toast, every state | Reference sheet |
| `States.dc.html` | Empty, too short, optimistic, loading, errors, edge cases | Reference sheet |
| `Directions.dc.html` | The two directions considered and why "Paper and margin" won | Background only |

## Concept

The essay is a typed student page (Tinos, double-spaced) on a cool blotter-grey desk. The detector speaks in the page's right margin, in blue-pen italics, in the first person, and marks sentences with highlighter. One ruler from −10 to +10 carries every score: the essay's position, the flag line, and the +9.8 ceiling. The tone is candid: a flag is a reason to ask questions, never proof.

## Tokens

All colours are OKLCH. Neutrals are tinted toward hue 265. No pure white, black or grey anywhere (the only exception is `#000` inside CSS masks).

```css
:root {
  /* surfaces and text */
  --desk:   oklch(0.955 0.008 265);  /* page background */
  --desk-2: oklch(0.925 0.011 265);  /* wells, tracks, segmented-control backgrounds, skeletons */
  --paper:  oklch(0.995 0.003 265);  /* essay sheet, panels, raised controls */
  --ink:    oklch(0.23 0.022 265);   /* text, ruler, essay marker */
  --ink-2:  oklch(0.38 0.020 265);   /* secondary text */
  --ink-3:  oklch(0.50 0.018 265);   /* captions, axis labels (still 4.5:1 on desk) */
  --line:   oklch(0.30 0.03 265 / 0.14);  /* hairline */
  --line-2: oklch(0.30 0.03 265 / 0.28);  /* strong hairline */

  /* the detector's voice */
  --pen:        oklch(0.45 0.17 265);
  --pen-hover:  oklch(from var(--pen) calc(l - 0.05) c h);
  --pen-active: oklch(from var(--pen) calc(l - 0.09) calc(c - 0.01) h);
  --pen-tint:   oklch(from var(--pen) 0.94 0.035 h);   /* selected rows, drop target */
  --pen-ring:   oklch(from var(--pen) l c h / 0.35);   /* margin rule, focus glow on inputs */

  /* highlighter: small, larger, largest score drop; --hl-2 is also the over-the-line zone */
  --hl-1: oklch(0.965 0.07 100);
  --hl-2: oklch(0.925 0.12 95);
  --hl-3: oklch(0.865 0.15 85);

  /* errors only, never a verdict */
  --brick:      oklch(0.50 0.16 32);
  --brick-tint: oklch(from var(--brick) 0.955 0.03 h);

  /* depth: tight contact layer + wide soft layer, tinted blue, 1px inset top highlight on raised things */
  --sh-1: inset 0 1px 0 oklch(1 0 0 / 0.55), 0 1px 1px oklch(0.30 0.04 265 / 0.10), 0 2px 6px -2px oklch(0.30 0.04 265 / 0.14);   /* buttons, selected segment */
  --sh-2: inset 0 1px 0 oklch(1 0 0 / 0.8),  0 1px 1px oklch(0.30 0.04 265 / 0.08), 0 10px 28px -10px oklch(0.30 0.05 265 / 0.20); /* essay, panels */
  --sh-3: 0 1px 2px oklch(0.30 0.04 265 / 0.12), 0 28px 64px -18px oklch(0.30 0.06 265 / 0.32);                                   /* popovers, toasts */
  --sh-pen: inset 0 1px 0 oklch(1 0 0 / 0.22), 0 1px 1px oklch(0.30 0.06 265 / 0.20), 0 4px 12px -4px oklch(0.45 0.17 265 / 0.45); /* primary button */

  /* motion */
  --ease-out: cubic-bezier(.22, 1, .36, 1);
  --ease-in:  cubic-bezier(.55, 0, .75, .3);
}
```

Relative colour syntax (`oklch(from …)`) needs a current browser. If you need older-browser support, precompute the derived values; don't invent new colours.

### Type

- **Atkinson Hyperlegible Next** (variable) for everything except essays. Weights: 420 body, 450 inactive tabs, 500 secondary buttons, 550 labels and active tabs, 600 small headings and primary buttons, 650 large headings.
- **Tinos** for essay text only (same metrics as Times New Roman).
- Self-host both (for example the `@fontsource-variable/atkinson-hyperlegible-next` and `@fontsource/tinos` packages) so the demo works offline in the viva room.

| Role | Size | Line height | Tracking | Weight |
|---|---|---|---|---|
| Display (page title) | `clamp(2.25rem, 1.55rem + 2.4vw, 3.5rem)` | 1.05 | −0.028em | 650 |
| Verdict | `clamp(1.75rem, 1.35rem + 1.5vw, 2.5rem)` | 1.1 | −0.02em | 650 |
| Section | 1.625rem | 1.15 | −0.015em | 650 |
| Small heading | 1.125rem | 1.35 | −0.005em | 600 |
| Essay (Tinos) | 1.1875rem | 2.05 | 0 | 400 |
| Body | 1.0625rem | 1.55 | 0 | 420 |
| Margin note | 0.9375rem italic, `--pen` | 1.5 | 0 | 420 |
| Caption | 0.875rem | 1.45 | +0.005em | 420 |

Every number uses `font-variant-numeric: tabular-nums`. Headings use `text-wrap: balance`; paragraphs `text-wrap: pretty`. Use a real minus sign (−) for negative scores.

### Space and radius

- Spacing: 2 px steps up to 16 (2, 4, 6, 8, 10, 12, 14, 16), then 20, 24, 28, 32, 40, 48, 56, 64, 80, 96. Nothing off this scale.
- Radius: 2 highlighter marks · 6 essay sheet · 8 buttons, inputs, segments · 10 primary button · 12 segmented track (8 + 4 padding) · 14 option list (8 + 6) and popovers · 18 panels and cards.
- Nested controls are concentric: outer radius = inner radius + inset. Cards with 20 px padding don't need to match (padding larger than the radius).

## Components and states

`Components.dc.html` draws every state; build exactly those:

- **Buttons:** primary, secondary, quiet and icon, each in rest, hover (pointer only), pressed (scale 0.97), keyboard focus (2 px pen outline, 3 px offset), working (spinner and "…ing" label) and disabled.
- **Inputs:** textarea in Tinos with a live word count; focus = pen border plus 3 px `--pen-ring` glow; error = brick border plus a message that says what to do; disabled select with the reason under it.
- **Navigation:** text tabs with a 2 px pen underline for the current page (`aria-current="page"`).
- **Segmented control** (Strict/Standard): the selected segment is the only raised thing in its track.
- **Method cards:** a radio group laid out with `grid-template-rows: subgrid` so titles, costs, descriptions and result lines align.
- **Rows:** rest, hover, selected (pen tint, weight 600), queued and error (brick tint). No coloured left stripes anywhere.
- **Popover** ("What is the flag line?") and **toast** (bottom right, `role="status"`; errors get a brick icon, never a stripe).

Hit areas are at least 44 px, even for 18 px icons. Hover styles only inside `@media (hover: hover)`; on touch the pressed colour shows while the finger is down.

## Motion

Animate only `transform` and `opacity`. Durations: press 120 ms, colour/border 150 ms, fades and list items 200 ms, moves 240 ms, exits 120–160 ms with `--ease-in`.

- **Score arrives:** the essay marker slides from the left end of the ruler to its score with a spring (about 320 ms; stiffness 380, damping 32). The verdict sentence fades in over 180 ms once the marker lands.
- **Strict/Standard:** the flag line moves with `translateX` over 240 ms `--ease-out`; the yellow zone resizes with `scaleX` from its right edge on the same timing. This is client-side and needs no request.
- **Highlights:** paint top to bottom, opacity over 180 ms with a 40 ms stagger; margin notes follow 120 ms later.
- **Popover:** enter with opacity and scale 0.96 → 1 over 180 ms `--ease-out`; exit over 120 ms `--ease-in`. Esc or an outside click closes it and focus returns to the button.
- **"Which AI" panel:** opens with `grid-template-rows: 0fr → 1fr` over 240 ms and its content fades in over 180 ms.
- **Rewrite and re-score:** the button presses to 0.97 and reads "Rewriting…". Typos are made on the client side and appear at once, changed words underlined. A hollow "after" marker waits at the old score, then springs to the new one when the score returns.
- **Attempts list:** a new attempt enters at the top (translateY −8 px → 0 with opacity over 200 ms); rows below shift with a FLIP transform over 200 ms. Removal: opacity and translateX 12 px over 160 ms `--ease-in`.
- **Class check:** on drop, every file appears at once as "Queued" and fills in as scores arrive. Each dot drops onto the strip (opacity and translateY 6 px, 180 ms, 20 ms apart, capped at 400 ms total). Sorting reorders with FLIP over 220 ms; above 50 rows, only a 120 ms cross-fade.
- **Toast:** enter translateY 16 px → 0 with opacity over 220 ms; stays 6 s, paused while hovered or focused; exit opacity and translateY 8 px over 160 ms.
- **Skeleton:** only after 300 ms of waiting; pulses opacity 0.55 → 1 over 1.4 s.
- **Reduced motion:** every movement becomes an opacity change of 120 ms or less; the skeleton is still at 0.7 opacity.

## States (see `States.dc.html`)

Empty · too short (needs 40 words; show "N more to go", not an error) · optimistic first 300 ms · skeleton after 300 ms · error: detector didn't respond (essay is kept, Score stays enabled, focus moves to the message, `role="alert"`) · error: not English (refuse to score, say why) · not flagged (no green, no tick, same honesty as a flag) · very long essay (show where reading stopped at 512 tokens; highlights end there) · class of one (hand over to the single-essay check) · hundreds of essays (strip becomes 0.5-point histogram bins past 60 essays; 50 rows per page).

## Rules for copy and numbers

- Use the artboards' wording. Sentence case. No emoji, no ALL-CAPS labels, no arrows appended to links.
- **Never invent a number.** Every score, rate and count shown must come from the model, the API or a results file. Thresholds come from `results/09_thresholds.csv`; false-positive rates from `results/09_threshold_rates.csv` and the model card.
- The margin notes in `Main.dc.html` were written by hand for one example. In the app, notes must be generated from real data only:
  - a note on the strongest-scoring sentence ("The sentence I lean on most…"),
  - a one-time note on the first highlight explaining what yellow means,
  - "I stopped reading here, at 512 tokens." when the essay is truncated,
  - "This example was written by a student." only for built-in examples whose label is known.
  - The misspelling note needs a real spell check. Leave it out unless one is added.
- The "Which AI" guess is shown only when the essay is flagged, always after its warning, and closed by default.
- On the class screen, "expected false flags" = number of essays × the unseen-prompt false-positive rate for the selected threshold. The design's copy quotes the worst single topic (7.7% at the 1% threshold, from notebook 14); the results file's average over both unseen topics is 3.85%. Pick one, say which in the copy, and read it from a file rather than hard-coding it.
- The example class (28 students, their names and scores) is made-up placeholder data. Don't ship it.

## Phone

`Phone.dc.html` is the main screen at 390 px: examples become sideways-scrolling chips with edge fades; margin notes move under their paragraph; a fixed bottom bar holds "Edit essay" and "Try to fool it" above the home indicator (safe-area inset). The other screens just need to reflow without horizontal page scroll; wide tables scroll inside their own box.
