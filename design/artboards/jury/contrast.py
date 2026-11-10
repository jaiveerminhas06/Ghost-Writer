"""WCAG contrast of every text and mark colour pair used on the Jury boards, light and proposed dark theme (OKLCH -> sRGB -> contrast ratio).

    python design/artboards/jury/contrast.py        # prints the table and writes design/artboards/jury/contrast.csv
Text needs 4.5:1, marks that carry meaning (rings, strokes, the flag line) need 3:1.
"""
import math
from pathlib import Path

import pandas as pd

LIGHT = {"desk": (0.955, 0.008, 265), "paper": (0.995, 0.003, 265), "ink": (0.23, 0.022, 265), "ink-2": (0.38, 0.02, 265), "ink-3": (0.50, 0.018, 265),
         "pen": (0.45, 0.148, 255), "pen-tint": (0.94, 0.035, 255), "hl-1": (0.965, 0.07, 100), "hl-2": (0.925, 0.12, 95), "hl-3": (0.865, 0.15, 85), "desk-2": (0.925, 0.011, 265)}
DARK = {"desk": (0.205, 0.014, 265), "paper": (0.255, 0.017, 265), "ink": (0.945, 0.008, 265), "ink-2": (0.83, 0.012, 265), "ink-3": (0.73, 0.014, 265),
        "pen": (0.80, 0.11, 255), "pen-tint": (0.31, 0.05, 255), "hl-1": (0.33, 0.05, 95), "hl-2": (0.40, 0.085, 92), "hl-3": (0.49, 0.11, 85), "desk-2": (0.262, 0.016, 265)}


def lum(L, C, h):
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_, m_, s_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3, (L - 0.1055613458 * a - 0.0638541728 * b) ** 3, (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_, -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_, -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
    r, g, b = (min(1, max(0, v)) for v in rgb)                                  # linear sRGB, clipped to the gamut
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = lum(*a), lum(*b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


PAIRS = [("text", "headline and body: ink on paper", "ink", "paper"), ("text", "summary text: ink-2 on paper", "ink-2", "paper"),
         ("text", "captions, tick labels: ink-3 on paper", "ink-3", "paper"), ("text", "captions on the desk: ink-3 on desk", "ink-3", "desk"),
         ("text", "margin note, flag-line label: pen on paper", "pen", "paper"), ("text", "chip text: ink on selected chip (pen-tint)", "ink", "pen-tint"),
         ("text", "'detectors disagree' note: ink on hl-1", "ink", "hl-1"), ("text", "pile caption: ink-2 on desk-2", "ink-2", "desk-2"),
         ("text", "tooltip: paper on ink", "paper", "ink"), ("text", "zone names: ink-2 on paper", "ink-2", "paper"),
         ("mark", "flagged dot and stem: ink on paper", "ink", "paper"), ("mark", "not-flagged ring: ink-2 on paper", "ink-2", "paper"),
         ("mark", "above-usual ring: ink on amber fill (hl-3)", "ink", "hl-3"), ("mark", "official ring and flag line: pen on paper", "pen", "paper"),
         ("mark", "flag line over the flagged band: pen on hl-3", "pen", "hl-3"), ("mark", "flag line over the above-usual band: pen on hl-2", "pen", "hl-2"),
         ("mark", "axis and ticks over the bands: ink on hl-2", "ink", "hl-2")]
rows = []
for theme, pal in (("light", LIGHT), ("dark", DARK)):
    for kind, name, fg, bg in PAIRS:
        r = ratio(pal[fg], pal[bg]); need = 4.5 if kind == "text" else 3.0
        rows.append({"theme": theme, "kind": kind, "pair": name, "ratio": round(r, 2), "needs": need, "passes": r >= need})
df = pd.DataFrame(rows)
df.to_csv(Path(__file__).with_name("contrast.csv"), index=False)
if __name__ == "__main__":
    print(df.to_string(index=False))
    print("\nfailures:", int((~df.passes).sum()), "of", len(df))
