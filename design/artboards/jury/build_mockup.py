"""Static mockup of "The Jury" for the Check an essay page (Phase 4 design, before any building).

    python design/artboards/jury/build_mockup.py        # writes design/artboards/Jury.html
    python design/artboards/jury/shoot.py               # screenshots every board into design/artboards/jury/*.png

Not code to ship (same rule as the other artboards): the real app is React. Every number on the boards is read from the results files and from
the precomputed trials (results/22_jury_examples.json), never typed here. The page copy is a proposal for approval.
"""
import html
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import pandas as pd

from api import jury_api, results
from src import jury as core

PRE = json.loads((ROOT / "results" / "22_jury_examples.json").read_text())
META = results.meta(jury_live=True)
EX = results.examples()
CAP = core.Calibration().cap
SC = core.Calibration().scale()
STATS = META["jury"]["statistics"]
ATT = META["jury"]["attacks_final"]
FLIPS = pd.read_csv(ROOT / "results" / "22b_flip_destinations.csv")
ZONE_LABEL = {"flagged": "Flagged", "above_usual": "Above usual", "not_flagged": "Not flagged"}


def entry(i):
    return PRE["examples"][jury_api.digest(EX[i]["text"])]


def one_in(p):
    return f"1 in {round(1 / p):,}"


def pct(x, d=1):
    return f"{100 * x:.{d}f}%"


def esc(s):
    return html.escape(str(s), quote=True)


# ---------------------------------------------------------------------------------------------------------------- the scale (SVG)
def dodge(items, step):
    """Discrete rows: each dot takes the lowest row not used by a dot closer than `step` in x. items: list of (x, key). Returns {key: row}."""
    rows, placed = {}, []
    for x, key in sorted(items):
        k = 0
        while any(abs(x - px) < step and pk == k for px, pk in placed):
            k += 1
        placed.append((x, k))
        rows[key] = k
    return rows


def scale_svg(events, official, phone=False, focus_seed=None, show_tip=None, label_ids="a"):
    """The one scale: ticks in plain words (1 in 10 ...), zone bands, the official marker on top, the jury hanging underneath.
    Vertical order, top to bottom: zone names, official label, marker, axis with the bands, tick labels, flag-line label, the swarm."""
    W = 342 if phone else 1160
    r = 6.0 if phone else 8.0
    step = 2 * r + 2
    band = 9 if phone else 11
    ax_y = 74 if phone else 86
    AX = W - 8 if phone else W - 236
    x0 = 4
    X = lambda pos: x0 + pos / CAP * (AX - x0)
    marks = [e for e in events if e["type"] == "juror"]
    inside = [(X(m["position"]), m["seed"]) for m in marks if not m["at_cap"]]
    capped = [m for m in marks if m["at_cap"]]
    rows = dodge(inside, step)
    top = ax_y + band + (50 if phone else 58)                      # first row of the swarm
    n_rows = (max(rows.values()) + 1) if rows else 0
    swarm_h = max(n_rows * step, 34)
    cols = 8 if phone else 9
    pile_rows = math.ceil(len(capped) / cols) if capped else 0
    pile_w, pile_h = cols * step + 22, pile_rows * step + 20
    tip_room = 52 if show_tip else 0
    if phone:
        pile_x, pile_y = W - pile_w, top + swarm_h + 12
        H = pile_y + pile_h + (58 if capped else 4) + tip_room
    else:
        pile_x, pile_y = AX + 30, ax_y + band + 8
        H = max(top + swarm_h + 14 + tip_room, pile_y + pile_h + 78)
    xa, xf = X(SC["above_usual_line"]), X(SC["flag_line"])
    o = []
    A = o.append
    A(f'<svg class="scale" width="{W}" height="{H:.0f}" viewBox="0 0 {W} {H:.0f}" role="img" aria-labelledby="sc-{label_ids}"><title id="sc-{label_ids}">Where each of the 20 detectors puts this essay, and the official verdict, on one scale</title>')
    # zone names (fixed row, never under the marker)
    A(f'<text x="{(xa + xf) / 2:.1f}" y="{13 if phone else 15}" text-anchor="middle" class="zlab">Above usual</text>')
    A(f'<text x="{(xf + AX) / 2:.1f}" y="{13 if phone else 15}" text-anchor="middle" class="zlab">Flagged</text>')
    A(f'<rect x="{xa:.1f}" y="{ax_y - band}" width="{xf - xa:.1f}" height="{2 * band}" class="z-above"/>')
    A(f'<rect x="{xf:.1f}" y="{ax_y - band}" width="{AX - xf:.1f}" height="{2 * band}" class="z-flag"/>')
    A(f'<line x1="{x0}" x2="{AX}" y1="{ax_y}" y2="{ax_y}" class="axis"/>')
    bottom = top + swarm_h
    ticks = ((0, "all" if phone else "every student"), (1, one_in(0.1)), (2, one_in(0.01)), (3, one_in(0.001)))
    for t, lab in ticks:
        x = X(t)
        A(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{ax_y - band}" y2="{ax_y + band}" class="tick"/>')
        A(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{ax_y + band + 24}" y2="{bottom}" class="grid"/>')
        A(f'<text x="{x + (2 if t == 0 else 0):.1f}" y="{ax_y + band + 18}" text-anchor="{"start" if t == 0 else "middle"}" class="tl">{lab}</text>')
    A(f'<line x1="{AX}" x2="{AX}" y1="{ax_y - band - 4}" y2="{ax_y + band + 4}" class="ceiling"/>')
    A(f'<line x1="{xa:.1f}" x2="{xa:.1f}" y1="{ax_y - band - 3}" y2="{ax_y + band + 3}" class="edge"/>')
    # the flag line runs from above the band down through the swarm; its label sits at the top of the swarm
    A(f'<line x1="{xf:.1f}" x2="{xf:.1f}" y1="{ax_y - band - 6}" y2="{bottom}" class="flagline"/>')
    A(f'<text x="{xf - 8:.1f}" y="{ax_y + band + 40 if not phone else ax_y + band + 38}" text-anchor="end" class="flaglab">Flag line{"" if phone else " · " + one_in(core.TAU_FLAG)}</text>')
    # official marker
    pos = min(CAP, -math.log10(official["p"]))
    xo = X(pos)
    cap_end = official["p"] <= 1 / (1 + SC["val_humans"]) + 1e-12
    lab = ("Official verdict at the end of the scale" if phone else "Official verdict: higher than every student essay") if cap_end else f"Official verdict: {one_in(official['p'])}"
    right = pos > CAP * 0.45
    A(f'<text x="{xo + (10 if right else -10) if False else (xo + 12 if right else xo - 12):.1f}" y="{ax_y - band - (27 if phone else 31)}" text-anchor="{"end" if right else "start"}" class="offlab">{lab}</text>')
    if right:                                                      # the label ends at the marker: shift it left of the triangle
        o[-1] = o[-1].replace(f'x="{xo + 12:.1f}"', f'x="{xo + 10:.1f}"')
    A(f'<g class="official"><path d="M{xo - 8:.1f} {ax_y - band - 21} h16 l-8 12 z" class="tri"/><line x1="{xo:.1f}" x2="{xo:.1f}" y1="{ax_y - band - 9}" y2="{ax_y + band}" class="stem"/></g>')
    def dot(m, cx, cy):
        cls = {"flagged": "d-flag", "above_usual": "d-above", "not_flagged": "d-not"}[m["zone"]]
        tip = f"Detector {m['seed']}: {ZONE_LABEL[m['zone']].lower()}; " + ("higher than every student essay we checked" if m["at_cap"] else f"{one_in(m['p'])} student essays score this high or higher")
        out = f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r + 3.2:.1f}" class="ens"/>' if m["ensemble_member"] else ""
        out += f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" class="{cls}"><title>{esc(tip)}</title></circle>'
        if m["seed"] == focus_seed:
            out += f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r + 6.5:.1f}" class="focus"/>'
        return out
    tip_xy = None
    for m in marks:
        if not m["at_cap"]:
            cx, cy = X(m["position"]), top + rows[m["seed"]] * step + r
            A(dot(m, cx, cy))
            if m["seed"] == show_tip:
                tip_xy = (m, cx)
    if tip_xy:
        m, cx = tip_xy
        text = f"Detector {m['seed']} · {ZONE_LABEL[m['zone']].lower()} · {one_in(m['p'])} student essays score this high or higher"
        tw = 7.3 * len(text) + 26
        tx = min(max(cx - tw / 2, 0), AX - tw)
        A(f'<g class="tip"><rect x="{tx:.1f}" y="{bottom + 12:.1f}" width="{tw:.1f}" height="34" rx="8"/><text x="{tx + 13:.1f}" y="{bottom + 34:.1f}">{esc(text)}</text></g>')
        A(f'<path d="M{cx - 6:.1f} {bottom + 12:.1f} l6 -7 l6 7 z" class="tipar"/>')
    if capped:
        A(f'<rect x="{pile_x:.1f}" y="{pile_y:.1f}" width="{pile_w}" height="{pile_h}" rx="12" class="pile"/>')
        for i, m in enumerate(capped):
            A(dot(m, pile_x + 11 + r + (i % cols) * step, pile_y + 10 + r + (i // cols) * step))
        cap_lines = ([f"{len(capped)} of 20 are off the scale: higher than every", "student essay we checked. Order here means nothing."] if phone else
                     [f"{len(capped)} of 20 score higher than", "every student essay we checked", "(all 2,291). Stacked: the", "order here means nothing."])
        ax_ = W if phone else pile_x
        A(f'<text x="{ax_:.1f}" y="{pile_y + pile_h + 20:.1f}" text-anchor="{"end" if phone else "start"}" class="pilecap"><tspan class="b">Off the scale</tspan>' + "".join(f'<tspan x="{ax_:.1f}" dy="{16 if phone else 17}">{esc(l)}</tspan>' for l in cap_lines) + '</text>')
        if phone:
            A(f'<path d="M{AX} {ax_y + band + 6} V{pile_y - 4:.1f}" class="bracket"/>')
        else:
            A(f'<path d="M{AX} {ax_y + band + 6} V{pile_y + 22:.1f} H{pile_x:.1f}" class="bracket"/>')
    A("</svg>")
    return "".join(o)


# ---------------------------------------------------------------------------------------------------------------- copy
def verdict_sentence(zone):
    p = META["official"]["p_ai_given_zone"]
    one_third, ten = p["34.6% (the dataset)"]["above_usual"]["value"], p["10%"]["above_usual"]["value"]
    if zone == "flagged":
        return "Flagged. This reads like the AI essays I was trained on, but that isn’t proof."
    if zone == "above_usual":
        return (f"Above usual. Higher than most student essays, but most essays that score here are written by students "
                f"(about {round(10 * (1 - one_third))} in 10 at a one-third AI share, about {round(10 * (1 - ten))} in 10 at 10%).")
    return "Not flagged. This reads like the student essays I was trained on."


def summary_sentence(s):
    a, u, n = s["says_ai"], s["unsure"], s["says_student"]
    if a == 20:
        return "All 20 detectors flag this essay."
    if n == 20:
        return "None of the 20 detectors flag this essay."
    parts = [f"{a} of 20 detectors flag this essay"]
    if u:
        parts.append(f"{u} say it is above usual")
    if n:
        parts.append(f"{n} say it reads like a student’s")
    return "; ".join(parts) + "."


SAME = "All 20 were trained on the same essays with the same method and are equally accurate; only the random seed differs. A single detector would have shown you just one of these marks."


def why_text():
    h = STATS["S3"]["heldout_prompt_humans"]["all20"]
    off = META["official"]["students_unseen_topics"]["flagged"]["value"]
    return (f"On student essays about topics the detectors had not seen, {pct(h['share_ge1']['value'])} got a flag from at least one of the 20, but only "
            f"{pct(h['share_all']['value'])} from all 20. The official verdict, which combines three of them, flagged {pct(off)}. "
            "“At least one of 20” looks worse than any single detector would, so we never quote it alone. The detectors disagree for two reasons: their weights differ with the random seed, "
            "and each one’s flag line rests on the few validation essays near it.")


def rerun_copy():
    f = lambda grp, a: ATT[grp]["attacks"][a]
    ai, un = f("ai_test", "typos5"), f("ai_unseen_generators", "typos5")
    def to_above(group_name):
        d = FLIPS[(FLIPS.group == group_name) & (FLIPS.attack == "typos 5%") & (FLIPS.zone_before == "flagged") & (FLIPS.zone_after != "flagged")]   # flags that were lost
        return int(d[d.zone_after == "above_usual"].essays.sum()), int(d.essays.sum())
    a1, b1 = to_above("AI, test")
    a2, b2 = to_above("AI, held-out generators")
    stu_new = META["official"]["students_unseen_topics"]["above_usual"]["value"]
    stu_t5 = f("students_test", "t5")["above_usual"]
    return (f"Light typos removed the flag from {pct(ai['flip'])} of flagged AI essays in our tests, and from {pct(un['flip'])} of essays from AI models the detectors had not seen. "
            f"Most of those moved to “above usual” ({a1} of {b1}, and {a2} of {b2}). That zone also holds {pct(stu_new)} of student essays on new topics, and rewording tools push some students there too "
            f"({pct(stu_t5)} of test students after a light paraphrase), so “above usual” means “look closer”, not “AI”.")


# ---------------------------------------------------------------------------------------------------------------- frames
FONT = "../../frontend/node_modules/@fontsource-variable/atkinson-hyperlegible-next/files/atkinson-hyperlegible-next-latin-wght-normal.woff2"
FONT_I = "../../frontend/node_modules/@fontsource-variable/atkinson-hyperlegible-next/files/atkinson-hyperlegible-next-latin-wght-italic.woff2"
TINOS = "../../frontend/node_modules/@fontsource/tinos/files/tinos-latin-400-normal.woff2"
CSS = open(Path(__file__).with_name("mockup.css")).read().replace("@@FONT@@", FONT).replace("@@FONT_I@@", FONT_I).replace("@@TINOS@@", TINOS)

NAV = '''<header class="hdr"><div class="hdr-in"><a class="brand" href="#"><svg width="22" height="26" viewBox="0 0 22 26" fill="none" aria-hidden="true"><path d="M2.5 1.5h12l5 5v18h-17z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M6 11h10M6 15h10M6 19h6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>Ghost Writer</a>
<nav aria-label="Pages"><a href="#" aria-current="page" class="tab cur">Check an essay</a><a href="#" class="tab">Try to fool it</a><a href="#" class="tab">Check a class</a></nav></div></header>'''


def chips(selected):
    out = []
    for e in EX:
        out.append(f'<button class="chip{" sel" if e["id"] == selected else ""}" aria-pressed="{str(e["id"] == selected).lower()}"><span class="chip-n">{esc(e["name"])}</span><span class="chip-w">{e["words"]} words</span></button>')
    return '<div class="chips" role="group" aria-label="Examples">' + "".join(out) + "</div>"


def essay_stub(i):
    text = EX[i]["text"].strip().replace("\n", " ")
    return f'<div class="paper"><p>{esc(text[:430])}…</p></div>'


def legend():
    return ('<ul class="legend"><li><svg width="18" height="18"><circle cx="9" cy="9" r="7" class="d-flag"/></svg>Flagged</li>'
            '<li><svg width="18" height="18"><circle cx="9" cy="9" r="7" class="d-above"/></svg>Above usual</li>'
            '<li><svg width="18" height="18"><circle cx="9" cy="9" r="7" class="d-not"/></svg>Not flagged</li>'
            '<li><svg width="22" height="22"><circle cx="11" cy="11" r="6.5" class="d-flag"/><circle cx="11" cy="11" r="9.7" class="ens"/></svg>One of the three detectors in the official verdict</li></ul>')


def waffle(counts):
    dots = ["flagged"] * counts["flagged"] + ["above_usual"] * counts["above_usual"] + ["not_flagged"] * counts["not_flagged"]
    cls = {"flagged": "d-flag", "above_usual": "d-above", "not_flagged": "d-not"}
    return '<svg class="waffle" width="%d" height="18" viewBox="0 0 %d 18" role="img" aria-label="%d flagged, %d above usual, %d not flagged">' % (20 * 17, 20 * 17, counts["flagged"], counts["above_usual"], counts["not_flagged"]) + "".join(f'<circle cx="{8 + i * 17}" cy="9" r="6" class="{cls[z]}"/>' for i, z in enumerate(dots)) + "</svg>"


def verdict_block(i, run, theme, phone, expand_why=False, note=None, focus=None, tip=None, rerun=None, tag="a"):
    if rerun:
        run = rerun                                    # after a re-run the scale shows the new marks
    ev = run["events"]
    s = ev[-1]
    off = s["official"]
    zone = off["zone"]
    cls = f"zone-{zone}"
    kind = EX[i]["kind"]
    notes = {"final_system_wrong": "A real student essay the system gets wrong.", "split_jury": "An AI-written essay on which the jurors disagree.",
             "example": EX[i]["note"] or ("This example was written by an AI model." if EX[i]["label"] == "ai" else "This example was written by a student.")}
    wrote = notes.get(kind) if kind != "example" or EX[i]["note"] or True else None
    if i == 2:
        wrote = "A student essay the earlier single-model detector flagged. The final system does not."
    disagree = (0 < s["says_ai"] < 20) or (s["unsure"] and s["says_ai"] + s["unsure"] < 20 and s["says_student"] > 0)
    why = (f'<details class="why"{" open" if expand_why else ""}><summary>Why 20 detectors?</summary><p>{esc(why_text())}</p></details>')
    if rerun:
        rr = rerun
        t = rr["start"]["typos"]
        ss = rr["events"][-1]
        bz, az = ss["before"]["official"]["zone"], ss["official"]["zone"]
        moved = ("The official verdict stayed " + ZONE_LABEL[az].lower() + "." if bz == az else f"The official verdict moved from {ZONE_LABEL[bz].lower()} to {ZONE_LABEL[az].lower()}.")
        changed = ss["jurors_changed_zone"]
        who = "All 20 detectors" if changed == 20 else f"{changed} of 20 detectors"
        rerun_html = f'''<section class="rerun" aria-labelledby="rr-{tag}"><h3 id="rr-{tag}">Typos in {t["words_changed"]} of {EX[i]["words"]} words. {who} changed their mind.</h3>
<p class="rr-row"><span class="rr-k">Before</span>{waffle(ss["before"]["counts"])}<span class="rr-v">{ss["before"]["says_ai"]} flag</span></p>
<p class="rr-row"><span class="rr-k">After</span>{waffle(ss["counts"])}<span class="rr-v">{ss["says_ai"]} flag</span></p>
<p class="rr-off"><strong>{moved}</strong></p><p class="rr-copy">{esc(rerun_copy())}</p>
<p class="rr-btns"><button class="btn sec">Re-run the trial</button><span class="cap">New typos each time. Different seeds give different results.</span></p></section>'''
    else:
        rerun_html = '<p class="rr-btns"><button class="btn sec">Re-run the trial</button><span class="cap">Adds typos to 5% of the words and asks the same 20 detectors again.</span></p>'
    svg = scale_svg(ev, off, phone=phone, focus_seed=focus, show_tip=tip, label_ids=tag)
    return f'''<section class="verdict {cls}" aria-labelledby="v-{tag}"><div class="v-top"><h2 id="v-{tag}" class="t-verdict{" long" if len(verdict_sentence(zone)) > 90 else ""}">{esc(verdict_sentence(zone))}</h2><p class="note">{esc(wrote)}</p></div>
<div class="scalewrap">{svg}</div>{legend()}
<p class="jsum" aria-live="polite"><strong>{esc(summary_sentence(s))}</strong> {esc(SAME)}</p>
{('<p class="disagree">The detectors disagree. That means the jury is less sure. It does not mean a student wrote it.</p>' if disagree else "")}
{why}{rerun_html}</section>'''


def frame(title, width, theme, selected, run, **kw):
    phone = width < 600
    body = f'''{NAV}<main class="main">{chips(selected)}{verdict_block(selected, run, theme, phone, **kw)}{essay_stub(selected)}</main>'''
    return f'<figure class="board"><figcaption>{esc(title)}</figcaption><div class="frame {"phone" if phone else "desk"}" data-theme="{theme}" style="width:{width}px">{body}</div></figure>'


# ---------------------------------------------------------------------------------------------------------------- decision boards
def decisions_board():
    import subprocess
    subprocess.run([sys.executable, str(Path(__file__).with_name('contrast.py'))], check=True, capture_output=True)
    cdf = pd.read_csv(Path(__file__).with_name('contrast.csv'))
    assert cdf.passes.all(), cdf[~cdf.passes]
    n_pairs = len(cdf)
    ai = entry(0)["untyped"]["events"]
    off = ai[-1]["official"]
    def column_naive():
        r, step, H = 8, 18, 20 * 18 + 70
        s = f'<svg width="150" height="{H}" viewBox="0 0 150 {H}" role="img" aria-label="Twenty dots stacked in one column"><line x1="75" x2="75" y1="14" y2="14" class="axis"/><line x1="30" x2="120" y1="30" y2="30" class="axis"/>'
        s += "".join(f'<circle cx="75" cy="{44 + i * step}" r="8" class="d-flag"/>' for i in range(20))
        s += f'<text x="75" y="{H - 8}" text-anchor="middle" class="tl">360 px tall</text></svg>'
        return s
    sep = f'''<svg width="360" height="170" viewBox="0 0 360 170" role="img" aria-label="Two different scales"><text x="0" y="16" class="tl b">Seed-42 score ruler, −10 to +10</text><line x1="0" x2="340" y1="40" y2="40" class="axis"/><path d="M300 22 h12 l-6 9 z" class="tri"/>
<text x="0" y="100" class="tl b">Jury, −log₁₀ p</text><line x1="0" x2="340" y1="124" y2="124" class="axis"/>{"".join(f'<circle cx="{230 + (i % 7) * 15}" cy="{108 - (i // 7) * 0}" r="6" class="d-flag"/>' for i in range(0))}
<text x="0" y="160" class="cap-svg">Two axes, two meanings, one flag line drawn twice</text></svg>'''
    return f'''<figure class="board wide"><figcaption>Decisions to approve</figcaption><div class="frame desk" data-theme="light" style="width:1440px"><div class="main decide">
<h2 class="t-section">Three design decisions, with the alternatives I rejected</h2>
<div class="cols">
<article><h3>1. One scale for the official verdict and the jury (recommended)</h3>
<p>The existing page draws the score on a −10 to +10 logit ruler. A logit means something different for each of the 20 detectors, so the jury cannot use it, and the official verdict is a mean of <em>p</em>-values, which has no logit at all. I propose that the page keeps one ruler, but in the units everything already shares: <em>how many of the 2,291 student essays we checked score this high or higher</em> (1 in 10, 1 in 100, …). The official marker sits on it, the jury hangs directly under it, and the flag line and the “above usual” edge are in the same place for all 21 marks.</p>
<p><strong>Rejected: two scales</strong> (the old logit ruler for seed 42, a second axis for the jury). It would draw the flag line twice at different places and make “the jury disagrees with the verdict” look like a drawing error.</p>
<p class="cost"><strong>Cost:</strong> the “+9.7 / ceiling at +9.8” language disappears from the page and from <code>docs/viva-demo.md</code>; the Strict/Standard switch goes too (the three zones carry what it carried). Say if you want the switch kept as a second flag line at {one_in(0.00093)} (the 0.5% point).</p></article>
<article><h3>2. The pile-up at the end of the scale: a stack in a box, not a column</h3>
<p>The head saturates, and the position −log₁₀ p cannot go past 3.36 (“higher than every one of the 2,291 student essays”). On a clear AI essay all 20 detectors land exactly there, so a beeswarm would be a column 360 px tall that looks like a measurement. Dots whose position is real are dodged in rows under the ruler. Dots <em>at the end</em> go into a labelled box beside the scale, “Off the scale”, in a grid whose order means nothing, with a bracket to the end of the axis.</p>
<div class="rej"><figure>{column_naive()}<figcaption class="cap">Rejected: a plain beeswarm at the end.</figcaption></figure></div></article>
<article><h3>3. Marks, not colours</h3>
<p>Flagged, above usual and not flagged are told apart by <strong>fill</strong> (solid, amber with a ring, hollow), by position and by the zone bands, never by colour alone and never green or red. The three detectors inside the official verdict get a blue ring. Each mark has a tooltip and a focus ring; the 20 marks are one tab stop with arrow keys, and the same information is available as a list.</p>
<p><strong>Dark theme.</strong> The app has no dark theme today (<code>color-scheme: light</code>). The boards propose dark tokens (same hues, inverted lightness; amber zones kept) and every text and mark pair on the boards passes (WCAG 4.5:1 for text, 3:1 for marks: {n_pairs} pairs in both themes, <code>jury/contrast.csv</code>); they would be added as one block in <code>tokens.css</code>.</p>
<p><strong>Motion.</strong> On Run, the 20 marks drop in one by one (opacity and a 12 px translateY, 40 ms apart, ending by 0.8 s), the official marker lands last with the spring. Re-run: marks move with <code>transform</code> only. Reduced motion: every mark appears in place with a 120 ms fade.</p></article>
</div></div></div></figure>'''


def build():
    e0, e2, e3, e4 = (entry(i) for i in (0, 2, 3, 4))
    boards = [
        frame("1440 · light · the AI essay: all 20 detectors at the end of the scale", 1440, "light", 0, e0["untyped"], tag="b1"),
        frame("1440 · dark · the AI essay that splits the jury: tooltip and keyboard focus on one mark, “Why 20 detectors?” open", 1440, "dark", 4, e4["untyped"], expand_why=True, focus=int(e4["untyped"]["events"][5]["seed"]), tip=int(e4["untyped"]["events"][5]["seed"]), tag="b2"),
        frame("1440 · light · after “Re-run the trial” on the student essay the final system gets wrong (typos seed 43)", 1440, "light", 3, e3["untyped"], rerun=e3["typos"]["43"], tag="b3"),
        frame("390 · light · the same student essay, phone width", 390, "light", 3, e3["untyped"], tag="b4"),
        frame("390 · dark · the student essay the earlier detector flagged: the before-and-after", 390, "dark", 2, e2["untyped"], tag="b5"),
        frame("390 · light · after “Re-run the trial” (the AI essay that splits the jury, typos seed 42)", 390, "light", 4, e4["untyped"], rerun=e4["typos"]["42"], tag="b6"),
        decisions_board(),
    ]
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>The Jury: mockup</title><style>{CSS}</style></head>
<body class="canvas"><h1 class="canvas-h">The Jury: static mockup for approval (nothing here is built yet)</h1>
<p class="canvas-p">Every number is read from <code>results/</code> and from the precomputed trials. The copy is a proposal. Boards: 1 to 3 at 1440 px, 4 to 6 at 390 px, then the decisions.</p>{"".join(boards)}</body></html>'''
    out = ROOT / "design" / "artboards" / "Jury.html"
    out.write_text(page)
    print("wrote", out, len(page) // 1024, "KB")


if __name__ == "__main__":
    build()
