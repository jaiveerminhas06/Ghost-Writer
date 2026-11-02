"""Browser test for the highlights on Check an essay (a regression test for a bug seen on 2026-11-02).

The bug: highlighted sentences showed a solid yellow bar and no text. The yellow is painted on a second, transparent copy of the
paragraph behind the real text. Its marks are animated, an animated element gets its own stacking context, and that painted
OVER the plain text layer. The text layer's own marks also showed the browser's default yellow.

What this checks, for every highlight on the page: (1) the pixels where it sits contain dark ink, not a flat bar of yellow (this is what catches the paint layer covering the text; elementFromPoint cannot, because that layer ignores the pointer), (2) its
colour is the ink colour, (3) its background is transparent, so the browser default yellow is not showing.

Needs the built page (`npm run build` in frontend/, or bash scripts/demo.sh), Playwright and Chromium; skipped otherwise.
The detector is the fake from conftest, so no GPU is used. Run with: pytest tests/test_frontend.py
"""
import io
import shutil
import socket
import threading
import time
from pathlib import Path

import numpy as np
import pytest

playwright = pytest.importorskip("playwright.sync_api")
uvicorn = pytest.importorskip("uvicorn")

from PIL import Image  # noqa: E402

from api import limiter, main, results  # noqa: E402
from tests.conftest import FakeDetector, FakeT5  # noqa: E402

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist" / "index.html"
CHROMIUM = shutil.which("chromium") or shutil.which("chromium-browser") or "/snap/bin/chromium"

pytestmark = pytest.mark.skipif(not DIST.exists(), reason="frontend/dist is not built")


@pytest.fixture(scope="module")
def live_server():
    from src.explain import sentence_spans

    def occlusion(det, text):
        spans = sentence_spans(text)
        return spans, np.linspace(0, 3, len(spans)), None   # every tier appears

    mp = pytest.MonkeyPatch()
    mp.setattr(main, "detector", lambda: FakeDetector())
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
def page(live_server):
    with playwright.sync_playwright() as p:
        try:
            browser = p.chromium.launch(executable_path=CHROMIUM if Path(CHROMIUM).exists() else None, args=["--no-sandbox"])
        except Exception as e:                                   # no browser on this machine
            pytest.skip(f"no Chromium to drive: {e}")
        pg = browser.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(f"{live_server}/?example=0")
        pg.wait_for_selector("[data-text] mark", timeout=20000)
        pg.wait_for_function("document.getAnimations().every((a) => a.playState === 'finished')", timeout=10000)   # marks have finished arriving
        yield pg
        browser.close()


CHECK = """() => {
  const ink = getComputedStyle(Object.assign(document.body.appendChild(document.createElement('i')), { style: 'color: var(--ink)' })).color
  const out = []
  for (const mark of document.querySelectorAll('[data-text] mark')) {
    if (mark.closest('[aria-hidden="true"]')) continue            // the paint layer: transparent text by design
    mark.scrollIntoView({ block: 'center' })                       // elementFromPoint only sees what is in the viewport
    const r = mark.getClientRects()[0]
    if (!r) continue
    const cs = getComputedStyle(mark)
    out.push({ text: mark.textContent.slice(0, 30), tier: mark.dataset.tier ?? null, ink, color: cs.color,
               background: cs.backgroundColor,
               box: { x: r.left, y: r.top, width: r.width, height: r.height } })
  }
  const painted = document.querySelectorAll('[data-text] [aria-hidden="true"] mark').length
  return { marks: out, painted }
}"""


def test_highlighted_text_is_visible(page):
    got = page.evaluate(CHECK)
    assert got["marks"], "no highlights were rendered, so there is nothing to check"
    assert got["painted"] >= len(got["marks"]), "the yellow is missing: the paint layer has fewer marks than the text layer"
    for m in got["marks"]:
        assert m["color"] == m["ink"], f"highlighted text is not the ink colour: {m}"
        assert m["background"] in ("rgba(0, 0, 0, 0)", "transparent"), f"browser-default yellow is showing: {m}"


def test_every_tier_is_painted_in_its_own_colour(page):
    """The yellow itself must reach the screen: each tier's paint-layer mark has a real, different background."""
    colours = page.evaluate("""() => {
      const by = {}
      for (const m of document.querySelectorAll('[data-text] [aria-hidden="true"] mark')) by[m.dataset.tier] = getComputedStyle(m).backgroundColor
      return by }""")
    assert {"1", "2", "3"} <= set(colours), f"expected all three tiers, got {colours}"
    assert len(set(colours.values())) == len(colours), f"two tiers share a colour: {colours}"
    assert all(c != "rgba(0, 0, 0, 0)" for c in colours.values()), colours


def test_text_is_painted_inside_every_highlight(page):
    """Pixel check: a highlight that hides its text is a flat yellow rectangle. Real text puts dark ink pixels inside it."""
    n = page.evaluate("[...document.querySelectorAll('[data-text] mark')].filter((x) => !x.closest('[aria-hidden=\"true\"]')).length")
    assert n
    for i in range(n):
        box = page.evaluate("""(i) => { const el = [...document.querySelectorAll('[data-text] mark')].filter((x) => !x.closest('[aria-hidden="true"]'))[i]
                               el.scrollIntoView({ block: 'center' })
                               const r = el.getClientRects()[0]; return { x: r.left, y: r.top, width: r.width, height: r.height } }""", i)
        pixels = Image.open(io.BytesIO(page.screenshot(clip=box))).convert("L").getdata()
        dark = sum(1 for v in pixels if v < 110)
        assert dark >= 20, f"no ink inside highlight {i} (only {dark} dark pixels): the text is covered"
