"""Motion audit: records every animation and transition the browser really runs, and checks them against the design spec.

    python scripts/motion_audit.py                       (the dev server on :5173 and the API on :8000 must be running)
    python scripts/motion_audit.py --url http://localhost:8000     (the built page served by FastAPI)
    python scripts/motion_audit.py --self-test                      (proves the judge rejects bad animations; needs no running app)
    CHROMIUM=/path/to/chromium python scripts/motion_audit.py       (otherwise it tries /snap/bin/chromium, then Playwright's own)

Needs `pip install playwright` (a development tool; it is not in requirements.txt). It runs the same walk-through twice, once normally and
once with `prefers-reduced-motion: reduce` emulated: score an essay (the twenty marks drop in), re-run the trial and show the original, open the "Which AI" drawer,
try to fool the detector twice, load both demo classes (60 essays, so the table passes 50 rows), sort and page, and hover controls.

It fails (exit code 1) if it records nothing, or does not see the animations that must exist (the marker's spring and the highlight fade),
and also if:
  normal mode:  a keyframe animation or element.animate() changes anything but transform and opacity, or a transition changes a property
                outside the allowed list: transform and opacity, plus what the spec itself calls for (colour and border changes on
                hover/press/focus/selection, the method cards' box-shadow, and the "Which AI" drawer's grid-template-rows);
  reduced mode: anything animates other than opacity, or for longer than 120 ms.
"""
import argparse
import json
import mimetypes
import os
import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_TRANSITIONS = {"transform", "opacity", "background-color", "color", "border-color", "box-shadow", "grid-template-rows"}

HOOK = """
window.__motion = []
const skip = new Set(['offset', 'easing', 'composite', 'computedOffset'])
const clean = (c) => String(c).replace(/_[a-z0-9]{5,}_\\d+$/, '').replace(/^_/, '')
const who = (el) => (el && el.tagName ? el.tagName.toLowerCase() + '.' + String(el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className).split(' ').map(clean).filter(Boolean).join('.') : '?')
const props = (a) => { try { return [...new Set(a.effect.getKeyframes().flatMap(k => Object.keys(k).filter(x => !skip.has(x))))] } catch { return [] } }
const rec = (kind, name, properties, timing, el) => window.__motion.push({ kind, name, properties, duration: timing && timing.duration, delay: timing && timing.delay, target: who(el) })
document.addEventListener('animationstart', (e) => { const a = (e.target.getAnimations ? e.target.getAnimations() : []).find(x => x.animationName === e.animationName); if (a) rec('css-animation', clean(e.animationName), props(a), a.effect.getTiming(), e.target) }, true)
document.addEventListener('transitionrun', (e) => { const a = document.getAnimations().find(x => x.transitionProperty === e.propertyName && x.effect && x.effect.target === e.target); rec('css-transition', e.propertyName, [e.propertyName], a ? a.effect.getTiming() : null, e.target) }, true)
const orig = Element.prototype.animate
Element.prototype.animate = function (kf, opts) { const a = orig.call(this, kf, opts); rec('waapi', 'element.animate', props(a), a.effect.getTiming(), this); return a }
"""


def files_of(*topics):
    out = []
    for t in topics:
        for f in sorted((ROOT / "demo" / "class_sample" / t).glob("*.txt")):
            out.append({"name": f.name, "mimeType": mimetypes.guess_type(f.name)[0] or "text/plain", "buffer": f.read_bytes()})
    return out


def walk(page, url, essays):
    """The walk-through. Every step waits for what it triggers, so each animation has time to run."""
    held = []
    page.route("**/api/score", lambda r: held.append(r))                                  # hold the first answer: shows the 300 ms window and the skeleton
    page.goto(url + "/?example=3")
    page.wait_for_timeout(700)
    if held:
        held[0].continue_()
    page.unroute("**/api/score")
    page.wait_for_selector("[class*=paint] mark", timeout=60000)
    page.wait_for_timeout(2200)
    ready = "section[aria-labelledby=verdict][aria-busy=false]"                           # the twenty marks have all dropped in
    page.wait_for_selector(ready, timeout=90000); page.wait_for_timeout(600)
    page.get_by_role("button", name="Re-run the trial").click(); page.wait_for_selector("text=Show original", timeout=60000)      # the marks travel to their new places
    page.wait_for_selector(ready, timeout=60000); page.wait_for_timeout(900)
    page.get_by_role("button", name="Show original").click(); page.wait_for_timeout(900)
    page.get_by_role("button", name="Show the guess anyway").click(); page.wait_for_selector("text=-based sources"); page.wait_for_timeout(500)
    page.get_by_role("button", name="Hide the guess").click(); page.wait_for_timeout(500)
    page.get_by_role("radio").nth(1).click(); page.wait_for_selector("h2#verdict:has-text('Not flagged')", timeout=60000); page.wait_for_timeout(1500)
    page.get_by_role("radio").nth(2).click(); page.wait_for_selector("[class*=paint] mark", timeout=60000)
    page.get_by_role("link", name="Try to fool it").first.click(); page.wait_for_selector("text=Rewrite with")
    page.get_by_role("button", name="Rewrite and re-score").click(); page.wait_for_selector("[role=table] button[role=row]", timeout=60000); page.wait_for_timeout(800)
    page.get_by_role("button", name="Try different typos").click()
    page.wait_for_function("document.querySelectorAll('[role=table] button[role=row]').length >= 3", timeout=60000); page.wait_for_timeout(800)
    page.get_by_role("link", name="Check a class").first.click(); page.wait_for_selector("text=Load the demo class")
    page.locator("input[type=file]").set_input_files(essays)                              # both demo classes: 60 essays, so the table passes 50 rows
    page.wait_for_selector("#summary", timeout=120000)
    page.wait_for_function("!document.body.innerText.includes('Waiting to score')", timeout=120000); page.wait_for_timeout(900)
    page.get_by_role("button", name="Students this high").click(); page.wait_for_timeout(600)
    page.get_by_role("button", name="Next 50").click(); page.wait_for_timeout(500)
    page.get_by_role("button", name="Choose files").hover(); page.wait_for_timeout(300)
    page.locator("a[role=row]").first.hover(); page.wait_for_timeout(300)
    page.get_by_role("button", name="Clear this class").click(); page.wait_for_timeout(300)


def audit(browser, url, reduced, essays):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce" if reduced else "no-preference")
    ctx.add_init_script(HOOK)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    walk(page, url, essays)
    log = page.evaluate("window.__motion")
    ctx.close()
    return log, errors


def groups(log):
    out = {}
    for m in log:
        key = (m["kind"], m["name"], tuple(sorted(m["properties"])))
        g = out.setdefault(key, {"n": 0, "durations": set(), "targets": set()})
        g["n"] += 1
        g["targets"].add(m["target"])
        if isinstance(m["duration"], (int, float)):
            g["durations"].add(round(m["duration"]))
    return out


def breaks_rules(kind, props, durations, reduced):
    """True if one recorded kind of animation breaks the spec (see the module docstring)."""
    if reduced:
        return bool(set(props) - {"opacity"}) or any(d > 120 for d in durations)
    if kind == "css-transition":
        return bool(set(props) - ALLOWED_TRANSITIONS)
    return bool(set(props) - {"transform", "opacity"})


SELF_TEST = [   # (reduced motion?, what it is, css, class added after load, must the judge reject it?)
    (False, "margin-left slides (keyframes)", "@keyframes a { from { margin-left: 0 } to { margin-left: 40px } } .x { animation: a 200ms }", "", True),
    (False, "width transition", ".x { transition: width 200ms } .x.go { width: 200px }", "go", True),
    (False, "opacity + transform keyframes", "@keyframes a { from { opacity: 0; transform: translateY(6px) } } .x { animation: a 180ms }", "", False),
    (False, "hover colour transition (allowed)", ".x { transition: background-color 150ms } .x.go { background: #123 }", "go", False),
    (True, "transform slide, 300 ms", "@keyframes a { from { transform: translateX(0) } to { transform: translateX(40px) } } .x { animation: a 300ms }", "", True),
    (True, "opacity fade, 400 ms (too long)", "@keyframes a { from { opacity: 0 } } .x { animation: a 400ms }", "", True),
    (True, "opacity fade, 90 ms", "@keyframes a { from { opacity: 0 } } .x { animation: a 90ms }", "", False),
]


def self_test(browser, url):
    """Feeds the recorder and the judge small pages whose motion is known, and checks the verdicts are the ones expected."""
    wrong = []
    for reduced, label, css, cls, expect_reject in SELF_TEST:
        ctx = browser.new_context(reduced_motion="reduce" if reduced else "no-preference")
        ctx.add_init_script(HOOK)
        page = ctx.new_page()
        body = f"<style>.x{{width:50px;height:10px;background:#888}}{css}</style><div class='x'>x</div>"
        page.route(url + "/__probe", lambda route, request, body=body: route.fulfill(content_type="text/html", body=body))
        page.goto(url + "/__probe")
        if cls:
            page.wait_for_timeout(80)
            page.evaluate(f"document.querySelector('.x').classList.add('{cls}')")
        page.wait_for_timeout(500)
        g = groups(page.evaluate("window.__motion"))
        rejected = any(breaks_rules(k[0], k[2], v["durations"], reduced) for k, v in g.items())
        ok = bool(g) and rejected == expect_reject
        print(f"  {'reduced' if reduced else 'normal ':8}{label:40} judge says {'REJECT' if rejected else 'accept'}  {'ok' if ok else 'WRONG'}")
        if not ok:
            wrong.append(label)
        ctx.close()
    return wrong


MUST_SEE = {False: {"land", "arrive"}, True: {"arrive"}}        # the spring, and the fade that paints highlights


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", default="http://localhost:5173")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    exe = os.environ.get("CHROMIUM") or next((p for p in ("/snap/bin/chromium", shutil.which("chromium") or "", shutil.which("chromium-browser") or "") if p and Path(p).exists()), None)
    essays = files_of("electoral_college", "summer_projects")
    failures = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe, args=["--no-sandbox"]) if exe else p.chromium.launch()
        if args.self_test:
            wrong = self_test(browser, args.url)
            browser.close()
            print("\nSelf-test " + ("FAILED: " + ", ".join(wrong) if wrong else "passed: the judge rejects what it should and accepts what it should."))
            sys.exit(1 if wrong else 0)
        for reduced in (False, True):
            log, errors = audit(browser, args.url, reduced, essays)
            mode = "REDUCED MOTION" if reduced else "NORMAL MOTION"
            g = groups(log)
            seen = {k[1] for k in g}
            if not log or not MUST_SEE[reduced] <= seen:
                failures.append(f"{mode}: recorded {len(log)} animations but not {sorted(MUST_SEE[reduced] - seen)}: the recorder or the walk-through is broken")
            print(f"\n=== {mode}: {len(log)} animations recorded, {len(g)} distinct ===")
            for (kind, name, props), v in g.items():
                bad = breaks_rules(kind, props, v["durations"], reduced)
                note = "    <-- FAILS" if bad else ""
                print(f"  {kind:14} {name[:28]:28} {','.join(props)[:34]:34} x{v['n']:<4} {sorted(v['durations'])} ms{note}")
                if bad:
                    failures.append(f"{mode}: {kind} {name} {props} {sorted(v['durations'])}")
            if errors:
                failures.append(f"{mode}: page errors {errors[:2]}")
        browser.close()
    print("\n" + ("MOTION AUDIT FAILED:\n  " + "\n  ".join(failures) if failures else "Motion audit passed."))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
