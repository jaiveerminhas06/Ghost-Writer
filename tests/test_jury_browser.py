"""Browser tests for the Jury on the built page (Phase 5). The twenty detectors are the fake from conftest (no GPU, no models); the page,
the stream and the layout are the real ones.

What is checked, in a real Chromium:
  * the trial completes on a built-in example and the page's summary matches what /api/jury sent for the same essay;
  * with reduced motion all twenty marks are on the page, fully visible, and nothing but opacity animates;
  * "Re-run the trial" updates the counts, the headline starts "After typos:", and "Show original" brings the first trial back;
  * the twenty marks are one tab stop and arrow keys move between them;
  * at 390 px nothing scrolls sideways, the two zone names do not overlap, and the page has room under the fixed action bar;
  * the class page shows "Jurors flagging n of 20", the finished state, and the end-of-scale box with a count.
Needs the built page (npm run build in frontend/), Playwright and Chromium; skipped otherwise. Run with: pytest tests/test_jury_browser.py
"""
import json
import shutil
import socket
import threading
import time
import urllib.request
from pathlib import Path

import numpy as np
import pytest

playwright = pytest.importorskip("playwright.sync_api")
uvicorn = pytest.importorskip("uvicorn")

from api import limiter, main, results, settings  # noqa: E402
from tests.conftest import FakeDetector, FakeJury, FakeT5  # noqa: E402

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist" / "index.html"
CHROMIUM = shutil.which("chromium") or shutil.which("chromium-browser") or "/snap/bin/chromium"
READY = "section[aria-labelledby=verdict][aria-busy=false]"                 # the verdict panel, once every mark has arrived

pytestmark = pytest.mark.skipif(not DIST.exists(), reason="frontend/dist is not built")


@pytest.fixture(scope="module")
def fake_jury():
    return FakeJury()


@pytest.fixture(scope="module")
def live_server(fake_jury):
    from src.explain import sentence_spans

    def occlusion(det, text):
        spans = sentence_spans(text)
        return spans, np.linspace(0, 3, len(spans)), None

    mp = pytest.MonkeyPatch()
    mp.setattr(main, "detector", lambda: FakeDetector())
    mp.setattr(settings, "RATE_LIMIT_PER_MIN", 100_000)        # these tests load many pages in a minute; the limit has its own tests
    mp.setattr(main, "jury", lambda: fake_jury)
    mp.setattr(main, "attribution_model", lambda: object())
    mp.setattr(main, "t5", lambda: FakeT5())
    mp.setattr("src.explain.occlusion", occlusion)
    mp.setattr("src.attribution.most_similar", lambda model, text, k=3: [("Mistral", 0.37)][:k])
    limiter.reset()
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)
    mp.undo()


@pytest.fixture(scope="module")
def browser():
    with playwright.sync_playwright() as p:
        try:
            b = p.chromium.launch(executable_path=CHROMIUM if Path(CHROMIUM).exists() else None, args=["--no-sandbox"])
        except Exception as e:                                               # no browser on this machine
            pytest.skip(f"no Chromium to drive: {e}")
        yield b
        b.close()


@pytest.fixture
def new_page(browser, live_server):
    pages = []

    def make(width=1440, height=900, reduced=False):
        ctx = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce" if reduced else "no-preference")
        pg = ctx.new_page()
        pg.errors = []
        pg.on("pageerror", lambda e: pg.errors.append(str(e)))
        pg.on("console", lambda m: pg.errors.append(m.text) if m.type == "error" else None)
        pages.append(ctx)
        return pg
    yield make
    for c in pages:
        c.close()


def stream(live_server, text, **body):
    req = urllib.request.Request(f"{live_server}/api/jury", json.dumps({"text": text, **body}).encode(), {"Content-Type": "application/json"})
    return [json.loads(x) for x in urllib.request.urlopen(req).read().decode().splitlines()]


def open_example(pg, live_server, i):
    pg.goto(f"{live_server}/?example={i}")
    pg.wait_for_selector(READY, timeout=30000)
    pg.wait_for_function("document.getAnimations().every((a) => a.playState === 'finished')", timeout=10000)


def test_the_trial_completes_and_the_summary_matches_the_api(new_page, live_server):
    pg = new_page()
    ai = results.examples()[0]
    open_example(pg, live_server, 0)
    marks = pg.locator("g[role=listitem]")
    assert marks.count() == 20
    api = stream(live_server, ai["text"])
    summary = api[-1]
    zones = pg.eval_on_selector_all("g[role=listitem]", "els => els.map((e) => e.dataset.zone)")
    assert {z: zones.count(z) for z in ("flagged", "above_usual", "not_flagged")} == summary["counts"]
    assert "All 20 detectors flag this essay." in pg.inner_text("[aria-live=polite]")
    assert pg.inner_text("h2#verdict").startswith("Flagged. Higher than every student essay we checked. That isn’t proof.")
    assert "Off the scale" in pg.inner_text("section[aria-labelledby=verdict]") or pg.locator("text=Off the scale").count() > 0
    assert "1 in 2,292" not in pg.inner_text("body")                           # a score at the floor is never printed as 1 in n+1
    student = results.examples()[1]
    open_example(pg, live_server, 1)
    assert pg.inner_text("h2#verdict").startswith("Not flagged. About 1 in ")
    assert "reads like a student" not in pg.inner_text("section[aria-labelledby=verdict]").lower()
    assert "None of the 20 detectors flag this essay." in pg.inner_text("[aria-live=polite]")
    assert stream(live_server, student["text"])[-1]["counts"]["not_flagged"] == 20
    assert pg.errors == []


def test_with_reduced_motion_all_twenty_marks_appear_without_movement(new_page, live_server):
    pg = new_page(reduced=True)
    pg.goto(f"{live_server}/?example=0")
    pg.wait_for_selector(READY, timeout=30000)
    pg.wait_for_timeout(400)                                                    # longer than the 120 ms fade
    assert pg.locator("g[role=listitem]").count() == 20
    opacity = pg.eval_on_selector_all("g[role=listitem] > g", "els => els.map((e) => getComputedStyle(e).opacity)")
    assert opacity and all(o == "1" for o in opacity)
    moving = pg.evaluate("""() => document.getAnimations().filter((a) => a.playState === 'running' && a.effect && a.effect.getKeyframes().some((k) => 'transform' in k && k.transform && k.transform !== 'none')).length""")
    assert moving == 0


def test_rerun_updates_the_counts_and_show_original_brings_the_first_trial_back(new_page, live_server, fake_jury):
    ai = results.examples()[0]
    fake_jury.degrade_unless = ai["text"]                                       # any typo version of the AI essay scores low
    try:
        pg = new_page()
        open_example(pg, live_server, 0)
        assert "All 20 detectors flag this essay." in pg.inner_text("[aria-live=polite]")
        pg.get_by_role("button", name="Re-run the trial").click()
        pg.wait_for_selector("text=Show original", timeout=30000)
        pg.wait_for_selector(READY, timeout=30000)
        assert pg.inner_text("h2#verdict").startswith("After typos: Not flagged.")
        assert "None of the 20 detectors flag this essay." in pg.inner_text("[aria-live=polite]")
        lead = pg.inner_text("h3#rerun-h")
        assert lead.startswith("Typos in ") and "All 20 detectors changed their mind; the official verdict moved from flagged to not flagged." in lead
        panel = pg.inner_text("section[aria-labelledby=rerun-h]")
        assert "This essay was written by an AI model" in panel                  # the author sentence, for a built-in example
        assert "look closer" in panel and "not “AI”" in panel                      # "above usual" always travels with what it means
        pg.get_by_role("button", name="Show original").click()
        pg.wait_for_selector("text=Flagged. Higher than every student essay we checked", timeout=10000)
        assert pg.locator("text=Show original").count() == 0
        assert pg.locator("g[role=listitem]").count() == 20
        assert pg.errors == []
    finally:
        fake_jury.degrade_unless = None


def test_the_twenty_marks_are_one_tab_stop_and_arrow_keys_move_between_them(new_page, live_server):
    pg = new_page()
    open_example(pg, live_server, 4)
    assert pg.locator("g[role=listitem][tabindex='0']").count() == 1
    assert pg.locator("g[role=listitem][tabindex='-1']").count() == 19
    pg.focus("g[role=listitem][tabindex='0']")
    first = pg.evaluate("document.activeElement.dataset.seed")
    pg.keyboard.press("ArrowRight")
    second = pg.evaluate("document.activeElement.dataset.seed")
    assert (first, second) == ("42", "43")
    assert pg.inner_text("p[class*=detail]").startswith("Detector 43: ")
    pg.keyboard.press("End")
    assert pg.evaluate("document.activeElement.dataset.seed") == "61"
    pg.keyboard.press("Home")
    assert pg.evaluate("document.activeElement.dataset.seed") == "42"


def test_at_390_px_nothing_scrolls_sideways_and_the_zone_names_do_not_collide(new_page, live_server, fake_jury):
    ai = results.examples()[0]
    fake_jury.degrade_unless = ai["text"]
    try:
        pg = new_page(width=390, height=844)
        for i in (0, 1, 2, 3, 4):
            open_example(pg, live_server, i)
            assert pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), f"example {i} scrolls sideways"
            names = pg.eval_on_selector_all("svg text[class*=zone]", "els => els.map((e) => { const r = e.getBoundingClientRect(); return [r.left, r.right, r.top, r.bottom] })")
            assert len(names) == 2
            (l1, r1, t1, b1), (l2, r2, t2, b2) = names
            assert r1 <= l2 + 0.5 or r2 <= l1 + 0.5 or b1 <= t2 or b2 <= t1, f"example {i}: the zone names overlap"
        open_example(pg, live_server, 0)
        pg.get_by_role("button", name="Re-run the trial").click()
        pg.wait_for_selector("text=Show original", timeout=30000)
        pg.wait_for_selector(READY, timeout=30000)
        assert pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
        # the fixed action bar must never hide the last control: scrolled to the end, the page's bottom padding is at least the bar's height
        bar = pg.evaluate("(() => { const b = document.querySelector('[class*=bar]'); return b ? b.getBoundingClientRect().height : 0 })()")
        pad = pg.evaluate("parseFloat(getComputedStyle(document.querySelector('[class*=page]')).paddingBottom)")
        assert bar > 0 and pad >= bar
        pg.get_by_role("button", name="Re-run the trial").scroll_into_view_if_needed()
        box = pg.get_by_role("button", name="Re-run the trial").bounding_box()
        assert box["y"] + box["height"] <= 844 - bar + 1, "the re-run button sits behind the action bar"
        assert pg.errors == []
    finally:
        fake_jury.degrade_unless = None


def test_the_class_page_shows_jurors_flagging_in_its_finished_state_and_the_end_of_scale_box(new_page, live_server, fake_jury):
    from api import demo
    slug = demo.topics()[0]
    cls = demo.demo_class(slug)
    ai_texts = {e["text"] for e in cls["essays"] if cls["labels"][e["name"]] == "ai"}
    original = fake_jury.logit
    fake_jury.logit = lambda seed, text: 9.8 if text in ai_texts else -9.0 + (len(text) % 97) * 0.12 + 0.01 * (seed - 42)   # known AI essays score at the end of the scale; students spread out
    try:
        pg = new_page()
        pg.goto(f"{live_server}/class")
        pg.get_by_text(cls["prompt"]).first.click()
        pg.wait_for_function("!document.body.innerText.includes('Waiting to score') && document.querySelector('#summary')", timeout=60000)
        body = pg.inner_text("body")
        assert "Jurors flagging" in body and "20 of 20" in body and "0 of 20" in body
        assert "None of 2,291" in pg.inner_text("[role=table]")                 # essays at the floor: the short form, never "1 in 2,292"
        assert "1 in 2,292" not in body
        assert pg.locator("svg[role=group]").count() == 1                       # the class strip is the essay page's scale component
        strip = pg.eval_on_selector("svg[role=group]", "e => e.textContent")
        assert "Off the scale" in strip and f"{len(ai_texts)} of {len(cls['essays'])} score higher than" in strip.replace("\n", " ")
        assert "1 in 1" in strip
        assert "How many student essays score this high or higher" in body
        assert pg.errors == []
    finally:
        fake_jury.logit = original
